import telebot
import os
from flask import Flask, request
import logging
import json

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, f"Priuvet {message.chat.username}")

@bot.message_handler("help")
def help(message):
    """Send a message when the command /help is issued."""
    text = f"""
    Hello, {message.chat.username}!
    I'm helper bot for channel t.me/vut_fit.
    Here is my command that can help you:
    /all_posts - to show all usefull posts in channel
    
    Pleas, remember, I'm still under development
    Thanks!
    """
    bot.send_message(message.chat.id, text)

@bot.message_handler("all_posts")
def all_posts(message):
    text = ""
    with open("./posts.json", "r") as f:
        data = json.load(f)
        for post in data["posts"]:
            text = text + f"{post[0]} - {post[1]}\n"
    bot.send_message(message.chat.id, "Posts are:\n" + text)
            
@bot.message_handler("add_post")
def add_post(message):
    if message.chat.username == "plov_ec":
        data = []
        with open("./posts.json", "r") as f:
            data = json.load(f)
        data["posts"].append(["link", "description"])
        with open("./posts.json", "w") as f:
            json.dump(data, f)
    else:
        bot.send_message(message.chat.id, f"Sorry, {message.chat.username}, you can't add posts")

if "HEROKU" in list(os.environ.keys()):
    logger = telebot.logger
    telebot.logger.setLevel(logging.INFO)

    server = Flask(__name__)
    @server.route("/bot", methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200
    
    @server.route("/")
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url=f'https://morning-beach-95188.herokuapp.com/bot') # этот url нужно заменить на url вашего Хероку приложения
        return "?", 200
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    # если переменной окружения HEROKU нету, значит это запуск с машины разработчика.  
    # Удаляем вебхук на всякий случай, и запускаем с обычным поллингом.
    bot.remove_webhook()
    bot.polling(none_stop=True)

# import logging
# from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
# import os
# import json
# PORT = int(os.environ.get('PORT', 5000))

# # Enable logging
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                     level=logging.INFO)

# logger = logging.getLogger(__name__)
# TOKEN = os.environ["TELEGRAM_TOKEN"]
# # Define a few command handlers. These usually take the two arguments update and
# # context. Error handlers also receive the raised TelegramError object in error.

# def check_bot(func):
#     def wrapper(update, context):
#         if update.message.from_user.is_bot:
#             pass
#     return wrapper

# def start(update, context):
#     """Send a message when the command /start is issued."""
#     update.message.reply_text('Hi!')
#     print(context)
    

# def echo(update, context):
#     """Echo the user message."""
#     update.message.reply_text(update.message.text)

# def error(update, context):
#     """Log Errors caused by Updates."""
#     logger.warning('Update "%s" caused error "%s"', update, context.error)


# def main():
#     """Start the bot."""
#     # add_post()
#     # Create the Updater and pass it your bot's token.
#     # Make sure to set use_context=True to use the new context based callbacks
#     # Post version 12 this will no longer be necessary
#     updater = Updater(TOKEN, use_context=True)

#     # Get the dispatcher to register handlers
#     dp = updater.dispatcher

#     # on different commands - answer in Telegram
#     dp.add_handler(CommandHandler("start", start))
#     dp.add_handler(CommandHandler("help", help))
#     dp.add_handler(CommandHandler("all_posts", all_posts))
#     dp.add_handler(CommandHandler("add_post", add_post))
#     # on noncommand i.e message - echo the message on Telegram
#     dp.add_handler(MessageHandler(Filters.text, echo))

#     # log all errors
#     dp.add_error_handler(error)

#     # Start the Bot
#     updater.start_webhook(listen="0.0.0.0",
#                           port=int(PORT),
#                           url_path=TOKEN)
#     updater.bot.setWebhook('https://morning-beach-95188.herokuapp.com/' + TOKEN)

#     # Run the bot until you press Ctrl-C or the process receives SIGINT,
#     # SIGTERM or SIGABRT. This should be used most of the time, since
#     # start_polling() is non-blocking and will stop the bot gracefully.
#     updater.idle()

# if __name__ == '__main__':
#     main()