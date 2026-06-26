from aiogram import Router
from aiogram.types import Message
from groq import AsyncGroq

from app.settings import secrets, bot
from app.views import system_prompt
from app.utils.opening_hours import check_opening_hours  # Импортируем функцию проверки времени

router = Router()
client = AsyncGroq(api_key=secrets.groq_api_key)


@router.business_message()
async def business_message_handler(message: Message):
    # Try to get opening_hours directly from the message object.
    # BusinessConnection.opening_hours is not available in the current aiogram
    # version, so we fall back to always responding when it can't be retrieved.
    opening_hours = getattr(message, "opening_hours", None)
    if opening_hours is not None:
        if not check_opening_hours(opening_hours):
            print("⏱ Сейчас рабочее время. Бот молчит.")
            return  # Выходим из функции, бот ничего не отвечает
    else:
        print("⏱ Часы работы недоступны — отвечаем на все сообщения.")

        # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ ТОЛЬКО В НЕРАБОЧЕЕ ВРЕМЯ (ИЛИ ВСЕГДА, ЕСЛИ ЧАСЫ НЕ НАСТРОЕНЫ) ---
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
        print("📤 Ответ успешно отправлен другу!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или отправки: {e}")