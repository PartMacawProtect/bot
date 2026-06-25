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
        # 1. Запрашиваем актуальную информацию о твоем бизнес-аккаунте
        business_conn = await bot.get_business_connection(message.business_connection_id)

        # 2. Проверяем рабочие часы.
        # Если часы настроены — проверяем, рабочее ли сейчас время.
        # Если часы НЕ настроены — бот отвечает всегда.
        opening_hours = getattr(business_conn, "opening_hours", None)
        if opening_hours:
            if not check_opening_hours(opening_hours):
                print("⏱ Сейчас рабочее время. Бот молчит.")
                return  # Выходим из функции, бот ничего не отвечает

    except Exception as e:
        print(f"⚠️ Ошибка при проверке рабочих часов: {e}")
        # Если не удалось проверить время — продолжаем и отвечаем, как при ненастроенных часах

        # --- ВСЁ ЧТО НИЖЕ — СРАБОТАЕТ В НЕРАБОЧЕЕ ВРЕМЯ ИЛИ ЕСЛИ ЧАСЫ НЕ НАСТРОЕНЫ ---
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