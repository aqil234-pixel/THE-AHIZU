import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# --- 1. KONFIGURASI ---
TOKEN = '8360782987:AAHq0sCk99_H_vq73HtTsPP91eVeRX7YoNA'
ADMIN_ID = 123456789 # GANTI DENGAN ID KAMU
SHEET_NAME = 'Pesanan Ikan Hias'
JSON_FILE = 'credentials.json'

# State untuk percakapan
CHOOSING_FISH, ASKING_ADDRESS, CHOOSING_PAYMENT = range(3)

KATALOG = {
    "betta": {"nama": "Ikan Cupang Nemo", "harga": 50000},
    "guppy": {"nama": "Guppy Albino", "harga": 35000},
    "arowana": {"nama": "Arwana Silver", "harga": 150000}
}

# --- 2. FUNGSI GOOGLE SHEETS ---
def catat_ke_sheet(nama, username, produk, harga, alamat, metode):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Tambahkan kolom Alamat dan Metode di baris baru
        sheet.append_row([waktu, nama, f"@{username}", produk, harga, alamat, metode])
        return True
    except:
        return False

# --- 3. FUNGSI BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    teks = (
        f"Halo {user_name}! 👋\n"
        f"Selamat datang di **dreamlandfish.myd**.\n"
        f"Ada yang bisa kami bantu hari ini?"
    )
    keyboard = [
        [InlineKeyboardButton("🖼️ Lihat Katalog Ikan", callback_data='lihat_katalog')],
        [InlineKeyboardButton("🛒 Pesan Sekarang", callback_data='pesan_ikan')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(teks, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(teks, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END # Reset konv jika balik ke start

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    teks_katalog = "📋 **KATALOG DREAMLAND FISH**\n\n"
    for k, v in KATALOG.items():
        teks_katalog += f"🔹 **{v['nama']}**\n   └ Harga: Rp{v['harga']:,}\n\n"
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='start_back')]]
    await query.message.reply_text(teks_katalog, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# STEP 1: Pilih Ikan
async def proses_pesan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton(f"🛍️ Beli {v['nama']}", callback_data=f"beli_{k}")] for k, v in KATALOG.items()]
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data='start_back')])
    await query.edit_message_text("Pilih ikan yang ingin dipesan:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_FISH

# STEP 2: Minta Alamat
async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Simpan pilihan ikan ke context user data
    key = query.data.replace("beli_", "")
    context.user_data['ikan_dipilih'] = KATALOG[key]
    
    await query.edit_message_text("📍 **Alamat Pengiriman**\nSilakan ketik alamat lengkap pengiriman Anda (Nama Jalan, No Rumah, Kota, dsb):", parse_mode='Markdown')
    return ASKING_ADDRESS

# STEP 3: Minta Metode Pembayaran
async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simpan alamat dari pesan teks user
    context.user_data['alamat_user'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("🏦 Transfer Rekening", callback_data='pay_rekening')],
        [InlineKeyboardButton("📱 Saldo DANA", callback_data='pay_dana')]
    ]
    await update.message.reply_text("💳 **Metode Pembayaran**\nSilakan pilih metode pembayaran:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CHOOSING_PAYMENT

# STEP 4: Finalisasi (Simpan & Notif)
async def konfirmasi_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ambil semua data yang disimpan
    ikan = context.user_data['ikan_dipilih']
    alamat = context.user_data['alamat_user']
    metode = "Rekening" if query.data == 'pay_rekening' else "DANA"
    user = query.from_user

    # Catat ke Sheets
    catat_ke_sheet(user.full_name, user.username, ikan['nama'], ikan['harga'], alamat, metode)

    # Notif ke Admin
    pesan_admin = (
        f"🔔 **ORDERAN BARU**\n\n"
        f"👤 **Pembeli:** {user.full_name}\n"
        f"🆔 **Username:** @{user.username}\n"
        f"🐠 **Pesanan:** {ikan['nama']}\n"
        f"📍 **Alamat:** {alamat}\n"
        f"💳 **Metode:** {metode}\n"
        f"💰 **Total:** Rp{ikan['harga']:,}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=pesan_admin, parse_mode='Markdown')

    # Balas ke User
    await query.edit_message_text(
        f"Selesai! Pesanan **{ikan['nama']}** sedang kami proses. ✨\n\n"
        f"Admin akan segera menghubungi Anda untuk nomor {metode} tujuan.\n"
        f"Terima kasih sudah memesan di **dreamlandfish.myd**!", 
        parse_mode='Markdown'
    )
    context.user_data.clear() # Bersihkan data sementara
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(proses_pesan, pattern='^pesan_ikan$')],
        states={
            CHOOSING_FISH: [CallbackQueryHandler(minta_alamat, pattern='^beli_')],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_pembayaran)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(konfirmasi_akhir, pattern='^pay_')]
        },
        fallbacks=[CallbackQueryHandler(start, pattern='^start_back$'), CommandHandler('start', start)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_katalog, pattern='^lihat_katalog$'))
    app.add_handler(CallbackQueryHandler(start, pattern='^start_back$'))
    app.add_handler(conv_handler)

    print("Bot Dreamland Fish v2 (Address & Payment) Aktif! 🚀")
    app.run_polling()

if __name__ == '__main__':
    main()