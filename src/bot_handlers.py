
import json
import hashlib
from bot import Bot
from telebot import types

# import re

posts_file = "posts.json"
idea_file = "ideas.txt"
qa_file = "qa.json"
channel_id = "@vut_fit"
tmp = None
bot = Bot()

msgs = {
    "start": "I'm helper bot for channel t.me/vut_fit. "
    "Here is my command that can help you:",
    "help": "/help - print help message\n"
    "/start - print hello message with help message\n"
    "/all posts | streams - to show all usefull posts in channel or all streams \n"
    "/help_me question - if you have any question, please use this "
    "command. It is needed to create bank of questions for every one. Thank:)\n"
    "/idea any idea - if you have any idea of new fiture or "
    "improvement use this command",
}


@bot.message_handler(commands=["start"])
def start(msg):
    """
    Send a message when the command /help or /start are sent or on the
    new member joining.
    """
    user = msg.from_user
    if user.username == "plov_ec" and msg.chat.type == "private":
        bot.my_chat_id = msg.chat.id

    # Create full name with username for chats
    name = user.first_name
    if hasattr(user, "last_name") and user.last_name is not None:
        name = name + f" {user.last_name}"

    if hasattr(user, "username") and user.username is not None:
        name = name + f" (@{user.username})"

    text = f"Hello, {name}!\n{msgs['start']}\n{msgs['help']}"
    bot.reply_to(msg, text)


@bot.message_handler(
    func=lambda m: m.content_type == "new_chat_members",
    content_types=["new_chat_members"],
)
def on_user_joins(msg):
    for _ in msg.new_chat_members:
        start(msg)


@bot.message_handler(commands=["help"])
def help_msg(msg):
    bot.send_message(msg.chat.id, msgs["help"])


@bot.message_handler(commands=["all"])
def all_usefull(msg):
    try:
        # Here would be raised IndexError, if there is any type
        tipe = msg.text.split(" ")[1]
        # And here would be raised KeyError, if type is incorrect
        data = bot.get_data(posts_file)[tipe]
        text = "\n".join(
            [f"{link} - {description}" for link, description in data]
        )
        bot.send_message(msg.chat.id, f"All {tipe}:\n{text}")
    except (IndexError, KeyError):
        bot.send_message(msg.chat.id, "Invalid type")


@bot.message_handler(commands=["add"])
def add_usefull(msg):
    if msg.chat.username == "plov_ec":
        data = bot.get_data(posts_file)
        tipe, link, description = [
            s.strip() for s in msg.text.split("/add ")[1].split("|")
        ]
        if tipe == "posts" or tipe == "streams":
            data[tipe].append([link, description])
            bot.update_data(posts_file, data)
        else:
            bot.send_message(
                msg.chat.id, "Incorrect type to add",
            )
    else:
        bot.send_message(
            msg.chat.id, f"Sorry, {msg.chat.username}, you can't add any info",
        )


@bot.message_handler(commands=["idea"])
def idea(message):
    # If user have any idea how to improve or what he want to add to bot
    data = bot.get_data(idea_file)
    idea = message.text.split("/idea ")[1]
    data["ideas"].append({"from": message.chat.username, "idea": idea})
    bot.send_message(
        bot.my_chat_id,
        f"There is new idea!\nFrom: {message.chat.username}\nIdea: {idea}",
    )
    bot.update_data(idea_file, data)


@bot.message_handler(commands=["help_me"])
def help_me(message):
    q = message.text.split("/help_me ")
    if len(q) < 2:
        bot.send_message(
            message.chat.id, "Repeat command with question, please"
        )
    else:
        q = q[1]
        if len(q) < 10:
            bot.send_message(
                message.chat.id,
                "I think, it isn't an question... Please, try again",
            )
        else:
            q_id = hashlib.sha1(bytes(q, "utf-8")).hexdigest()[:10]
            # TODO search algorithm and run search of phrases
            data = bot.get_data(qa_file)

            # Search question ID in list of all IDs
            if q_id not in [i["id"] for i in data["qa"]]:
                # If not present, then and new question entry and send my message
                # with question
                data["qa"].append({"id": q_id, "q": q, "a": "", "tag": []})
                bot.update_data(qa_file, data)

                markup = types.InlineKeyboardMarkup(row_width=2)
                cb_data_send = f"send#{message.chat.id}|{q_id}"
                if message.chat.type != "private":
                    # If message is not from private chat, then username would be
                    # saved to ping user in future
                    cb_data_send += f"|{message.from_user.username}"

                markup.add(
                    types.InlineKeyboardButton(
                        "Answer", callback_data=f"answer#{q_id}"
                    ),
                    types.InlineKeyboardButton(
                        "Send", callback_data=cb_data_send
                    ),
                )
                bot.send_message(
                    bot.my_chat_id,
                    f"Question from {message.from_user.username}: {q}",
                    reply_markup=markup,
                )
                bot.reply_to(
                    message,
                    "Thanks for your question. I will answer you as soon as possible",
                )

            else:
                # If ID exists, then send corresponding answer
                answer = [i["a"] for i in data["qa"] if i["id"] == q_id][0]
                bot.send_message(message.chat.id, answer)


@bot.callback_query_handler(func=lambda call: True)
def process_step(call):
    # Args is used for returning answer from process_answer function
    try:
        step, data = call.data.split("#")
        if step == "answer":
            msg = bot.send_message(bot.my_chat_id, "Type answer")
            bot.register_next_step_handler(
                msg, lambda m: process_answer(m, data)
            )
        elif step == "send":
            # Split data to extract chat_id and username
            data = data.split("|")
            chat_id, q_id = data[0], data[1]

            with open(qa_file, "r") as f:
                data_f = json.load(f)
                answer = [
                    entry["a"] for entry in data_f["qa"] if entry["id"] == q_id
                ][0]

            if len(data) == 2:
                bot.send_message(
                    int(chat_id),
                    f"Hi! Here is answer on your question: {answer}",
                )
            else:
                bot.send_message(
                    int(chat_id),
                    f"Hi, @{data[2]}! Here is answer on your question: {answer}",
                )
    except ValueError:
        pass


@bot.message_handler(commands=["create_post"])
def create_post(msg):
    bot.send_message(channel_id, "Test of sending message")


def process_answer(msg, q_id):

    data = bot.get_data(qa_file)
    entry = [entry for entry in data["qa"] if entry["id"] == q_id][0]
    index = data["qa"].index(entry)
    entry["a"] = msg.text
    data["qa"][index] = entry
    bot.update_data(qa_file, data)


if __name__ == "__main__":
    bot.start_env()
