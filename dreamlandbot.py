#-- import library ---
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
    "betta": {"nama": "Ikan Cupang Nemo", "harga": 50000, "foto": "cupang.jpg"},
    "guppy": {"nama": "Guppy Albino", "harga": 35000, "foto": "guppy.jpg"},
    "arowana": {"nama": "Arwana Silver", "harga": 150000, "foto": "arowana.jpg"},
}
# --- 3. FUNGSI BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    teks = (f"Halo {user_name}! 👋\n"
            f"Selamat datang di **dreamlandfish.myd**.\n"
            f"Silakan lihat katalog kami di bawah ini:")
    keyboard = [[InlineKeyboardButton("🖼️ Lihat Katalog", callback_data='lihat_katalog')]]
    if update.message:
        await update.message.reply_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📋 **KATALOG DREAMLANDFISH**", parse_mode='Markdown')
    for k, v in KATALOG.items():
        teks_ikan = f"🔹 **{v['nama']}**\n   └ Harga: Rp{v['harga']:,}"
        keyboard = [[InlineKeyboardButton(f"🛒 Pesan {v['nama']}", callback_data=f"beli_{k}")]]
        try:
            with open(v['foto'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_file, caption=teks_ikan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except FileNotFoundError:
            await query.message.reply_text(f"{teks_ikan}\n*(File {v['foto']} tidak ditemukan)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    await query.message.reply_text("---", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='start_back')]]))
    return CHOOSING_FISH

async def minta_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("beli_", "")
    context.user_data['ikan_dipilih'] = KATALOG[key]
    await query.message.reply_text(f"🔢 Mau pesan berapa ekor **{KATALOG[key]['nama']}**?", parse_mode='Markdown')
    return ASKING_QUANTITY

async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Masukkan angka saja.")
        return ASKING_QUANTITY
    context.user_data['qty'] = int(update.message.text)
    context.user_data['total_harga'] = context.user_data['ikan_dipilih']['harga'] * context.user_data['qty']
    await update.message.reply_text(f"📍 **Alamat Pengiriman:**\nKetik alamat lengkap Anda:", parse_mode='Markdown')
    return ASKING_ADDRESS

async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['alamat_user'] = update.message.text
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

    nota_teks = (
        f"📝 **NOTA PEMESANAN DIGITAL**\n"
        f"------------------------------------------\n"
        f"📅 **Waktu:** {waktu}\n"
        f"👤 **Pembeli:** {update.effective_user.full_name}\n"
        f"📦 **Produk:** {ikan['nama']}\n"
        f"🔢 **Jumlah:** {qty} ekor\n"
        f"📍 **Alamat:** {alamat}\n"
        f"------------------------------------------\n"
        f"💰 **TOTAL TAGIHAN: Rp{total:,}**\n"
        f"📌 **Status:** MENUNGGU PEMBAYARAN\n\n"
        f"Transfer ke:\n🏦 `{NOREK_BANK}`\n📱 `{NOREK_DANA}`"
    )
    
    keyboard = [[InlineKeyboardButton("✅ Sudah Transfer (Bank)", callback_data='pay_rekening')],
                [InlineKeyboardButton("✅ Sudah Transfer (DANA)", callback_data='pay_dana')]]
    await update.message.reply_text(nota_teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CHOOSING_PAYMENT

async def konfirmasi_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    metode = "Rekening" if query.data == 'pay_rekening' else "DANA"
    user = query.from_user
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")


    # Notif Admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **ORDER BARU MASUK**\n\nUser: {user.full_name}\nProduk: {ikan['nama']} ({qty}x)\nTotal: Rp{total:,}\nMetode: {metode}",
        parse_mode='Markdown'
    )

    context.user_data['nota_final'] = (
        f"📝 **NOTA PEMESANAN DIGITAL**\n"
        f"------------------------------------------\n"
        f"📅 **Waktu:** {waktu}\n"
        f"👤 **Pembeli:** {user.full_name}\n"
        f"📦 **Produk:** {ikan['nama']}\n"
        f"🔢 **Jumlah:** {qty} ekor\n"
        f"📍 **Alamat:** {alamat}\n"
        f"------------------------------------------\n"
        f"💰 **TOTAL TAGIHAN: Rp{total:,}**\n"
        f"📌 **Status:** Menunggu Verifikasi Admin"
    )

    keyboard_selesai = [[InlineKeyboardButton("📜 1. Lihat Nota", callback_data='lihat_nota_akhir')],
                        [InlineKeyboardButton("💬 2. Hubungi Admin", url='https://wa.me/6287828062625')]]

    await query.edit_message_text(f"✅ **Konfirmasi Diterima!**\n\nTerima kasih {user.first_name}, pesanan Rp{total:,} telah dicatat.", 
                                  reply_markup=InlineKeyboardMarkup(keyboard_selesai), parse_mode='Markdown')
    return ConversationHandler.END

async def tampilkan_nota_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nota = context.user_data.get('nota_final', "⚠️ Nota tidak ditemukan.")
    await query.message.reply_text(nota, parse_mode='Markdown')

def main():
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(minta_jumlah, pattern='^beli_')],
        states={
            ASKING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_alamat)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_pembayaran)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(konfirmasi_akhir, pattern='^pay_')]
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^start_back$')]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(menu_katalog, pattern='^lihat_katalog$'))
    app.add_handler(CallbackQueryHandler(tampilkan_nota_akhir, pattern='^lihat_nota_akhir$'))
    app.add_handler(conv_handler)
    print("Bot Dreamland Fish v5.5 (FIXED) 🚀")
    app.run_polling()

if __name__ == '__main__':
    main()