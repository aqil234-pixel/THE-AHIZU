import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# --- 1. KONFIGURASI --- aqil
TOKEN = '8360782987:AAHq0sCk99_H_vq73HtTsPP91eVeRX7YoNA'
ADMIN_ID = 8313481314
SHEET_NAME = 'Pesanan Ikan Hias'
JSON_FILE = 'credentials.json'

# INFO REKENING
NOREK_BANK = "Bank BCA - 123456789 (A/N Dreamland)"
NOREK_DANA = "DANA - 08123456789 (A/N Dreamland)"

# State untuk percakapan
CHOOSING_FISH, ASKING_QUANTITY, ASKING_ADDRESS, CHOOSING_PAYMENT = range(4)

# KATALOG DENGAN FILE LOKAL
KATALOG = {
    "betta": {
        "nama": "Ikan Cupang Nemo", 
        "harga": 50000, 
        "foto": "foto katalog/cupang.JPG"
    },
    "guppy": {
        "nama": "Guppy Albino", 
        "harga": 35000, 
        "foto": "foto katalog/guppy.JPG"
    },
    "arowana": {
        "nama": "Arwana Silver", 
        "harga": 150000, 
        "foto": "foto katalog/arowana.JPG"
    },
}
