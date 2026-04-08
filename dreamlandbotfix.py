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
# --- 2. FUNGSI BOT ---iman

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    teks = (
        f"Halo {user_name}! 👋\n"
        f"Selamat datang di **dreamlandfish.myd**.\n"
        f"Silakan lihat katalog kami di bawah ini:"
    )
    keyboard = [[InlineKeyboardButton("🖼️ KLIK Lihat Katalog & Pesan", callback_data='lihat_katalog')]]
    
    if update.message:
        await update.message.reply_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text("📋 **MENGIRIM KATALOG DREAMLANDFISH**", parse_mode='Markdown')
    
    for k, v in KATALOG.items():
        teks_ikan = f"🔹 **{v['nama']}**\n   └ Harga: Rp{v['harga']:,}"
        keyboard = [[InlineKeyboardButton(f"🛒 Pesan {v['nama']}", callback_data=f"beli_{k}")]]
        
        try:
            with open(v['foto'], 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file,
                    caption=teks_ikan,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        except FileNotFoundError:
            await query.message.reply_text(f"{teks_ikan}\n*(Gambar tidak ditemukan)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    keyboard_back = [[InlineKeyboardButton("⬅️ Kembali", callback_data='start_back')]]
    await query.message.reply_text("---", reply_markup=InlineKeyboardMarkup(keyboard_back))
    return CHOOSING_FISH

async def minta_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("beli_", "")
    context.user_data['ikan_dipilih'] = KATALOG[key]
    await query.message.reply_text(f"🔢 Mau pesan berapa ekor **{KATALOG[key]['nama']}**?\n(Ketik angka saja, misal: 2)", parse_mode='Markdown')
    return ASKING_QUANTITY

async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Harap masukkan angka yang valid.")
        return ASKING_QUANTITY
    
    qty = int(update.message.text)
    context.user_data['qty'] = qty
    ikan = context.user_data['ikan_dipilih']
    context.user_data['total_harga'] = ikan['harga'] * qty
    
    await update.message.reply_text(f"✅ {qty} ekor dicatat.\n\n📍 **Alamat Pengiriman:**\nSilakan ketik alamat lengkap Anda:", parse_mode='Markdown')
    return ASKING_ADDRESS

async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['alamat_user'] = update.message.text
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
