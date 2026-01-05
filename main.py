import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# ==========================================
# 🛑 核心配置：雙核心名單 (菁英 + 指定熱門獵殺)
# ==========================================
TG_TOKEN = "8533923327:AAFfSDIxOuZDDMKdLkyOFznLafpKpTTdJok"
TG_CHAT_ID = "1009141944"

# 1. 你的菁英庫
ELITE_DATABASE = {
    "2408.TW": "南亞科", "2344.TW": "華邦電", "2337.TW": "旺宏", "8299.TWO": "群聯", 
    "3260.TWO": "威剛", "3006.TW": "晶豪科", "3363.TWO": "上詮", "4979.TWO": "華星光", 
    "3450.TW": "聯鈞", "3163.TWO": "波若威", "2359.TW": "所羅門", "2049.TW": "上銀",
    "1519.TW": "華城", "1513.TW": "中興電", "2330.TW": "台積電", "2317.TW": "鴻海",
    "2382.TW": "廣達", "3231.TW": "緯創", "2603.TW": "長榮", "2002.TW": "中鋼"
}

# 2. 幫你補齊：你指定的熱門股代號與名稱對照表
HOT_WATCH_DATABASE = {
    "2543.TW": "皇昌", "1717.TW": "長興", "1725.TW": "元禎", "4720.TW": "德淵", 
    "4764.TW": "雙邦", "6861.TW": "睿生光電", "6239.TW": "力成", "8110.TW": "華東", 
    "3057.TW": "雲辰", "2409.TW": "友達", "3481.TW": "群創", "6116.TW": "彩晶", 
    "8105.TW": "凌巨", "6285.TW": "啟碁", "2460.TW": "建通", "6155.TW": "鈞寶", "2461.TW": "光群雷"
}

# 合併兩者作為「已知名稱資料庫」
FULL_NAME_DB = {**ELITE_DATABASE, **HOT_WATCH_DATABASE}

# ==========================================
# 🧠 強化版分析邏輯 (加入快漲停符號)
# ==========================================
def analyze_reason(ticker, change, v_ratio):
    prefix = ticker[:2]
    # 判斷是否「快漲停」或「已漲停」
    warning_sign = ""
    if change >= 9.5:
        warning_sign = "🛑【已鎖死】"
    elif change >= 8.0:
        warning_sign = "⚡【快漲停避雷】"
    elif change >= 6.0:
        warning_sign = "🚀【強力拉升】"

    # 行業別判斷
    reason = "🚨 帶量轉強"
    if prefix in ["17", "47"]:
        reason = "🧪 化工族群連動"
    elif ticker in ["2409.TW", "3481.TW", "6116.TW"]:
        reason = "📺 面板族群轉強"
    elif v_ratio > 2.5:
        reason = "🔥 大戶異常掃貨"
    
    return f"{warning_sign} {reason}"

def send_tg_msg(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

@st.cache_data(ttl=60)
def get_full_hunting_list():
    all_known_tickers = list(FULL_NAME_DB.keys())
    try:
        # 動態搜尋全市場當前熱門 (yf.Search)
        search = yf.Search("TW", max_results=30)
        dynamic_tickers = [s['symbol'] for s in search.stocks if '.TW' in s['symbol'] or '.TWO' in s['symbol']]
        return list(set(all_known_tickers + dynamic_tickers))
    except:
        return all_known_tickers

# ==========================================
# 🖥️ 介面
# ==========================================
st.set_page_config(page_title="RICHROY 終極戰情室", layout="wide")
st.title("🏹 RICHROY 終極「雙核心」量價監控系統")

with st.sidebar:
    st.header("⚙️ 偵測配置")
    system_power = st.toggle("🚀 啟動全市場獵殺", value=False)
    st.divider()
    min_up = st.slider("最低漲幅門檻 (%)", 0.0, 9.5, 3.0)
    min_vol = st.slider("量爆發倍數 (昨量比)", 0.5, 5.0, 1.2)
    interval = st.select_slider("掃描頻率 (分)", options=[1, 3, 5], value=1)
    custom_url = st.text_input("🔗 填入部署網址")

# ==========================================
# 🚀 執行獵殺
# ==========================================
if system_power:
    hunting_list = get_full_hunting_list()
    main_placeholder = st.empty()
    tw_tz = pytz.timezone('Asia/Taipei')
    
    with st.spinner(f"正在分析 {len(hunting_list)} 檔標的..."):
        raw_data = yf.download(hunting_list, period="2d", group_by='ticker', progress=False)
        winners = []
        
        for t in hunting_list:
            try:
                if t not in raw_data.columns.get_level_values(0): continue
                df = raw_data[t].dropna()
                if len(df) >= 2:
                    now_p = df['Close'].iloc[-1]
                    prev_p = df['Close'].iloc[-2]
                    change = ((now_p - prev_p) / prev_p) * 100
                    v_ratio = df['Volume'].iloc[-1] / df['Volume'].iloc[-2] if df['Volume'].iloc[-2] > 0 else 1.0
                    
                    if change >= min_up and v_ratio >= min_vol:
                        # 從資料庫抓名稱，抓不到才顯示代號
                        stock_name = FULL_NAME_DB.get(t, f"市場熱門({t.split('.')[0]})")
                        reason_with_sign = analyze_reason(t, change, v_ratio)
                        
                        winners.append({
                            "代號": t.split('.')[0],
                            "名稱": stock_name,
                            "價格": round(now_p, 2),
                            "漲幅": f"{change:.2f}%",
                            "量比": f"{v_ratio:.1f}x",
                            "狀態判斷": reason_with_sign
                        })
            except: continue

    with main_placeholder.container():
        now_time = datetime.now(tw_tz).strftime('%H:%M:%S')
        st.metric("🕒 系統掃描中", now_time, delta=f"名單總量: {len(hunting_list)} 檔")
        
        if winners:
            winners_df = pd.DataFrame(winners).sort_values(by="價格", ascending=False)
            st.error(f"🎯 偵測到 {len(winners)} 檔強勢金流！")
            # 讓表格看起來更有警示感
            st.dataframe(winners_df.style.highlight_max(axis=0, subset=['價格']), use_container_width=True)
            
            # --- TG 傳送 ---
            msg_body = "\n---\n".join([f"<b>[{w['代號']}] {w['名稱']}</b>\n{w['狀態判斷']}\n價:{w['價格']} ({w['漲幅']}) 量:{w['量比']}" for w in winners])
            send_tg_msg(f"🏹 <b>RICHROY 終極獵殺報警</b>\n⏰ {now_time}\n\n" + msg_body)
        else:
            st.info("尚未發現符合標準的標的。")

    time.sleep(interval * 60)
    st.rerun()