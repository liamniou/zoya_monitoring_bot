# !/usr/bin/python3
# -*- coding: utf-8 -*-
import configparser
import datetime
import logging as log
import os.path
import pickle
import telebot
from telebot import types
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


class Config():
    config = configparser.ConfigParser()
    config_file_path = None

    def __init__(self):
        self.config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        self.load_config()

    def load_config(self):
        '''Load configuration parameters'''
        if os.path.exists(self.config_file_path):
            self.config.read(self.config_file_path)
        else:
            self.set_default_config()

    def set_default_config(self):
        '''Set default configuration'''
        self.config['telegram'] = {}
        self.config['telegram']['token'] = 'TELEGRAM_BOT_TOKEN'
        self.config['sheets'] = {}
        self.config['sheets']['scope'] = ' https://www.googleapis.com/auth/spreadsheets'
        self.config['sheets']['spreadsheet_id'] = 'SPREADSHEET_ID'
        self.config['sheets']['sheet_id'] = 'SHEET_ID'

        with open(self.config_file_path, 'w') as config_file:
            self.config.write(config_file)

    def get(self):
        '''Obtain configuration'''
        return self.config


config = Config().get()
SCOPES = [config['sheets']['scope']]
SPREADSHEET_ID = config['sheets']['spreadsheet_id']
SHEET_ID = config['sheets']['sheet_id']
BUTTONS = ['🏠 пописала дома', '🏠 покакала дома', '🌳 пописала на улице', '🌳 покакала на улице']
bot = telebot.TeleBot(config['telegram']['token'], threaded=False)


@bot.message_handler(commands=['start', 'help'])
def greet_new_user(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(types.KeyboardButton(BUTTONS[0]),
               types.KeyboardButton(BUTTONS[1]),
               types.KeyboardButton(BUTTONS[2]),
               types.KeyboardButton(BUTTONS[3]))
    bot.send_message(message.chat.id, "Привет! Добро пожаловать в мониторинг активностей самоеда Зои!",
                     reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in BUTTONS)
def command_buttons(message):
    insert_raw(build_service(), [str(datetime.datetime.now()), message.text])
    bot.send_message(message.chat.id, "Принято!")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(message):
    bot.send_message(message.chat.id, "Я тебя не понял :( воспользуйся кнопками")


def listener(messages):
    for m in messages:
        log.info(m)


def build_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Credentials are expired")
            creds.refresh(Request())
        else:
            log.info("Credentials don't exist")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)


def get_data(service, range_name):
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                range=range_name).execute()
    return result.get('values', [])


def insert_raw(service, values):
    requests = [{
        "insertRange": {
            "range": {
                "sheetId": SHEET_ID,
                "startRowIndex": 1,
                "endRowIndex": 2
            },
            "shiftDimension": "ROWS"
        }
    },
    {
        "pasteData": {
            "data": ", ".join(values),
            "type": "PASTE_NORMAL",
            "delimiter": ",",
            "coordinate": {
                "sheetId": SHEET_ID,
                "rowIndex": 1
            }
        }
    }]

    body = {
        'requests': requests
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=body).execute()
    return 0


if __name__ == '__main__':
    bot.set_update_listener(listener)
    bot.polling()
