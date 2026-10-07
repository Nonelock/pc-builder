import os
import logging
from threading import Lock

import telebot
from telebot import types


logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"].strip())
SITE_URL = "https://nonelock.github.io/pc-builder/"

bot = telebot.TeleBot(TOKEN)
waiting = set()
lock = Lock()


def menu():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "🖥 Открыть конфигуратор",
            url=SITE_URL,
        ),
        types.InlineKeyboardButton(
            "🐞 Сообщить об ошибке",
            callback_data="report",
        ),
        types.InlineKeyboardButton(
            "ℹ️ О проекте",
            callback_data="about",
        ),
    )
    return keyboard


def begin_report(chat_id):
    with lock:
        waiting.add(chat_id)

    bot.send_message(
        chat_id,
        "🐞 Опиши проблему одним текстовым сообщением.

↩️ /cancel — отменить.",
    )


def show_about(chat_id):
    bot.send_message(
        chat_id,
        "ℹ️ PC Сборщик

🖥 Подбор комплектующих для ПК.

🐞 Нашёл ошибку? Отправь /report.",
        reply_markup=menu(),
    )


@bot.message_handler(commands=["start", "site", "help"])
def start(message):
    if message.chat.type != "private":
        bot.reply_to(message, "💬 Напиши мне в личные сообщения.")
        return

    text = "👋 Добро пожаловать в PC Сборщик!

🖥 Открой конфигуратор или выбери действие ниже."

    if message.from_user.id == ADMIN_ID:
        text += "

👑 Ты администратор этого бота."

    bot.send_message(message.chat.id, text, reply_markup=menu())


@bot.message_handler(commands=["id"])
def show_id(message):
    bot.reply_to(message, f"🆔 Твой Telegram ID: {message.from_user.id}")


@bot.message_handler(commands=["report"])
def report_command(message):
    if message.chat.type != "private":
        bot.reply_to(message, "💬 Напиши мне в личные сообщения.")
        return

    begin_report(message.chat.id)


@bot.message_handler(commands=["cancel"])
def cancel(message):
    with lock:
        waiting.discard(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👌 Отправка отчёта отменена.",
        reply_markup=menu(),
    )


@bot.message_handler(commands=["about"])
def about_command(message):
    show_about(message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data in ("report", "about"))
def handle_button(call):
    bot.answer_callback_query(call.id)

    if not call.message:
        return

    if call.message.chat.type != "private":
        return

    chat_id = call.message.chat.id

    if call.data == "report":
        begin_report(chat_id)
    else:
        show_about(chat_id)


@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.chat.type != "private":
        return

    chat_id = message.chat.id

    with lock:
        pending = chat_id in waiting

    if not pending:
        bot.send_message(
            chat_id,
            "👇 Выбери действие в меню.",
            reply_markup=menu(),
        )
        return

    user = message.from_user
    username = f"@{user.username}" if user.username else "без username"
    header = f"🐞 Новый отчёт

👤 От: {user.first_name} ({username})
🆔 ID: {user.id}

📩 Сообщение пользователя — ниже:"

    try:
        bot.send_message(ADMIN_ID, header)
        bot.forward_message(ADMIN_ID, chat_id, message.message_id)
    except Exception as error:
        detail = str(error).replace(TOKEN, "[TOKEN HIDDEN]")
        logging.error("Report delivery failed: %s", detail)

        bot.send_message(
            chat_id,
            "❌ Не удалось доставить отчёт. Попробуй позже или нажми /cancel.",
        )
        return

    with lock:
        waiting.discard(chat_id)

    bot.send_message(
        chat_id,
        "✅ Спасибо! Отчёт доставлен разработчику.",
        reply_markup=menu(),
    )


if __name__ == "__main__":
    bot.infinity_polling(timeout=30, long_polling_timeout=30)