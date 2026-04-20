import os
import logging
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

load_dotenv()

# --- SETUP ABSOLUTE PATH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- KONFIGURASI UTAMA ---
# Ubah token di sini jika .env bermasalah
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = 8313481314 

NOREK_BANK = "Bank BCA - 123456789 (A/N Dreamland)"
NOREK_DANA = "DANA - 08123456789 (A/N Dreamland)"

# State untuk ConversationHandler
CHOOSING_FISH, ASKING_QUANTITY, ASKING_ADDRESS, CHOOSING_PAYMENT = range(4)
# --- 1. PERBAIKAN KATALOG (TYPO FIX) ---
KATALOG = {
    "betta": {"nama": "Ikan Cupang Nemo", "harga": 50000, "foto": "cupang.jpg"},
    "guppy": {"nama": "Guppy Albino", "harga": 35000, "foto": "guppy.jpg"}, # Sudah jadi .jpg
    "arowana": {"nama": "Arwana Silver", "harga": 150000, "foto": "arowana.jpg"},
}

# --- 2. PERBAIKAN FUNGSI KIRIM FOTO ---
async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    
    await send_typing_action(context, chat_id, 1.0)
    await query.message.reply_text("📋 **KATALOG DREAMLANDFISH**", parse_mode='Markdown')
    
    for k, v in KATALOG.items():
        teks_ikan = f"🔹 **{v['nama']}**\n   └ Harga: Rp{v['harga']:,}"
        keyboard = [[InlineKeyboardButton(f"🛒 Pesan {v['nama']}", callback_data=f"beli_{k}")]]
        
        # Path absolut biar bot gak nyasar
        foto_path = os.path.join(BASE_DIR, v['foto'])
        
        # Cek apakah file fisik beneran ada di folder
        if os.path.exists(foto_path):
            try:
                with open(foto_path, 'rb') as photo_file:
                    await context.bot.send_photo(
                        chat_id=chat_id, 
                        photo=photo_file, 
                        caption=teks_ikan, 
                        reply_markup=InlineKeyboardMarkup(keyboard), 
                        parse_mode='Markdown'
                    )
            except Exception as e:
                # Jika koneksi/proxy bermasalah pas kirim foto
                print(f"Gagal kirim foto {v['foto']}: {e}")
                await context.bot.send_message(chat_id=chat_id, text=f"{teks_ikan}\n*(Koneksi lambat, gambar gagal muat)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            # Jika file emang ga ada di folder
            print(f"❌ FILE TIDAK DITEMUKAN: {foto_path}")
            await context.bot.send_message(chat_id=chat_id, text=f"{teks_ikan}\n*(File {v['foto']} tidak ada di folder)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    return CHOOSING_FISH

# --- FITUR ADVANCE 1: SIMULASI MENGETIK (TYPING EFFECT) ---
async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, duration: float = 1.0):
    """Membuat bot seolah-olah sedang mengetik pesan seperti manusia."""
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(duration)

# --- SISTEM KEAMANAN (ERROR HANDLER) ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Terjadi error: {context.error}")
    pesan_error = f"⚠️ **SYSTEM ALERT**\n\nError: `{context.error}`"
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=pesan_error, parse_mode='Markdown')
    except:
        pass 

# --- ALUR KERJA BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    # Animasi ngetik
    await send_typing_action(context, chat_id, 1.5)
    
    teks = (f"Halo kak **{user_name}**! 👋\n\n"
            "Selamat datang di **DreamlandFish Official**.\n"
            "Kami menyediakan ikan hias kualitas premium.\n\n"
            "Silakan cek koleksi kami di bawah ini 👇")
            
    keyboard = [[InlineKeyboardButton("🖼️ Buka Katalog Ikan", callback_data='lihat_katalog')]]
    
    if update.message:
        await update.message.reply_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    
    await send_typing_action(context, chat_id, 1.0)
    await query.message.reply_text("📋 **KATALOG DREAMLANDFISH**", parse_mode='Markdown')
    
    for k, v in KATALOG.items():
        teks_ikan = f"🔹 **{v['nama']}**\n   └ Harga: Rp{v['harga']:,}"
        keyboard = [[InlineKeyboardButton(f"🛒 Pesan {v['nama']}", callback_data=f"beli_{k}")]]
        foto_path = os.path.join(BASE_DIR, v['foto'])
        
        try:
            with open(foto_path, 'rb') as photo_file:
                await context.bot.send_photo(chat_id=chat_id, photo=photo_file, caption=teks_ikan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=f"{teks_ikan}\n*(Gambar sedang disinkronisasi)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    return CHOOSING_FISH

async def minta_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    key = query.data.replace("beli_", "")
    ikan = KATALOG[key]
    context.user_data['ikan_dipilih'] = ikan
    
    # FITUR ADVANCE 2: Dynamic Edit Message
    await query.edit_message_reply_markup(reply_markup=None) # Hilangkan tombol agar rapi
    await query.message.reply_text(f"✅ Anda memilih **{ikan['nama']}**.\n\n🔢 Masukkan **jumlah ekor** yang ingin dipesan (contoh: 2):", parse_mode='Markdown')
    return ASKING_QUANTITY

async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("⚠️ *Mohon maaf, masukkan jumlah dalam bentuk angka (contoh: 3).*")
        return ASKING_QUANTITY
        
    qty = int(update.message.text)
    
    # FITUR ADVANCE 3: Validasi Logika Bisnis
    if qty <= 0:
        await update.message.reply_text("⚠️ *Jumlah pesanan minimal 1 ekor. Silakan masukkan lagi:*", parse_mode='Markdown')
        return ASKING_QUANTITY
        
    context.user_data['qty'] = qty
    context.user_data['total_harga'] = context.user_data['ikan_dipilih']['harga'] * qty
    
    await send_typing_action(context, update.effective_chat.id, 0.5)
    await update.message.reply_text(f"📍 **Alamat Pengiriman:**\nSilakan ketik alamat lengkap pengiriman paket Anda:")
    return ASKING_ADDRESS

async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['alamat_user'] = update.message.text
    chat_id = update.effective_chat.id
    
    # Simulasi sistem memproses data
    loading_msg = await update.message.reply_text("🔄 *Sistem sedang membuat nota pembayaran...*", parse_mode='Markdown')
    await asyncio.sleep(1.5)
    
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    waktu = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # FITUR ADVANCE 4: Format Nota Profesional (Monospace Block)
    nota = (f"🧾 **INVOICE PEMBAYARAN** 🧾\n"
            f"```text\n"
            f"Waktu  : {waktu}\n"
            f"Produk : {ikan['nama']}\n"
            f"Jumlah : {qty} Ekor\n"
            f"Total  : Rp{total:,}\n"
            f"```\n"
            f"📍 **Tujuan:** {alamat}\n\n"
            f"Silakan transfer sesuai total di atas ke:\n"
            f"🏦 `{NOREK_BANK}`\n"
            f"📱 `{NOREK_DANA}`\n\n"
            f"Klik tombol di bawah ini JIKA SUDAH TRANSFER:")
    
    keyboard = [[InlineKeyboardButton("💳 Konfirmasi Transfer Bank", callback_data='pay_rekening')],
                [InlineKeyboardButton("💳 Konfirmasi Transfer DANA", callback_data='pay_dana')],
                [InlineKeyboardButton("❌ Batalkan Pesanan", callback_data='cancel_order')]]
                
    await loading_msg.delete() # Hapus pesan loading
    await context.bot.send_message(chat_id=chat_id, text=nota, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return CHOOSING_PAYMENT

async def konfirmasi_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # FITUR ADVANCE 5: Fitur Cancel Order
    if query.data == 'cancel_order':
        await query.edit_message_text("❌ *Pesanan Anda telah dibatalkan.* Ketik /start untuk memesan kembali.", parse_mode='Markdown')
        context.user_data.clear()
        return ConversationHandler.END
    
    ikan = context.user_data['ikan_dipilih']
    qty = context.user_data['qty']
    total = context.user_data['total_harga']
    alamat = context.user_data['alamat_user']
    metode = "Bank" if query.data == 'pay_rekening' else "DANA"
    user = query.from_user
    
    # Kirim ke Admin
    admin_msg = (f"🚨 **NEW ORDER ALERT!** 🚨\n\n"
                 f"👤 Pembeli: [{user.full_name}](tg://user?id={user.id})\n"
                 f"🐟 Item: {ikan['nama']} ({qty}x)\n"
                 f"💰 Rp{total:,} via {metode}\n"
                 f"📍 Alamat: `{alamat}`")
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Gagal kirim admin: {e}")

    keyboard = [[InlineKeyboardButton("💬 Hubungi Admin via WA", url='https://wa.me/6287828062625')]]
    
    # Animasi Sukses
    await query.edit_message_text("🔄 *Memverifikasi pembayaran...*", parse_mode='Markdown')
    await asyncio.sleep(1.5)
    await query.edit_message_text(f"✅ **Pembayaran Sedang Diverifikasi!**\n\nTerima kasih, pesanan {ikan['nama']} Anda akan segera diproses oleh Admin. Kami akan menghubungi Anda segera.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    context.user_data.clear() # Bersihkan keranjang
    return ConversationHandler.END

# Fitur Cancel dari Command
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Pesanan dibatalkan. Ketik /start jika ingin mulai dari awal.")
    context.user_data.clear()
    return ConversationHandler.END

# --- MAIN PROGRAM ---

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    if not TOKEN:
        print("❌ CRITICAL ERROR: TOKEN KOSONG!")
        return

    # Builder dengan Sistem Anti-Badai
    app = (
        Application.builder()
        .token(TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(minta_jumlah, pattern='^beli_')],
        states={
            ASKING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_alamat)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_pembayaran)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(konfirmasi_akhir, pattern='^(pay_|cancel_order)')]
        },
        fallbacks=[
            CommandHandler('start', start),
            CommandHandler('cancel', cancel_command)
        ]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(menu_katalog, pattern='^lihat_katalog$'))
    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)
    
    print("Bot Enterprise Edition (VVIP) Berhasil Berjalan 🚀🔥")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()