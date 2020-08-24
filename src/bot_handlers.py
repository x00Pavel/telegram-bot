import json
import hashlib
from bot import Bot
from telebot import types

posts_file = "posts.json"
idea_file = "ideas.txt"
qa_file = "qa.json"
bot = Bot()


@bot.message_handler(commands=["start", "help"])
def help(message):
    """Send a message when the command /help or /start are sent."""
    if message.from_user.username == "plov_ec" and message.chat.type == "private":
        bot.my_chat_id = message.chat.id
    text = f"""
Hello, {message.chat.username}!
I'm helper bot for channel t.me/vut_fit.
Here is my command that can help you:
/all_posts - to show all usefull posts in channel

Pleas, remember, I'm still under development
Thanks!
    """
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["all_posts"])
def all_posts(message):
    data = bot.get_data(posts_file)
    text = ""
    for post in data["posts"]:
        text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "All posts:\n" + text)


@bot.message_handler(commands=["add_post"])
def add_post(message):
    if message.chat.username == "plov_ec":
        data = bot.get_data(posts_file)
        words = message.text.split("/add_post ").split("|")
        data["posts"].append([words[0], words[1]])
        bot.update_data([posts_file, data])
    else:
        bot.send_message(
            message.chat.id, f"Sorry, {message.chat.username}, you can't add posts"
        )


@bot.message_handler(commands=["idea"])
def idea(message):
    # If user have any idea how to improve or what he want to add to bot
    data = bot.get_data(idea_file)
    idea = message.text.split("/idea ")[1]
    data["ideas"].append({"from": message.chat.username, "idea": idea})
    bot.update_data(idea_file, data)


@bot.message_handler(commands=["help_me"])
def help_me(message):
    q = message.text.split("/help_me ")
    if len(q) < 2:
        bot.send_message(message.chat.id, "Repeat command with question, please")
    else:
        q = q[1]
        hash_object = hashlib.sha1(bytes(q, "utf-8"))
        # TODO search algorithm and run search of patterns in another thread
        q_id = hash_object.hexdigest()
        data = bot.get_data(qa_file)

        # Search question ID in list of all IDs
        if q_id not in [i["id"] for i in data["qa"]]:
            # If not present, then and new question entry and send my message
            # with question
            data["qa"].append({"id": q_id, "q": q, "a": ""})
            bot.update_data(qa_file, data)

            markup = types.InlineKeyboardMarkup(row_width=2)
            cb_data_send = f"send#{message.chat.id}|{q_id}"
            if message.chat.type != "private":
                # If message is not from private chat, then username would be saved
                # to ping user in future
                cb_data_send += f"|{message.from_user.username}"

            markup.add(
                types.InlineKeyboardButton("Answer", callback_data=f"answer#{q_id}"),
                types.InlineKeyboardButton("Send", callback_data=cb_data_send),
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
def process_step(call, *args):
    # Args is used for returning answer from process_answer function
    try:
        step, data = call.data.split("#")
        if step == "answer":
            msg = bot.send_message(bot.my_chat_id, "Type answer")
            bot.register_next_step_handler(msg, lambda m: process_answer(m, data))
        elif step == "send":
            # Split data to extract chat_id and username
            data = data.split("|")
            chat_id, q_id = data[0], data[1]

            with open(qa_file, "r") as f:
                data_f = json.load(f)
                answer = [entry["a"] for entry in data_f["qa"] if entry["id"] == q_id][
                    0
                ]

            if len(data) == 2:
                bot.send_message(
                    int(chat_id), f"Hi! Here is answer on your question: {answer}"
                )
            else:
                bot.send_message(
                    int(chat_id),
                    f"Hi, @{data[2]}! Here is answer on your question: {answer}",
                )
    except ValueError:
        pass


def process_answer(message, q_id):
    data = bot.get_data(qa_file)
    entry = [entry for entry in data["qa"] if entry["id"] == q_id][0]
    index = data["qa"].index(entry)
    entry["a"] = message.text
    data["qa"][index] = entry
    bot.update_data(qa_file, data)


if __name__ == "__main__":
    bot.start_env()
