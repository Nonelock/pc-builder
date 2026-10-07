import os
import logging
import threading
from html import escape

import telebot
from telebot import types


logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"].strip())

SITE_URL = "https://nonelock.github.io/pc-builder/"

bot = telebot.TeleBot(TOKEN)

waiting = set()
lock = threading.Lock()


def menu():
    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton(
            "🖥 Открыть конфигуратор",
            url=SITE_URL
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "🐞 Сообщить об ошибке",
            callback_data="report"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "ℹ️ О проекте",
            callback_data="about"
        )
    )

    return markup


def begin_report(chat_id):
    with lock:
        waiting.add(chat_id)

    bot.send_message(
        chat_id,
        "🐞 Опиши проблему одним текстовым сообщением.

"
        "Например: «Не отображается видеокарта» "
        "или «Сайт неправильно проверяет совместимость».

"
        "↩️ /cancel — отменить отправку."
    )


@bot.message_handler(commands=["start", "site", "help"])
def start(message):
    if message.chat.type != "private":
        bot.reply_to(
            message,
            "💬 Напиши мне в личные сообщения."
        )
        return

    text = (
        "👋 Добро пожаловать в PC Сборщик!

"
        "🔧 Подбирай комплектующие для своего ПК.
"
        "🧩 Проверяй базовую совместимость деталей.
"
        "🐞 Сообщай об ошибках — поможем проекту стать лучше!"
    )

    if message.from_user.id == ADMIN_ID:
        text += "

👑 Ты администратор этого бота."

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=menu()
    )


@bot.message_handler(commands=["id"])
def show_id(message):
    bot.reply_to(
        message,
        f"🆔 Твой Telegram ID: {message.from_user.id}"
    )


@bot.message_handler(commands=["report"])
def report_command(message):
    if message.chat.type == "private":
        begin_report(message.chat.id)
    else:
        bot.reply_to(
            message,
            "💬 Для отправки отчёта напиши мне в личные сообщения."
        )


@bot.message_handler(commands=["cancel"])
def cancel(message):
    with lock:
        waiting.discard(message.chat.id)

    bot.send_message(
        message.chat.id,
        "👌 Отправка отчёта отменена.",
        reply_markup=menu()
    )


@bot.message_handler(commands=["about"])
def about(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ О проекте PC Сборщик

"
        "🖥 Конфигуратор для подбора комплектующих "
        "и базовой проверки совместимости ПК.

"
        "⚠️ Перед покупкой сверяй характеристики "
        "с документацией производителей.

"
        "💡 Нашёл неточность? Отправь /report.",
        reply_markup=menu()
    )


@bot.callback_query_handler(
    func=lambda call: call.data in ["report", "about"]
)
def callback(call):
    bot.answer_callback_query(call.id)

    if not call.message:
        return

    if call.message.chat.type != "private":
        return

    if call.data == "report":
        begin_report(call.message.chat.id)
    elif call.data == "about":
        about(call.message)


@bot.message_handler(content_types=["text"])
def receive_text(message):
    if message.chat.type != "private":
        return

    with lock:
        pending = message.chat.id in waiting

    if not pending:
        bot.send_message(
            message.chat.id,
            "👇 Выбери действие в меню.

"
            "🐞 Для отправки отчёта используй /report.",
            reply_markup=menu()
        )
        return

    user = message.from_user
    username = (
        "@" + user.username
        if user.username
        else "без username"
    )

    header = (
        "🐞 <b>Новый отчёт об ошибке</b>

"
        f"👤 От: {escape(user.first_name)} "
        f"({escape(username)})
"
        f"🆔 ID: <code>{user.id}</code>

"
        "📩 Сообщение пользователя — ниже:"
    )

    try:
        bot.send_message(
            ADMIN_ID,
            header,
            parse_mode="HTML"
        )

        bot.forward_message(
            ADMIN_ID,
            message.chat.id,
            message.message_id
        )

    except Exception as error:
        detail = str(error).replace(
            TOKEN,
            "[TOKEN HIDDEN]"
        )

        logging.error(
            "Report delivery failed: %s: %s",
            type(error).__name__,
            detail
        )

        bot.send_message(
            message.chat.id,
            "❌ Отчёт не доставлен.

"
            "🔄 Попробуй отправить сообщение позже "
            "или нажми /cancel.
"
            "📝 Причина записана в журнал сервиса."
        )
        return

    with lock:
        waiting.discard(message.chat.id)

    bot.send_message(
        message.chat.id,
        "✅ Спасибо! Отчёт доставлен разработчику.

"
        "💚 Ты помогаешь улучшать PC Сборщик!",
        reply_markup=menu()
    )


if __name__ == "__main__":
    print(
        "🚀 PC Сборщик бот запущен",
        flush=True
    )

    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30
    )