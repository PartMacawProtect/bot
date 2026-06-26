from aiogram import Router
from aiogram.types import Message
from groq import AsyncGroq
import aiohttp

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


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
        print(f"⚠️ API вернул ошибку")
        return None

    oh_data = data.get("result")
    if not oh_data:
        print(f"⚠️ opening_hours не найдены")
        return None

    print(f"✅ opening_hours найдены: {oh_data}")
    return oh_data


@router.business_message()
async def business_message_handler(message: Message):
    try:
        # Получаем часы работы пользователя
        user_id = message.from_user.id
        opening_hours_data = await get_opening_hours_from_user(user_id)
        
        if opening_hours_data:
            print(f"✅ Часы работы получены успешно")
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

