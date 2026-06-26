from aiogram import Router
from aiogram.types import Message, BusinessOpeningHours, BusinessOpeningHoursInterval
from groq import AsyncGroq
import aiohttp

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours  # Импортируем функцию проверки времени

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


async def get_opening_hours_raw(business_connection_id: str):
    """
    Запрашивает данные бизнес-подключения напрямую через Telegram Bot API
    и возвращает объект BusinessOpeningHours, собранный из сырого JSON-ответа.
    Это нужно потому, что aiogram не маппит поле opening_hours в своём враппере
    (BusinessConnection объект не содержит атрибут opening_hours в текущей версии).
    """
    url = f"https://api.telegram.org/bot{secrets.token}/getBusinessConnection"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"business_connection_id": business_connection_id}) as resp:
            data = await resp.json()

    if not data.get("ok"):
        print(f"⚠️ Telegram API вернул ошибку: {data}")
        return None

    conn_data = data["result"]
    oh_data = conn_data.get("opening_hours")
    if not oh_data:
        return None

    # Собираем объект BusinessOpeningHours из сырых данных
    intervals = [
        BusinessOpeningHoursInterval(
            opening_minute=interval["opening_minute"],
            closing_minute=interval["closing_minute"],
        )
        for interval in oh_data.get("opening_hours", [])
    ]
    return BusinessOpeningHours(
        time_zone_name=oh_data["time_zone_name"],
        opening_hours=intervals,
    )


@router.business_message()
async def business_message_handler(message: Message):
    try:
        # 1. Запрашиваем рабочие часы напрямую из Telegram Bot API,
        #    минуя aiogram-враппер, который не маппит поле opening_hours.
        opening_hours = await get_opening_hours_raw(message.business_connection_id)

        # 2. Проверяем рабочие часы.
        # Если часы не настроены в Telegram вообще ИЛИ если check_opening_hours вернула False (сейчас рабочее время)
        if not opening_hours or not check_opening_hours(opening_hours):
            print("⏱ Сейчас рабочее время (или часы работы не настроены в ТГ). Бот молчит.")
            return  # Выходим из функции, бот ничего не отвечает

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        # Если не удалось проверить время, на всякий случай выходим, чтобы не ответить посреди рабочего дня
        return

        # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ ТОЛЬКО В НЕРАБОЧЕЕ ВРЕМЯ ---
    print(f"📥 Нерабочее время! Бот поймал сообщение от @{message.from_user.username}: {message.text}")

    try:
        print("🤖 Отправляем запрос в Groq API...")
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": message.text}
            ]
        )
        answer = response.choices[0].message.content
        print(f"🎯 Ответ от Groq получен: {answer}")

        await bot.send_message(
            chat_id=message.chat.id,
            text=answer,
            business_connection_id=message.business_connection_id
        )
        print("📤 Ответ успешно отправлен другу!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или отправки: {e}")