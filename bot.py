import logging
import os
import random

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from markov_chain import MarkovChain, MarkovState
from text_propabilities import get_words_propabilities


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def send_typing_action(func):
    def wrapper(self, update, context):
        context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
        func(self, update, context)

    return wrapper

class Bot:
    def __init__(self):
        self.token = os.getenv("telegram_token")
        if self.token is None:
            logger.error('Set "telegram_token" environment variable.')
            logger.error("export telegram_token=example_token")
            exit(os.EX_CONFIG)
        
        self.last_command = ''
        self.updater = Updater(self.token, use_context=True)
        self.set_commands_handlers()

        self.static_dir = os.path.join('.', 'static')
        if not os.path.isdir(self.static_dir):
            os.mkdir(self.static_dir)

    def local_run(self):
        self.updater.start_polling()
        self.updater.idle()

    def web_run(self):
        port = int(os.environ.get("PORT", 5000))
        self.updater.start_webhook(
            listen="0.0.0.0", port=port, url_path=self.token,
        )
        self.updater.bot.setWebhook(
            "https://markov-chain-bulgakov.herokuapp.com/{}".format(self.token)
        )
        self.updater.idle()

    def text_to_channel(self, chat_id, text):
        self.updater.bot.sendMessage(chat_id=chat_id, text=text)

    def set_commands_handlers(self):
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler("start", self.on_start))
        dp.add_handler(CommandHandler("help", self.on_help))
        dp.add_handler(CommandHandler("load", self.on_load))
        dp.add_handler(CommandHandler("list", self.on_list))
        dp.add_handler(CommandHandler("markov", self.on_markov))

        dp.add_handler(MessageHandler(Filters.text, self.on_unknown))

        dp.add_handler(MessageHandler(Filters.document, self.on_file))
        dp.add_error_handler(self.on_error)

    def on_start(self, update, context):
        self.on_help(update, context)
        self.last_command = ''

    def on_help(self, update, context):
        help_text = (
            "/load - load new file\n"
            "/list - list of available files\n"
            "/markov - generate text using markov chain\n"
            "/setSentenceCount - set sentence count\n"
        )
        update.message.reply_text(help_text)
        self.last_command = ''

    @send_typing_action
    def on_unknown(self, update, context):
        if self.last_command == 'markov':
            r = self.calc_markov(os.path.join(self.static_dir, update.message.text))
            update.message.reply_text(r)
        else:
            update.message.reply_text(f'on unknown command "{update.message.text}"')
        
        self.last_command = ''

    def on_error(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)
        self.last_command = ''

    def on_load(self, update, context):
        update.message.reply_text(f'Load your file.')
        self.last_command = ''

    def on_file(self, update, context):
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file = context.bot.getFile(file_id)
        file.download(os.path.join(self.static_dir, file_name))
        update.message.reply_text(f'File successfully downloaded.')
        self.last_command = ''

    def on_list(self, update, context):
        files = ', '.join(os.listdir(self.static_dir))
        update.message.reply_text(files)
        self.last_command = ''

    def on_markov(self, update, context):
        self.last_command = 'markov'

        menu_keyboard = [os.listdir(self.static_dir)]
        menu_markup = telegram.ReplyKeyboardMarkup(menu_keyboard, one_time_keyboard=True, resize_keyboard=True)
        self.updater.bot.sendMessage(chat_id=update.message.chat_id, text="Choose file:", reply_markup=menu_markup)
        
    def calc_markov(self, file):
        with open(file, encoding="utf-8") as f:
            propabilities = get_words_propabilities(f.read())

        m = MarkovChain(MarkovState(random.choice(list(propabilities.keys()))), history=200)
        for word, prop in propabilities.items():
            state_1 = MarkovState(word)
            for word_2, value in prop.items():
                state_2 = MarkovState(word_2)
                m.add_probability(state_1, state_2, value)
        result = "."
        for word in m:
            if result.count(".") > 5:
                break
            if result.endswith("."):
                word = word.capitalize()
            result += f" {word}"

        print(result)
        return result[1:]

if __name__ == "__main__":
    bot = Bot()
    bot.web_run()
