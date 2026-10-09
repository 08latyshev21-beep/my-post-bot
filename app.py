
import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.environ["BOT_TOKEN"]
SECRET = os.environ["WEBHOOK_SECRET"]
API = f"https://api.telegram.org/bot{TOKEN}"

# Первая версия: временное хранение в памяти
users = {}

MENU = [
    ["📝 Создать пост", "📅 Контент-план"],
    ["📢 Рекламный пост", "✏️ Изменить пост"],
    ["📂 Мои проекты", "⚙️ Настройки"]
]

def send(chat, text, keyboard=None):
    data = {"chat_id": chat, "text": text}
    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }
    requests.post(
        f"{API}/sendMessage",
        json=data,
        timeout=15
    ).raise_for_status()

def state(user):
    return users.setdefault(user, {
        "channel": None,
        "draft": None,
        "mode": None
    })

@app.get("/")
def home():
    return "My Post Bot is running", 200

@app.post("/webhook")
def webhook():
    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != SECRET:
        return "Forbidden", 403

    update = request.get_json(silent=True) or {}
    msg = update.get("message", {})
    chat = msg.get("chat", {})

    if chat.get("type") != "private":
        return "OK", 200

    user = chat.get("id")
    text = msg.get("text", "")
    if not user or not text:
        return "OK", 200

    s = state(user)

    try:
        if text == "/start" or text == "🏠 Меню":
            s["mode"] = None
            send(user,
                 "⚡ MY POST BOT\n\n"
                 "Создавайте и публикуйте посты!",
                 MENU)

        elif text == "⚙️ Настройки":
            send(user,
                 "⚙️ Настройки\n\n"
                 "Для подключения канала отправьте "
                 "его @username.\n"
                 "Бот должен быть администратором "
                 "с правом публикации.",
                 [["🔗 Подключить канал"],
                  ["🏠 Меню"]])

        elif text == "🔗 Подключить канал":
            s["mode"] = "channel"
            send(user, "Отправьте @username канала.")

        elif s["mode"] == "channel":
            if not text.startswith("@"):
                send(user, "Нужен @username канала.")
            else:
                result = requests.post(
                    f"{API}/getChatMember",
                    json={"chat_id": text,
                          "user_id": int(
                              requests.get(
                                  f"{API}/getMe",
                                  timeout=15
                              ).json()["result"]["id"]
                          )},
                    timeout=15
                ).json()
                member = result.get("result", {})
                if (member.get("status") == "administrator"
                    and member.get("can_post_messages")):
                    s["channel"] = text
                    s["mode"] = None
                    send(user, "✅ Канал подключён!", MENU)
                else:
                    send(user,
                         "❌ Дайте боту права "
                         "администратора для публикации.")

        elif text in ("📝 Создать пост",
                      "📢 Рекламный пост"):
            s["mode"] = "draft"
            send(user, "✍️ Отправьте текст поста.")

        elif s["mode"] == "draft":
            s["draft"] = text
            s["mode"] = None
            send(user,
                 "✅ Черновик сохранён:\n\n" + text,
                 [["🚀 Опубликовать"],
                  ["✏️ Изменить пост"],
                  ["🏠 Меню"]])

        elif text == "✏️ Изменить пост":
            s["mode"] = "draft"
            send(user, "Отправьте новый текст поста.")

        elif text == "🚀 Опубликовать":
            if not s["channel"] or not s["draft"]:
                send(user, "Сначала подключите канал "
                     "и создайте пост.")
            else:
                result = requests.post(
                    f"{API}/sendMessage",
                    json={"chat_id": s["channel"],
                          "text": s["draft"]},
                    timeout=15
                ).json()
                if result.get("ok"):
                    send(user, "✅ Пост опубликован!", MENU)
                else:
                    send(user,
                         "❌ Ошибка публикации. "
                         "Проверьте права бота.")

        elif text == "📂 Мои проекты":
            send(user,
                 "📂 Канал: " +
                 (s["channel"] or "не подключён"),
                 MENU)

        elif text == "📅 Контент-план":
            send(user,
                 "📅 Публикации по расписанию "
                 "добавим на следующем этапе.",
                 MENU)

        else:
            send(user, "Выберите действие 👇", MENU)

    except Exception as e:
        app.logger.exception("Bot error")
        return "Error", 500

    return "OK", 200
