import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz
import time

# ==========================================
# 🛑 核心參數設定
# ==========================================
TG_TOKEN = "8533923327:AAFfSDIxOuZDDMKdLkyOFznLafpKpTTdJok"
TG_CHAT_ID = "1009141944"

# 精準市場分類 (避免 Yahoo Error)
LISTED_TW = ["2330", "2317", "2454", "2382", "3231", "3017", "1513", "1519", "2603", "2609", "2618", "2881", "2882", "2303", "2301", "2357", "3711", "2449", "2408", "3037"]
OTC_TWO = ["3324", "3661", "3443", "6669", "3131", "3363", "6451", "4966", "8358", "4562"]

# ==========================================
# 🛠️ 核心功能
# ==========================================
def send_tg_msg(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload, timeout=10)
    except: pass

@st.cache_data(ttl=30)
def get_market_data(tickers):
    # 使用 threads=False 增加穩定性，避免卡在 Stopping
    data = yf.download(tickers, period="20d", group_by='ticker', progress=False, threads=False)
    return data

# ==========================================
# 📈 戰情室介面
# ==========================================
st.set_page_config(page_title="RICHROY 穩定監控", layout="wide")
st.title("🏹 RICHROY 500強量價獵人 (Bug 修復版)")

with st.sidebar:
    st.header("⚙️ 系統控制")
    system_power = st.toggle("🔥 啟動全天候監控", value=False)
    interval = st.select_slider("掃描頻率 (分鐘)", options=[1, 3, 5, 10, 30], value=1)
    custom_url = st.text_input("🔗 您的部署網址", placeholder="https://xxx.streamlit.app")

if system_power:
    main_placeholder = st.empty()
    tw_tz = pytz.timezone('Asia/Taipei')
    now_time = datetime.now(tw_tz).strftime('%H:%M:%S')
    
    all_tickers = [f"{c}.TW" for c in LISTED_TW] + [f"{c}.TWO" for c in OTC_TWO]
    
    with st.spinner(f"巡邏中... {now_time}"):
        raw_data = get_market_data(all_tickers)
        winners = []
        
        for full_code in all_tickers:
            if full_code in raw_data.columns.levels[0]:
                df = raw_data[full_code].dropna()
                if len(df) >= 2:
                    now_p = df['Close'].iloc[-1]
                    prev_p = df['Close'].iloc[-2]
                    change = ((now_p - prev_p) / prev_p) * 100
                    
                    now_vol = int(df['Volume'].iloc[-1])
                    avg_vol = df['Volume'].mean()
                    vol_ratio = now_vol / avg_vol if avg_vol > 0 else 1.0
                    
                    if change >= 7.0:
                        # 這裡統一使用「狀態」
                        status_str = "🚨【即將漲停】" if change < 9.5 else "🔴【已漲停】"
                        winners.append({
                            "代號": full_code.split('.')[0],
                            "現價": round(now_p, 2),
                            "漲幅": f"{change:.2f}%",
                            "今日成交量": f"{now_vol:,}",
                            "量增比": f"{vol_ratio:.1f}x",
                            "狀態": status_str
                        })

    with main_placeholder.container():
        st.metric("🕒 最後掃描時間", now_time)
        if winners:
            st.error(f"🔥 偵測到 {len(winners)} 檔強勢股！")
            st.table(winners)
            
            # --- Telegram 訊息組合 (修正後的 Key) ---
            msg_items = []
            for w in winners:
                # 這裡確保使用的是 w['狀態'] 而非 w['status']
                item = (f"{w['狀態']} <b>{w['代號']}</b>\n"
                        f"💰 價：{w['現價']} ({w['漲幅']})\n"
                        f"📊 量：{w['今日成交量']} (增幅{w['量增比']})")
                msg_items.append(item)
            
            footer = f"\n\n🔗 <b>戰情室連結：</b>\n{custom_url}" if custom_url else ""
            full_msg = f"🌟 <b>RICHROY 量價警報</b>\n⏰ {now_time}\n\n" + "\n---\n".join(msg_items) + footer
            send_tg_msg(full_msg)
        else:
            st.info("目前市場平靜，暫無符合條件標的。")

    time.sleep(interval * 60)
    st.rerun()
else:
    st.info("系統待命中，請開啟左側開關。")