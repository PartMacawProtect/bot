from aiogram import Router
from aiogram.types import Message, BusinessOpeningHours, BusinessOpeningHoursInterval
from groq import AsyncGroq
import aiohttp

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


async def get_opening_hours_raw(business_connection_id: str):
    """
    Запрашивает данные бизнес-подключения напрямую через Telegram Bot API
    и возвращает объект BusinessOpeningHours, собранный из сырого JSON-ответа.
    Это нужно потому, что aiogram не маппит поле opening_hours в своём враппере.
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
        print("⚠️ opening_hours не найдены в ответе Telegram API")
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
        # 1. Запрашиваем рабочие часы напрямую из Telegram Bot API
        opening_hours = await get_opening_hours_raw(message.business_connection_id)

        # 2. Проверяем рабочие часы
        if opening_hours and not check_opening_hours(opening_hours):
            print("⏱ Сейчас рабочее время. Бот молчит.")
            return

        if not opening_hours:
            print("⚠️ Не удалось получить рабочие часы, но продолжаем отвечать на сообщение")

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        return

    # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ ТОЛЬКО В НЕРАБОЧЕЕ ВРЕМЯ ---
    print(f"📥 Бот поймал сообщение от @{message.from_user.username}: {message.text}")

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
        print("📤 Ответ успешно отправлен!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или отправки: {e}")

