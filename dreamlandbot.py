import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler

# --- KONFIGURASI ---
TOKEN = '8360782987:AAHq0sCk99_H_vq73HtTsPP91eVeRX7YoNA'
ADMIN_ID = 7283608092
JSON_KEY = 'credentials.json' # File dari Google Cloud
SHEET_NAME = 'Pesanan Ikan Hias'

# --- FUNGSI GOOGLE SHEETS ---
def catat_ke_sheet(nama, username, produk, harga):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    
    # Menambahkan baris baru (Waktu, Nama, Username, Produk, Harga, Status)
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([waktu, nama, f"@{username}", produk, harga, "Belum Bayar"])

# --- DATA KATALOG ---
KATALOG = {
    "betta": {"nama": "Ikan Cupang Nemo", "harga": 50000, "foto": "https://images.unsplash.com/photo-1524594152303-9fd13543fe6e?q=80&w=400"},
    "guppy": {"nama": "Guppy Albino", "harga": 35000, "foto": "https://images.unsplash.com/photo-1620230003115-38b8d4386762?q=80&w=400"}
}

ORDERING = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🐠 **FISH SHOP BOT** 🐠\nSilakan pilih menu di bawah ini:"
    keyboard = [
        [InlineKeyboardButton("🖼️ Lihat Katalog", callback_data='lihat_katalog')],
        [InlineKeyboardButton("🛒 Pesan Ikan", callback_data='pesan_ikan')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    for key, ikan in KATALOG.items():
        caption = f"🏷️ *{ikan['nama']}*\n💰 Harga: Rp{ikan['harga']:,}"
        await query.message.reply_photo(photo=ikan['foto'], caption=caption, parse_mode='Markdown')
    
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='kembali')]]
    await query.message.reply_text("Ingin memesan? Klik tombol Kembali lalu pilih Pesan.", reply_markup=InlineKeyboardMarkup(keyboard))

async def proses_pesan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton(f"{v['nama']} (Rp{v['harga']:,})", callback_data=f"beli_{k}")] for k, v in KATALOG.items()]
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data='kembali')])
    
    await query.edit_message_text("Pilih ikan yang ingin kamu beli:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ORDERING

async def konfirmasi_pesanan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    key = query.data.replace("beli_", "")
    ikan = KATALOG[key]
    user = query.from_user

    # 1. Catat ke Google Sheets
    try:
        catat_ke_sheet(user.full_name, user.username, ikan['nama'], ikan['harga'])
        status_sheet = "✅ Data tercatat di Google Sheets."
    except Exception as e:
        status_sheet = f"⚠️ Gagal mencatat ke Sheets: {e}"

    # 2. Kirim Notif ke Admin
    pesan_admin = (
        f"🔔 **PESANAN MASUK**\n\n"
        f"👤 Pembeli: {user.full_name}\n"
        f"🆔 Username: @{user.username}\n"
        f"🐠 Produk: {ikan['nama']}\n"
        f"💸 Total: Rp{ikan['harga']:,}\n\n"
        f"Silakan hubungi pembeli untuk pembayaran."
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=pesan_admin, parse_mode='Markdown')

    # 3. Respon ke User
    await query.edit_message_text(
        f"Pesanan **{ikan['nama']}** berhasil dikirim!\n\nAdmin akan segera menghubungi kamu.\n\n{status_sheet}",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(proses_pesan, pattern='^pesan_ikan$')],
        states={ORDERING: [CallbackQueryHandler(konfirmasi_pesanan, pattern='^beli_')]},
        fallbacks=[CallbackQueryHandler(start, pattern='^kembali$')]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_katalog, pattern='^lihat_katalog$'))
    app.add_handler(CallbackQueryHandler(start, pattern='^kembali$'))
    app.add_handler(conv_handler)

    print("Bot Ikan Hias sudah meluncur... 🌊")
    app.run_polling()

if __name__ == '__main__':
    main()