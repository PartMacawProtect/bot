from aiogram import Router
from aiogram.types import Message, BusinessOpeningHours, BusinessOpeningHoursInterval
from groq import AsyncGroq
import aiohttp

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)

# ID владельца бизнес-аккаунта
BUSINESS_OWNER_ID = 5999387348


async def get_opening_hours_from_user(user_id: int):
    """
    Получает часы работы пользователя через Telegram Bot API.
    Используем метод getUserBusinessOpeningHours.
    """
    url = f"https://api.telegram.org/bot{secrets.token}/getUserBusinessOpeningHours"
    
    print(f"🔍 Запрашиваем opening_hours для user_id: {user_id}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"user_id": user_id}) as resp:
            data = await resp.json()

    print(f"📡 Ответ от Telegram API: {data}")

    if not data.get("ok"):
        print(f"⚠️ API вернул ошибку: {data.get('description')}")
        return None

    oh_data = data.get("result")
    if not oh_data:
        print(f"⚠️ opening_hours не найдены")
        return None

    print(f"✅ opening_hours найдены: {oh_data}")
    
    # Преобразуем в объект BusinessOpeningHours
    try:
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
    except Exception as e:
        print(f"❌ Ошибка при преобразовании opening_hours: {e}")
        return None


@router.business_message()
async def business_message_handler(message: Message):
    try:
        # Получаем часы работы владельца бизнес-аккаунта
        opening_hours = await get_opening_hours_from_user(BUSINESS_OWNER_ID)
        
        if opening_hours:
            print(f"✅ Часы работы получены успешно")
            # Проверяем рабочие часы
            if not check_opening_hours(opening_hours):
                print("⏱ Сейчас рабочее время. Бот молчит.")
                return
        else:
            print("⚠️ Не удалось получить часы работы, отвечаем на все сообщения")

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        import traceback
        traceback.print_exc()

    # --- ОТВЕЧАЕМ НА СООБЩЕНИЕ ---
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

