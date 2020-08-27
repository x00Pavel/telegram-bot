import json
import hashlib
from bot import Bot
from telebot import types
import re

# import calendar

posts_file = "posts.json"
idea_file = "ideas.txt"
qa_file = "qa.json"
bot = Bot()

tmp = None

msg = {
    "start": "I'm helper bot for channel t.me/vut_fit."
    "Here is my command that can help you:",
    "help": "/all_posts - to show all usefull posts in channel\n"
    "/help_me <question> - if you have any question, please use this "
    "command. It is needed to create bank of questions for every one. Thank:)\n"
    "/idea <any text> - if you have any idea of new fiture or "
    "improvement use this command",
}


@bot.message_handler(commands=["start"])
def start(message):
    """Send a message when the command /help or /start are sent."""
    if (
        message.from_user.username == "plov_ec"
        and message.chat.type == "private"
    ):
        bot.my_chat_id = message.chat.id
    text = f"Hello, {message.chat.username}!\n{msg['start']}\n{msg['help']}"
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["help"])
def help(message):
    bot.send_message(message.chat.id, msg["help"])


@bot.message_handler(commands=["all_posts"])
def all_posts(message):
    data = bot.get_data(posts_file)
    text = ""
    for post in data["posts"]:
        text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "All posts:\n" + text)


@bot.message_handler(command=["add_tag"])
def add_tag(msg):
    if msg.chat.username == "plov_ec":
        data = bot.get_data(qa_file)
        tags = msg.text.split("/add_post ")[0]
        for tag in re.findall(r"([а-я]+)", tags):
            data["tags"].append(tag)
        bot.update_data(qa_file, data)
    else:
        bot.send_message(
            msg.chat.id, f"Sorry, {msg.chat.username}, you can't add tags"
        )


@bot.message_handler(commands=["add_post"])
def add_post(message):
    if message.chat.username == "plov_ec":
        data = bot.get_data(posts_file)
        words = message.text.split("/add_post ").split("|")
        data["posts"].append([words[0], words[1]])
        bot.update_data([posts_file, data])
    else:
        bot.send_message(
            message.chat.id,
            f"Sorry, {message.chat.username}, you can't add posts",
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
        bot.send_message(
            message.chat.id, "Repeat command with question, please"
        )
    else:
        q = q[1]
        q_id = hashlib.sha1(bytes(q, "utf-8")).hexdigest()[:10]
        # TODO search algorithm and run search of patterns in another thread
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
                types.InlineKeyboardButton("Send", callback_data=cb_data_send),
                types.InlineKeyboardButton(
                    "Show avaliable tags", callback_data=f"tags#{q_id}"
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

        elif step == "tags":
            tags = bot.get_data(qa_file)["tags"]
            msg = bot.send_message(
                bot.my_chat_id, f"Avaliable tags:\n{', '.join(tags)}"
            )
    except ValueError:
        pass


def process_answer(msg, q_id, **kwargs):

    match_tags = (
        re.findall(r"tags: (.*)\n", msg.text)
        if "tags" not in kwargs.keys()
        else kwargs["tags"]
    )
    match_text = (
        re.findall(r"text: (.+)", msg.text)
        if "text" not in kwargs.keys()
        else kwargs["text"]
    )
    chat_id = msg.chat.id
    if match_tags and match_text:
        data = bot.get_data(qa_file)
        entry = [entry for entry in data["qa"] if entry["id"] == q_id][0]
        index = data["qa"].index(entry)
        entry["a"] = match_text[0]  # because findall() return list

        tags = match_tags[0].split()
        for tag in tags:
            if tag in data["tags"]:
                entry["tag"].append(tag)
            else:
                bot.send_message(chat_id)

        data["qa"][index] = entry
        bot.update_data(qa_file, data)
    else:
        args = {}
        m = None
        if not match_tags:
            m = bot.send_message(
                msg.chat.id,
                "Please, provide tags in following format:\n"
                "tags: tag1, tag2, etc",
            )
        else:
            args["tags"] = match_tags

        if not match_text:
            m = bot.send_message(
                msg.chat.id,
                "Please, provide answer in following format:\n"
                "text: here is text of answer",
            )
        else:
            args["text"] = match_text
        bot.register_next_step_handler(
            m, lambda m: process_answer(m, data, args)
        )


if __name__ == "__main__":
    bot.start_env()
