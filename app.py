import time
import threading
import os
import schedule
import streamlit as st
import requests
from langchain_groq import ChatGroq

# ==================== БЕЗОПАСНОЕ ЧТЕНИЕ КЛЮЧЕЙ ====================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# ==================================================================

st.set_page_config(page_title="ETH Auto-Analyst", page_icon="🤖", layout="centered")

def send_telegram_message(text: str):
    """Отправка живого отчета в Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Ошибка: Не заданы TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"📡 Telegram статус: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def get_eth_market_data():
    """Получение актуальных данных по ETH через публичный API CoinGecko (без банов IP)"""
    print("🌐 Запрос свежих данных через CoinGecko API...")
    
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true"
    }
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    eth_data = data.get("ethereum", {})
    price = eth_data.get("usd", 3000.0)
    change_24h = eth_data.get("usd_24h_change", 0.0)
    volume_24h = eth_data.get("usd_24h_vol", 1000000000.0)
    
    print(f"✅ Актуальная цена ETH: ${price}")

    return {
        "price": price,
        "change_24h": change_24h,
        "volume_24h": volume_24h,
        "open_interest": 2000000.0,  # Заглушка для стабильности
        "funding_rate": 0.01
    }

def generate_crypto_report():
    """Сбор свежих данных, анализ через Groq LLM и отправка"""
    print("🔄 Запуск генерации актуального отчета...")
    try:
        data = get_eth_market_data()
        
        if not GROQ_API_KEY:
            print("❌ Ошибка: Не найден GROQ_API_KEY")
            return

        print("🤖 Передаем свежие метрики в Groq LLM...")
        prompt = f"""
        Ты — профессиональный крипто-аналитик. Проанализируй актуальные данные Ethereum (ETH) прямо сейчас:
        - Текущая цена: ${data['price']:,.2f}
        - Изменение за 24ч: {data['change_24h']:.2f}%
        - Объем за 24ч: ${data['volume_24h']:,.0f}

        Дай четкий, краткий структурированный аналитический отчет на русском языке:
        1. Общая рыночная тенденция (Бычий / Медвежий / Флэт)
        2. Краткий разбор ценового движения за сутки
        3. Торговый вердикт: LONG / SHORT / WAIT
        4. Уровень риска: Низкий / Средний / Высокий
        """
        
        llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2
        )
        
        response = llm.invoke(prompt)
        report_text = response.content
        print("✅ Анализ от Groq успешно сгенерирован!")
        
        tg_message = f"🚨 *АКТУАЛЬНЫЙ АНАЛИТИЧЕСКИЙ ОТЧЕТ ПО ETH*\n\n{report_text}"
        send_telegram_message(tg_message)
        
    except Exception as e:
        print(f"❌ ОШИБКА в generate_crypto_report: {e}")

if "is_started" not in st.session_state:
    st.session_state["is_started"] = True
    def run_scheduler():
        schedule.every(1).hours.do(generate_crypto_report)
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    print("🚀 Планировщик авто-отчетов запущен в фоновом режиме.")

st.title("🤖 ETH Auto-Analyst Bot")
st.success("Сервер работает в облаке 24/7. Отчеты уходят каждый час.")

if st.button("📨 Запросить свежий отчет прямо сейчас"):
    with st.spinner("Получаем актуальные данные и анализируем..."):
        generate_crypto_report()
        st.success("Готово! Проверьте свой Telegram и логи.")
