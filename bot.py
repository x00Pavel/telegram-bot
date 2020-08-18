import telebot
from telebot import types
import os
from flask import Flask, request
import logging
import json
import boto3

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)

my_chat_id = 320130425
s3 = boto3.client('s3')
BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
file_name = "posts.json"

def check_bot(message):
    if message.from_user.is_bot:
        bot.kick_chat_member(message.chat.id, message.from_user.user_id)
        return False
    return True


@bot.message_handler(commands=["start", "help"])
def help(message):
    """Send a message when the command /help or /start 
    are sent."""
    if message.from_user.username == "plov_ec" and \
        message.chat.type == "private":
        global my_chat_id
        my_chat_id = message.chat.id
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
    text = ""
    if not os.path.exists(file_name):
        with open(file_name, "wb") as f:
            s3.download_fileobj(BUCKET_NAME, file_name, f)
        
    with open(file_name, "r") as f:
        data = json.load(f)
        for post in data["posts"]:
            text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "All posts:\n" + text)

        
@bot.message_handler(commands=["add_post"])
def add_post(message):
    if message.chat.username == "plov_ec":
        # Download file if it does not exist - only in first use after restart
        if not os.path.exists(file_name):
            with open(file_name, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, file_name, f)

        # Parse message -> insert to file -> upload to S3
        with open(file_name, "w+") as f:
            data = json.load(f)
            words = message.text.split("/add_post ").split("|")
            data["posts"].append([words[0], words[1]])
            json.dump(data, f)

        with open(file_name, "rb") as f:
            s3.upload_fileobj(f, BUCKET_NAME, file_name)

    else:
        bot.send_message(message.chat.id, 
        f"Sorry, {message.chat.username}, you can't add posts")


@bot.message_handler(commands=["idea"])
def idea(message):
    file_name = "ideas.txt"
    if not os.path.exists(file_name):
        with open(file_name, "wb") as f:
            s3.download_fileobj(BUCKET_NAME, file_name, f)

    # Parse message -> insert to file -> upload to S3
    with open(file_name, "a+") as f:
        words = message.text.split("/idea ")[1]
        f.write(f"From {message.chat.username}: {words}\n\n")

    with open(file_name, "rb") as f:
        s3.upload_fileobj(f, BUCKET_NAME, file_name)


@bot.message_handler(commands=["help_me"])
def help_me(message):
    file_name = "qa.json"
    if not os.path.exists(file_name):
            with open(file_name, "wb") as f:
                s3.download_fileobj(BUCKET_NAME, file_name, f)

    # I don't know why, but here 'with' statement doesn't work
    f = open(file_name, "r")
    data = json.load(f)
    f.close()
    q = message.text.split("/help_me ")

    if len(q) < 2:
        bot.send_message(message.chat.id, "Repeat command with question, please")
    else:
        q = q[1]
        q_id = abs(hash(q)) % (10 ** 8)
        # TODO search algorithm and run search of patterns in another thread
        # Search question ID in list of all IDs
        if q_id not in [int(i["id"]) for i in data]:
            # If not present, then and new question entry and send my message with question
            data["qa"].append({"id": q_id, "question": q, "answer": ""})
            sorted(data["qa"], key=lambda i: i["id"])

            f = open(file_name, "w")
            json.dump(data, f)
            f.close()
            # with open(file_name, "rb") as f:
            #     s3.upload_fileobj(f, BUCKET_NAME, file_name)

            markup = types.InlineKeyboardMarkup(row_width=2)

            cb_data_send = f"send#{message.chat.id}" 
            if message.chat.type != "private":
                cb_data_send += f"|{message.from_user.username}"

            markup.add(
                types.InlineKeyboardButton("Answer", callback_data=f"answer#{q_id}"),
                types.InlineKeyboardButton("Send", 
                callback_data=cb_data_send),
            )
            bot.send_message(my_chat_id, 
                            f"Chat ID: {message.chat.id}\nQuestion from {message.from_user.username}: {q}",
                            reply_markup=markup)
            bot.reply_to(message, "Thanks for your question. I will answer you as soon as possible")

        else:
            # If ID exists, then send corresponding answer
            answer = [i["answer"] for i in data["qa"] if int(i["id"]) == q_id][0]
            bot.send_message(message.chat.id, answer)


@bot.callback_query_handler(func=lambda call: True)
def process_step(call, *args):
    # Args is used for returning answer from process_answer function
    try:
        step, data = call.data.split("#")
        if step == "answer":
            msg = bot.send_message(my_chat_id, "Type answer")
            bot.register_next_step_handler(msg, process_answer, int(call.data))
        elif step == "send":
            # Split data to extract chat_id and username
            data = data.split("|")
            if len(data) == 1:
                bot.send_message(int(data[0]), f"Hi! Here is answer on your question: {args[0]}")
            else:
                bot.send_message(int(data[0]), f"Hi, @{data[1]}! Here is answer on your question: {args[0]}")
    except ValueError:
        pass


def process_answer(message, q_id):
    with open("qa.json", "w+") as f:
        data = json.load(f)
        entry = [int(entry["id"]) for entry in data["qa"] if int(entry["id"]) == q_id][0]
        index = data["qa"].index(entry)
        entry["answer"] = message.text
        data["qa"][index] = entry
        json.dump(data, f)
    bot.register_next_step_handler(message, process_step, message.text)

@bot.message_handler(commands=["answer"])
def answer(message):
    if message.from_user.username == "plov_ec":
        pass

if "HEROKU" in os.environ.keys():
    logger = telebot.logger
    telebot.logger.setLevel(logging.DEBUG)

    server = Flask(__name__)
    @server.route('/' + TOKEN, methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200

    bot.remove_webhook()
    bot.set_webhook(url=f'https://morning-beach-95188.herokuapp.com/{TOKEN}')
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    bot.remove_webhook()
    bot.polling()