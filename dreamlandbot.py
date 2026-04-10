import logging
import asyncio
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# --- 1. KONFIGURASI ---
TOKEN = '8360782987:AAHq0sCk99_H_vq73HtTsPP91eVeRX7YoNA'
ADMIN_ID = 8313481314 

NOREK_BANK = "Bank BCA - 123456789 (A/N Dreamland)"
NOREK_DANA = "DANA - 08123456789 (A/N Dreamland)"

CHOOSING_FISH, ASKING_QUANTITY, ASKING_ADDRESS, CHOOSING_PAYMENT = range(4)

KATALOG = {
    "betta": {"nama": "Ikan Cupang Nemo", "harga": 50000, "foto": "cupang.jpg"},
    "guppy": {"nama": "Guppy Albino", "harga": 35000, "foto": "guppy.jpg"},
    "arowana": {"nama": "Arwana Silver", "harga": 150000, "foto": "arowana.jpg"},
}

# --- 2. ERROR HANDLING SYSTEM ---

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log error dan kirim notif ke Admin agar bot tidak mati total."""
    logging.error(f"Terjadi error: {context.error}")
    
    pesan_error = f"⚠️ **BOT REPORT ERROR**\n\nDetail: `{context.error}`"
    try:
        # Beritahu Admin kalau ada yang rusak
        await context.bot.send_message(chat_id=ADMIN_ID, text=pesan_error, parse_mode='Markdown')
        
        # Beritahu User kalau ada gangguan teknis (opsional)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("Maaf, terjadi gangguan teknis. Admin sudah diberitahu! 🙏")
    except:
        pass # Jika kirim pesan error pun gagal, biarkan saja agar bot tidak loop error

# --- 3. FUNGSI UTAMA ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    teks = f"Halo {user_name}! 👋\nSelamat datang di **dreamlandfish.myd**.\nSilakan lihat katalog kami:"
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
            # Pengaman Foto: Jika file tidak ada, bot tidak akan crash
            with open(v['foto'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_file, caption=teks_ikan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except (FileNotFoundError, Exception):
            # Jika foto gagal kirim, kirim teks deskripsi saja
            await query.message.reply_text(f"{teks_ikan}\n*(Foto sedang diperbarui)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    return CHOOSING_FISH

async def minta_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("beli_", "")
    context.user_data['ikan_dipilih'] = KATALOG[key]
    await query.message.reply_text(f"🔢 Mau pesan berapa ekor **{KATALOG[key]['nama']}**?")
    return ASKING_QUANTITY

async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Validasi input angka agar tidak error saat dikali harga
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ Tolong masukkan **angka saja** (contoh: 2).")
        return ASKING_QUANTITY
        
    context.user_data['qty'] = int(update.message.text)
    context.user_data['total_harga'] = context.user_data['ikan_dipilih']['harga'] * context.user_data['qty']
    await update.message.reply_text(f"📍 **Alamat Pengiriman:**\nKetik alamat lengkap Anda:")
    return ASKING_ADDRESS

async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['alamat_user'] = update.message.text
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    nota = (f"📝 **NOTA PEMESANAN**\n------------------\n"
            f"📅 {waktu}\n📦 {ikan['nama']} ({qty} ekor)\n📍 {alamat}\n"
            f"💰 **Total: Rp{total:,}**\n\nTransfer ke:\n🏦 `{NOREK_BANK}`\n📱 `{NOREK_DANA}`")
    
    keyboard = [[InlineKeyboardButton("✅ Sudah Transfer (Bank)", callback_data='pay_rekening')],
                [InlineKeyboardButton("✅ Sudah Transfer (DANA)", callback_data='pay_dana')]]
    await update.message.reply_text(nota, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CHOOSING_PAYMENT

async def konfirmasi_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Ambil data dari sesi user
    ikan = context.user_data.get('ikan_dipilih', {'nama': 'Ikan'})
    qty = context.user_data.get('qty', 0)
    total = context.user_data.get('total_harga', 0)
    alamat = context.user_data.get('alamat_user', '-')
    metode = "Rekening" if query.data == 'pay_rekening' else "DANA"
    user = query.from_user
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Kirim Notif ke Admin (Proteksi agar tidak error jika Admin ID salah)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 **ORDER BARU**\n\n👤 User: {user.full_name}\n🐠 Produk: {ikan['nama']}\n🔢 Qty: {qty}\n💰 Total: Rp{total:,}\n📍 Alamat: {alamat}\n💳 Metode: {metode}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Gagal kirim notif admin: {e}")

    # Simpan nota untuk dilihat nanti
    context.user_data['nota_final'] = f"📝 **NOTA ANDA**\n📅 {waktu}\n📦 {ikan['nama']} ({qty}x)\n💰 Total: Rp{total:,}\n📍 {alamat}"
    
    keyboard = [[InlineKeyboardButton("📜 Lihat Nota", callback_data='lihat_nota_akhir')],
                [InlineKeyboardButton("💬 Hubungi Admin", url='https://wa.me/6287828062625')]]

    await query.edit_message_text(f"✅ **Berhasil!** Pesanan telah diteruskan ke Admin untuk diverifikasi.", 
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def tampilkan_nota_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nota = context.user_data.get('nota_final', "⚠️ Nota tidak ditemukan atau sesi telah berakhir.")
    await query.message.reply_text(nota, parse_mode='Markdown')

# --- 4. MAIN PROGRAM ---

def main():
    # Setup Logging untuk memantau error di konsol PythonAnywhere
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    app = Application.builder().token(TOKEN).build()
    
    # Handler Percakapan
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
    
    # PASANG PENGAMAN ERROR GLOBAL
    app.add_error_handler(error_handler)
    
    print("Bot v5.9 (STABLE & PROTECTED) 🚀")
    app.run_polling()

if __name__ == '__main__':
    main()