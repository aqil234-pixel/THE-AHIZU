import os
import logging
import asyncio
import random
import socket
import time
import psutil
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    ConversationHandler, 
    MessageHandler, 
    filters
)

# --- KONFIGURASI PATH & ENV ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# Setup Logging Error ke File
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.ERROR, 
    filename=os.path.join(BASE_DIR, 'bot_errors.log'), 
    filemode='a'
)

# --- KONFIGURASI UTAMA ---
TOKEN = os.getenv("BOT_TOKEN")

# Proteksi jika ADMIN_ID kosong atau bukan angka agar bot tidak crash saat start
try:
    ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
except ValueError:
    ADMIN_ID = None
    print("⚠️ WARNING: ADMIN_ID di Environment Variables bukan angka yang valid!")

ADMIN_WA = os.getenv("ADMIN_WA")
GROQ_API_KEY = os.getenv("API_KEY")

# Inisialisasi Client Groq jika API Key tersedia
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

NAMA_FOLDER_FOTO = "assets" 
PATH_FOTO_LENGKAP = os.path.join(BASE_DIR, NAMA_FOLDER_FOTO)

# --- DATABASE SEMENTARA (Memory) ---
DATABASE_ORDER = {}

# States untuk Conversation Handler
CHOOSING_FISH, ASKING_NAME, ASKING_ADDRESS, ASKING_QUANTITY, CHOOSING_PAYMENT = range(5)
ADMIN_UPDATE_STOK_PILIH, ADMIN_UPDATE_STOK_INPUT = range(10, 12)

KATALOG = {
    "betta": {
        "nama": "Ikan Cupang Nemo", 
        "harga": 50000, 
        "foto": "cupang.jpg", 
        "stok": 10,
        "deskripsi": "Ikan cupang hias dengan corak warna-warni mirip ikan nemo. Agresif dan lincah." 
    },
    "guppy": {
        "nama": "Guppy Albino", 
        "harga": 35000, 
        "foto": "guppy.jpg",
        "stok": 20,
        "deskripsi": "Ikan guppy anggun berwarna putih kemerahan (albino). Sangat cocok untuk aquascape."
    },
    "arowana": {
        "nama": "Arwana Silver", 
        "harga": 150000, 
        "foto": "arowana.jpg", 
        "stok": 5,
        "deskripsi": "Ikan predator eksotis berukuran sedang. Melambangkan keberuntungan dan kemewahan."
    },
}

# --- ALUR CLIENT (USER) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id 
    
    teks = (
        "Selamat datang di *dreamlandfish.myd* 🐟\n"
        "Pusat ikan hias terbaik impian Anda!\n\n"
        "💡 _Tanya seputar ikan? Langsung ketik aja di chat, Admin AI kami siap bantu!_"
    )
    
    keyboard = [
        [InlineKeyboardButton("🖼️ Lihat Katalog", callback_data='lihat_katalog')],
        [InlineKeyboardButton("🛒 Pesan Ikan", callback_data='lihat_katalog')],
        [InlineKeyboardButton("🏪 Informasi Toko", callback_data='info_toko')],
        [InlineKeyboardButton("🤖 Cara Chat dengan AI", callback_data='bantuan_ai')]
    ]
    
    # --- LOGIKA KHUSUS ADMIN ---
    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        keyboard.append([InlineKeyboardButton("🐞 CEK BUG (Admin Only)", callback_data="admin_cek_bug")])
        keyboard.append([InlineKeyboardButton("📦 Update Stok Ikan", callback_data="admin_update_stok")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    logo_path = os.path.join(PATH_FOTO_LENGKAP, "logo_dream.jpg")

    if update.message:
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=teks, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(teks, reply_markup=reply_markup, parse_mode='Markdown')
            
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        try: 
            await query.delete_message()
        except: 
            pass
            
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=teks, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=teks, reply_markup=reply_markup, parse_mode='Markdown')

    return ConversationHandler.END

async def bantuan_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="💡 CARA PENGGUNAAN:\n\nNggak perlu klik menu apa-apa, Kak! Langsung aja ketik pertanyaan Kakak. Nanti AI kami bakal otomatis balas! 🤖✨", show_alert=True)

async def info_toko(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    teks_info = (
        "🏪 *INFORMASI TOKO DREAMLANDFISH*\n"
        "━━━━━━━━━━━━━━━\n"
        "🐟 Nama Toko: Dreamlandfish\n\n"
        "📍 *Alamat Toko:*\n"
        "Sumberan, Sumberagung, Moyudan,\n"
        "Sleman Regency, Special Region of Yogyakarta 55563\n\n"
        "🕒 *Jam Operasional:*\n"
        "Setiap Hari : 08.00 - 21.00 WIB\n\n"
        "📱 *Kontak Admin:*\n"
        "0878-2806-2625\n\n"
        "📸 *Instagram:*\n"
        "@dreamlandfish.myd\n\n"
        "📝 *Tentang Toko:*\n"
        "Menyediakan berbagai macam ikan hias seperti Guppy, Platy, Molly, Cupang, Channa, dan lainnya.\n\n"
        "✨ Terima kasih telah mengunjungi Dreamlandfish!"
    )

    keyboard = [
        [InlineKeyboardButton("📍 Buka Google Maps", url="https://maps.google.com")],
        [InlineKeyboardButton("💬 Chat Admin", url=f"https://wa.me/{ADMIN_WA if ADMIN_WA else ''}")],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="start_back")]
    ]

    await query.message.reply_text(
        teks_info,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def menu_katalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try: 
        await query.delete_message()
    except: 
        pass
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📋 **KATALOG KAMI:**", parse_mode='Markdown')
    
    for k, v in KATALOG.items():
        foto_path = os.path.join(PATH_FOTO_LENGKAP, v['foto'])
        teks_ikan = f"🔹 **{v['nama']}**\n💰 Harga: Rp{v['harga']:,}\n📦 Stok: {v.get('stok', 0)} ekor"
        
        keyboard = [
            [InlineKeyboardButton("📖 Lihat Deskripsi", callback_data=f"desc_{k}")],
            [InlineKeyboardButton(f"🛒 Pesan {v['nama']}", callback_data=f"beli_{k}")],
        ]
        
        try:
            with open(foto_path, 'rb') as f:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f, caption=teks_ikan, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        except FileNotFoundError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{teks_ikan}\n*(Gambar tdk ditemukan)*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    return CHOOSING_FISH

async def tampilkan_deskripsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    key = query.data.split("_")[1] 
    
    if key in KATALOG:
        ikan = KATALOG[key]
        deskripsi = ikan.get("deskripsi", "Deskripsi untuk ikan ini belum tersedia.")
        
        teks_popup = (
            f"🐟 {ikan['nama'].upper()}\n"
            f"💰 Harga: Rp{ikan['harga']:,}\n\n"
            f"📝 KETERANGAN:\n"
            f"{deskripsi}"
        )
        await query.answer(text=teks_popup, show_alert=True)
    else:
        await query.answer(text="⚠️ Deskripsi tidak ditemukan.", show_alert=True)

async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not groq_client:
        await update.message.reply_text("Waduh, fitur AI belum dikonfigurasi oleh Admin (API Key kosong).")
        return

    pesan_user = update.message.text
    daftar_produk = ""
    for k, v in KATALOG.items():
        daftar_produk += f"- {v['nama']}: Rp{v['harga']:,} ({v['deskripsi']})\n"

    system_prompt = f"""
Kamu adalah 'gammy', asisten admin toko ikan 'Dreamlandfish.myd'. 
Gaya bicara: Gaul, santai, pake bahasa anak muda (pake kata 'kak' yang asik), ramah, dan informatif.

TUGAS UTAMA:
1. Menjawab pertanyaan tentang ikan yang ada di katalog kami.
2. Memberikan tips perawatan ikan secara umum.
3. Mengarahkan orang untuk klik tombol 'Lihat Katalog' jika mereka mau beli.

DATA KATALOG KAMI:
{daftar_produk}

ATURAN PENTING:
- JANGAN jawab kalau ditanya hal di luar ikan (politik, agama, teknologi, dll). Bilang aja "Waduh, gue cuma jago urusan ikan nih, kak! Tanya soal ikan aja yuk."
- Kalau ikan yang ditanya GAK ADA di katalog, tawarkan opsi yang ada.
- Jawab singkat padat, jangan terlalu panjang.
"""
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pesan_user}
            ],
            model="llama-3.1-8b-instant",
        )
        
        balasan_ai = chat_completion.choices[0].message.content
        await update.message.reply_text(balasan_ai)
        
    except Exception as e:
        logging.error(f"Error Groq: {e}")
        await update.message.reply_text("Waduh, otak gue lagi nge-lag dikit nih. Coba tanya lagi dong! 😅")

# --- FLOW PEMESANAN ---
async def minta_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("beli_", "")
    context.user_data['ikan_dipilih'] = KATALOG[key]
    
    await query.message.reply_text(f"📝 Anda akan memesan **{KATALOG[key]['nama']}**.\n\nSilakan ketik Nama Lengkap Anda:", parse_mode='Markdown')
    return ASKING_NAME

async def minta_alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama_user'] = update.message.text
    await update.message.reply_text("📍 Silakan ketik Alamat Lengkap pengiriman Anda:", parse_mode='Markdown')
    return ASKING_ADDRESS

async def minta_jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['alamat_user'] = update.message.text
    
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="qty_1"),
            InlineKeyboardButton("2", callback_data="qty_2"),
            InlineKeyboardButton("3", callback_data="qty_3")
        ],
        [
            InlineKeyboardButton("4", callback_data="qty_4"),
            InlineKeyboardButton("5", callback_data="qty_5"),
            InlineKeyboardButton("10", callback_data="qty_10")
        ]
    ]
    
    teks = "🔢 **Pilih Jumlah Pesanan:**\n\
