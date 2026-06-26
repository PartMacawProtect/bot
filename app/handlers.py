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
    try:
        # Проверяем, что ID бизнес-соединения вообще существует в сообщении
        if not message.business_connection_id:
            return

        # 1. Запрашиваем информацию о бизнес-соединении
        business_conn = await bot.get_business_connection(business_connection_id=message.business_connection_id)

        # 2. Рабочие часы привязаны к чату аккаунта. Запрашиваем полную информацию о чате владельца бизнеса.
        chat_info = await bot.get_chat(chat_id=business_conn.user_chat_id)
        opening_hours = chat_info.business_opening_hours

        # 3. Проверяем рабочие часы.
        # Если часы не настроены в Telegram вообще ИЛИ если check_opening_hours вернула False (сейчас рабочее время)
        if not opening_hours or not check_opening_hours(opening_hours):
            print("⏱ Сейчас рабочее время (или часы работы не настроены в ТГ). Бот молчит.")
            return  # Выходим из функции, бот ничего не отвечает

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        # Если не удалось проверить время, на всякий случай выходим, чтобы случайно не ответить в рабочее время
        return

    # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ ТОЛЬКО В НЕРАБОЧЕЕ ВРЕМЯ ---
    
    # Оформляем имя пользователя для логов
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    print(f"📥 Нерабочее время! Бот поймал сообщение от {user_info}: {message.text}")

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

        # Отправляем ответ в рамках того же бизнес-соединения
        await bot.send_message(
            chat_id=message.chat.id,
            text=answer,
            business_connection_id=message.business_connection_id
        )
        print("📤 Ответ успешно отправлен пользователю!")

    except Exception as e:
        print(f"❌ Ошибка в блоке Groq или при отправке сообщения: {e}")
