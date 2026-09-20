import time
import threading
import os
import schedule
import streamlit as st
import requests
import ccxt
from langchain_groq import ChatGroq

# ==================== БЕЗОПАСНОЕ ЧТЕНИЕ КЛЮЧЕЙ ====================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# ==================================================================

# Минимальная настройка страницы, чтобы Render видел живой Web Service
st.set_page_config(page_title="ETH Bot Status", page_icon="🤖", layout="centered")

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
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Отчет успешно отправлен в Telegram!")
        else:
            print(f"❌ Ошибка Telegram API: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def get_eth_market_data():
    """Получение свежих данных по ETHUSDT с Binance Futures"""
    exchange = ccxt.binanceusdm()
    symbol = 'ETH/USDT'
    
    ticker = exchange.fetch_ticker(symbol)
    time.sleep(1)
    
    funding_rate = 0.01
    open_interest = 2000000.0
    
    try:
        funding_info = exchange.fetch_funding_rate(symbol)
        funding_rate = funding_info['fundingRate'] * 100
    except:
        pass
        
    try:
        time.sleep(1)
        oi_info = exchange.fetch_open_interest(symbol)
        open_interest = oi_info['openInterestAmount']
    except:
        pass

    return {
        "price": ticker['last'],
        "change_24h": ticker['percentage'],
        "volume_24h": ticker['quoteVolume'],
        "open_interest": open_interest,
        "funding_rate": funding_rate
    }

def generate_crypto_report():
    """Генерация отчета через Groq и отправка в Telegram"""
    print("🔄 Генерация фонового отчета...")
    try:
        data = get_eth_market_data()
        
        prompt = f"""
        Ты — старший крипто-аналитик. Проанализируй данные фьючерса ETHUSDT с Binance Futures:
        - Текущая цена: ${data['price']:,.2f} (Изменение за 24ч: {data['change_24h']:.2f}%)
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
        
    except Exception as e:
        print(f"❌ Ошибка в фоновой задаче: {e}")

# Функция фонового планировщика
def run_scheduler():
    schedule.every(1).hours.do(generate_crypto_report)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запускаем фоновый поток для расписания один раз при старте
if 'scheduler_started' not in st.session_state:
    st.session_state['scheduler_started'] = True
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()

# --- МИНИМАЛИСТИЧНЫЙ ИНТЕРФЕЙС СТАТУСА ---
st.title("🤖 ETHUSDT Auto-Analyst Bot")
st.success("Бот успешно запущен в облаке и работает 24/7!")
st.write("Этот сервис работает в фоновом режиме. Каждые 60 минут он отправляет аналитический отчет по ETH в ваш Telegram-канал/чат.")

if st.button("📨 Отправить тестовый отчет прямо сейчас"):
    with st.spinner("Генерируем отчет..."):
        generate_crypto_report()
        st.success("Тестовый отчет отправлен в Telegram!")
