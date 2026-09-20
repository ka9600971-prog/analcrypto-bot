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
    """Получение актуальных рыночных данных с Binance Futures в реальном времени"""
    print("🌐 Запрос свежих данных с Binance Futures...")
    
    exchange = ccxt.binanceusdm({
        'timeout': 15000,
        'enableRateLimit': True,
    })
    symbol = 'ETH/USDT'
    
    ticker = exchange.fetch_ticker(symbol)
    print(f"✅ Актуальная цена ETH: ${ticker['last']}")
    
    funding_rate = 0.01
    open_interest = 2000000.0
    
    try:
        time.sleep(1.2)
        funding_info = exchange.fetch_funding_rate(symbol)
        funding_rate = funding_info['fundingRate'] * 100
    except Exception as e:
        print(f"⚠️ Предупреждение по фандингу: {e}")
        
    try:
        time.sleep(1.2)
        oi_info = exchange.fetch_open_interest(symbol)
        open_interest = oi_info['openInterestAmount']
    except Exception as e:
        print(f"⚠️ Предупреждение по Open Interest: {e}")

    return {
        "price": ticker['last'],
        "change_24h": ticker['percentage'],
        "volume_24h": ticker['quoteVolume'],
        "open_interest": open_interest,
        "funding_rate": funding_rate
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
        Ты — профессиональный крипто-аналитик. Проанализируй актуальные данные фьючерса ETHUSDT с Binance Futures прямо сейчас:
        - Текущая цена: ${data['price']:,.2f}
        - Изменение за 24ч: {data['change_24h']:.2f}%
        - Объем за 24ч: ${data['volume_24h']:,.0f}
        - Open Interest (Открытый интерес): {data['open_interest']:,.2f} ETH
        - Funding Rate (Ставка финансирования): {data['funding_rate']:.4f}%

        Дай четкий, краткий структурированный аналитический отчет на русском языке:
        1. Общая рыночная тенденция (Бычий / Медвежий / Флэт)
        2. Оценка метрик OI и Funding (есть ли перегрев лонгов/шортов)
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
        
        tg_message = f"🚨 *АКТУАЛЬНЫЙ АНАЛИТИЧЕСКИЙ ОТЧЕТ ПО ETHUSDT*\n\n{report_text}"
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

st.title("🤖 ETHUSDT Auto-Analyst Bot")
st.success("Сервер работает в облаке 24/7. Отчеты уходят каждый час.")

if st.button("📨 Запросить свежий отчет прямо сейчас"):
    with st.spinner("Получаем актуальные данные с Binance и анализируем..."):
        generate_crypto_report()
        st.success("Готово! Проверьте свой Telegram и логи Render.")
