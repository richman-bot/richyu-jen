import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# ==========================================
# 🛑 核心配置：雙核心名單 (菁英 + 動態)
# ==========================================
TG_TOKEN = "8533923327:AAFfSDIxOuZDDMKdLkyOFznLafpKpTTdJok"
TG_CHAT_ID = "1009141944"

# 你的 82 檔核心菁英庫 (人工核實版)
ELITE_DATABASE = {
    "2408.TW": "南亞科", "2344.TW": "華邦電", "2337.TW": "旺宏", "8299.TWO": "群聯", 
    "3260.TWO": "威剛", "3006.TW": "晶豪科", "3363.TWO": "上詮", "4979.TWO": "華星光", 
    "3450.TW": "聯鈞", "3163.TWO": "波若威", "2359.TW": "所羅門", "2049.TW": "上銀",
    "1519.TW": "華城", "1513.TW": "中興電", "2330.TW": "台積電", "2317.TW": "鴻海",
    "2382.TW": "廣達", "3231.TW": "緯創", "2603.TW": "長榮", "2002.TW": "中鋼"
    # ... (此處可放入之前那 82 檔，為了精簡程式碼先列出核心指標)
}

# ==========================================
# 🛠️ 核心功能：獵殺與通報
# ==========================================
def send_tg_msg(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

@st.cache_data(ttl=60)
def get_full_hunting_list():
    """
    雙核心邏輯：菁英名單 + 全市場成交量熱門股
    """
    elite_tickers = list(ELITE_DATABASE.keys())
    try:
        # 動態抓取台股當下最熱門的 50 檔 (解決你說的漏掉漲起來的股票)
        search = yf.Search("TW", max_results=50)
        dynamic_tickers = [s['symbol'] for s in search.stocks if '.TW' in s['symbol'] or '.TWO' in s['symbol']]
        full_list = list(set(elite_tickers + dynamic_tickers))
        return full_list
    except:
        return elite_tickers

# ==========================================
# 🖥️ 戰情室主介面
# ==========================================
st.set_page_config(page_title="RICHROY 終極戰情室", layout="wide")
st.title("🏹 RICHROY 終極「雙核心」量價監控系統")

with st.sidebar:
    st.header("⚙️ 偵測配置")
    system_power = st.toggle("🚀 啟動全市場獵殺", value=False)
    
    st.divider()
    st.subheader("🎯 篩選標準")
    min_up = st.slider("最低漲幅門檻 (%)", 1.0, 9.5, 5.0)
    min_vol = st.slider("量爆發倍數 (昨量比)", 1.0, 5.0, 1.5)
    
    st.divider()
    interval = st.select_slider("掃描頻率 (分)", options=[1, 3, 5], value=1)
    custom_url = st.text_input("🔗 填入部署網址")

# ==========================================
# 🚀 執行獵殺
# ==========================================
if system_power:
    hunting_list = get_full_hunting_list()
    main_placeholder = st.empty()
    tw_tz = pytz.timezone('Asia/Taipei')
    
    with st.spinner(f"正在掃描全市場 {len(hunting_list)} 檔最具潛力標的..."):
        # 一次抓取所有數據
        raw_data = yf.download(hunting_list, period="2d", group_by='ticker', progress=False, threads=False)
        winners = []
        
        # 取得目前資料庫中有的代號
        active_tickers = raw_data.columns.levels[0] if isinstance(raw_data.columns, pd.MultiIndex) else [raw_data.name]
        
        for t in active_tickers:
            try:
                df = raw_data[t].dropna()
                if len(df) >= 2:
                    now_p = df['Close'].iloc[-1]
                    change = ((now_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                    
                    now_v = int(df['Volume'].iloc[-1])
                    v_ratio = now_v / int(df['Volume'].iloc[-2]) if int(df['Volume'].iloc[-2]) > 0 else 1.0
                    
                    if change >= min_up and v_ratio >= min_vol:
                        # 顯示名稱邏輯：如果是在精華名單就顯示名字，否則顯示代號
                        name = ELITE_DATABASE.get(t, f"市場飆股({t.split('.')[0]})")
                        winners.append({
                            "標的": name,
                            "價格": round(now_p, 2),
                            "漲幅": f"{change:.2f}%",
                            "量比": f"{v_ratio:.1f}x",
                            "狀態": "🔴漲停" if change >= 9.5 else "🚨帶量噴發"
                        })
            except: continue

    with main_placeholder.container():
        now_time = datetime.now(tw_tz).strftime('%H:%M:%S')
        st.metric("🕒 系統掃描中", now_time, delta=f"當前獵殺範圍: {len(hunting_list)} 檔")
        
        if winners:
            winners_df = pd.DataFrame(winners).sort_values(by="漲幅", ascending=False)
            st.error(f"🎯 偵測到 {len(winners)} 檔強勢金流！")
            st.table(winners_df)
            
            # --- TG 傳送 ---
            msg_body = "\n---\n".join([f"<b>{w['標的']}</b> {w['狀態']}\n價:{w['價格']} ({w['漲幅']}) 量:{w['量比']}" for w in winners])
            send_tg_msg(f"🏹 <b>RICHROY 終極獵殺報警</b>\n⏰ {now_time}\n\n" + msg_body + f"\n\n🔗 {custom_url}")
        else:
            st.info("掃描完成，目前市場暫無標的符合您的獵殺標準。")

    time.sleep(interval * 60)
    st.rerun()
else:
    st.info("💡 系統已就緒。開啟「啟動全市場獵殺」後，將自動監控精華名單與全市場突發標的。")
