import time
import threading
import os
import schedule
import streamlit as st
import requests
import ccxt
from langchain_groq import ChatGroq

# ==================== БЕЗОПАСНОЕ ЧТЕНИЕ КЛЮЧЕЙ ====================
# Ключи подтягиваются из системных переменных (на Render.com настраиваются в панели Environment)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# ==================================================================

st.set_page_config(page_title="Crypto Analytics Dash", page_icon="📈", layout="centered")

def send_telegram_message(text: str):
    """Отправка сообщения в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Ошибка: Не заданы токен или Chat ID для Telegram")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def get_eth_market_data():
    """Получение свежих данных по ETHUSDT с Binance Futures с задержками от банов"""
    exchange = ccxt.binanceusdm()
    symbol = 'ETH/USDT'
    
    # Делаем паузы между запросами, чтобы API Binance не банило общий IP облачного сервера
    ticker = exchange.fetch_ticker(symbol)
    time.sleep(1)
    funding_info = exchange.fetch_funding_rate(symbol)
    time.sleep(1)
    oi_info = exchange.fetch_open_interest(symbol)
    
    return {
        "price": ticker['last'],
        "change_24h": ticker['percentage'],
        "volume_24h": ticker['quoteVolume'],
        "open_interest": oi_info['openInterestAmount'],
        "funding_rate": funding_info['fundingRate'] * 100
    }

def generate_crypto_report():
    """Генерация отчета через Groq и отправка в Telegram"""
    try:
        data = get_eth_market_data()
        
        prompt = f"""
        Ты — старший крипто-аналитик. Проанализируй данные фьючерса ETHUSDT с Binance Futures:
        - Текущая цена: ${data['price']:,.2f} (Изменение за 24ч: {data['change_24h']:,.2f}%)
        - Объем за 24ч: ${data['volume_24h']:,.0f}
        - Open Interest: {data['open_interest']:,.2f} ETH
        - Funding Rate: {data['funding_rate']:.4f}%

        Сделай краткий структурированный отчет на русском языке:
        1. Состояние рынка (Бычий / Медвежий / Флэт)
        2. Анализ метрик (OI и Funding Rate)
        3. Вердикт: LONG / SHORT / WAIT
        4. Уровень риска (Низкий / Средний / Высокий)
        """
        
        llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="openai/gpt-oss-20b",
            temperature=0.2
        )
        
        response = llm.invoke(prompt)
        report_text = response.content
        
        tg_message = f"⏰ *ЕЖАСОВОЙ АВТО-ОТЧЕТ ПО ETHUSDT*\n\n{report_text}"
        send_telegram_message(tg_message)
        print("✅ Ежечасовой отчет успешно отправлен в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка в фоновой задаче: {e}")

# Функция фонового планировщика
def run_scheduler():
    schedule.every(1).hours.do(generate_crypto_report)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запускаем фоновый поток для расписания один раз при старте приложения
if 'scheduler_started' not in st.session_state:
    st.session_state['scheduler_started'] = True
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

# --- ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.title("📈 Панель Аналитики ETHUSDT")
st.caption("Веб-панель активна. Защита от лимитов биржи включена. Авто-рассылка работает.")

if st.button("🚀 Запустить анализ вручную", type="primary", use_container_width=True):
    with st.spinner("Запрашиваем данные с биржи и генерируем отчет..."):
        try:
            data = get_eth_market_data()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Цена ETH", f"${data['price']:,.2f}", f"{data['change_24h']:,.2f}%")
            col2.metric("Open Interest", f"{data['open_interest']:,.0f} ETH")
            col3.metric("Funding Rate", f"{data['funding_rate']:,.4f}%")
            
            prompt = f"""
            Ты — старший крипто-аналитик. Проанализируй данные фьючерса ETHUSDT с Binance Futures:
            - Текущая цена: ${data['price']:,.2f} (Изменение за 24ч: {data['change_24h']:,.2f}%)
            - Объем за 24ч: ${data['volume_24h']:,.0f}
            - Open Interest: {data['open_interest']:,.2f} ETH
            - Funding Rate: {data['funding_rate']:.4f}%

            Сделай краткий структурированный отчет на русском языке:
            1. Состояние рынка (Бычий / Медвежий / Флэт)
            2. Анализ метрик (OI и Funding Rate)
            3. Вердикт: LONG / SHORT / WAIT
            4. Уровень риска (Низкий / Средний / Высокий)
            """
            
            llm = ChatGroq(
                groq_api_key=GROQ_API_KEY,
                model_name="openai/gpt-oss-20b",
                temperature=0.2
            )
            
            response = llm.invoke(prompt)
            report_text = response.content
            
            st.subheader("📋 Результат анализа:")
            st.write(report_text)
            
            tg_message = f"📊 *РУЧНОЙ ОТЧЕТ ПО ETHUSDT*\n\n{report_text}"
            send_telegram_message(tg_message)
            
            st.success("✅ Отчет выведен на экран и отправлен в Telegram!")

        except Exception as e:
            st.error(f"Произошла ошибка: {str(e)}")
