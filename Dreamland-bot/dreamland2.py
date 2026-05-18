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

# Proteksi jika ADMIN_ID kosong atau bukan angka
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

# Global DATA KATALOG yang bisa di-update stoknya
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
        "deskripsi": "Ikan predator exotic berukuran sedang. Melambangkan keberuntungan dan kemewahan."
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

    # Deteksi jika dipanggil dari text message atau callback button
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
        [InlineKeyboardButton("📍 Buka Google Maps", url="https://maps.google.com/?q=Dreamlandfish+Moyudan")],
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
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📋 **KATALOG LIVE STOK KAMI:**", parse_mode='Markdown')
    
    for k, v in KATALOG.items():
        foto_path = os.path.join(PATH_FOTO_LENGKAP, v['foto'])
        
        # Sisa stok dinamis yang diambil langsung dari database KATALOG global
        teks_ikan = f"🔹 **{v['nama']}**\n💰 Harga: Rp{v['harga']:,}\n📦 Sisa Stok: *{v.get('stok', 0)} ekor*"
        
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
        daftar_produk += f"- {v['nama']}: Rp{v['harga']:,} (Sisa Stok: {v['stok']}) - {v['deskripsi']}\n"

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
    context.user_data['ikan_key_dipilih'] = key
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
    
    teks = """🔢 **Pilih Jumlah Pesanan:**

_( SILAHKAN BUAT PESANAN )_"""
    
    await update.message.reply_text(teks, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ASKING_QUANTITY

async def minta_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try: 
            await query.delete_message()
        except: 
            pass
        jumlah = int(query.data.split("_")[1]) 
    else:
        if not update.message.text.isdigit():
            await update.message.reply_text("⚠️ Masukkan angka yang valid!")
            return ASKING_QUANTITY
        jumlah = int(update.message.text)

    # Validasi jika pesanan melebihi sisa stok yang tersedia
    stok_tersedia = context.user_data['ikan_dipilih']['stok']
    if jumlah > stok_tersedia:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"❌ Maaf, jumlah pesanan ({jumlah} ekor) melebihi sisa stok yang tersedia ({stok_tersedia} ekor).\n\nSilakan masukkan kembali jumlah yang sesuai:"
        )
        return ASKING_QUANTITY

    context.user_data['qty'] = jumlah
    total_harga = context.user_data['ikan_dipilih']['harga'] * context.user_data['qty']
    context.user_data['total_harga'] = total_harga
    
    teks_bayar = (
        f"💳 **PEMBAYARAN**\n"
        f"━━━━━━━━━━━━━\n"
        f"Total Tagihan: **Rp{total_harga:,}**\n"
        f"━━━━━━━━━━━━━\n"
        f"Silakan transfer ke:\n"
        f"🏦 BCA: `123456789` (A/N Dreamland)\n"
        f"🏦 Mandiri: `123456789` (A/N Dreamland)\n"
        f"📱 Atau scan QRIS di bawah ini.\n"
        f"━━━━━━━━━━━━━"
    )
    
    keyboard = [[InlineKeyboardButton("✅ Selesai Transfer & Buat Nota", callback_data='buat_nota')]]
    qris_path = os.path.join(PATH_FOTO_LENGKAP, "qris.jpg")
    
    try:
        with open(qris_path, 'rb') as f:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f, caption=teks_bayar, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=teks_bayar, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    return CHOOSING_PAYMENT
    
async def buat_nota_akhir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    order_id = f"ORD-{random.randint(1000, 9999)}"
    ikan_key = context.user_data['ikan_key_dipilih']
    qty_beli = context.user_data['qty']

    # POTONG STOK DI KATALOG UTAMA SECARA OTOMATIS
    if KATALOG[ikan_key]['stok'] >= qty_beli:
        KATALOG[ikan_key]['stok'] -= qty_beli
    
    DATABASE_ORDER[order_id] = {
        'nama': context.user_data['nama_user'],
        'alamat': context.user_data['alamat_user'],
        'ikan': context.user_data['ikan_dipilih']['nama'],
        'qty': qty_beli,
        'total': context.user_data['total_harga'],
        'status_bayar': "⏳ Menunggu Verifikasi",
        'status_barang': "📦 Sedang Diproses"
    }
    
    nota = (
        f"🧾 **NOTA PEMESANAN ({order_id})**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Nama: {DATABASE_ORDER[order_id]['nama']}\n"
        f"📍 Alamat: {DATABASE_ORDER[order_id]['alamat']}\n"
        f"🐟 Pesanan: {DATABASE_ORDER[order_id]['ikan']}\n"
        f"🔢 Jumlah: {DATABASE_ORDER[order_id]['qty']} ekor\n"
        f"💰 Total: Rp{DATABASE_ORDER[order_id]['total']:,}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 Status Bayar: {DATABASE_ORDER[order_id]['status_bayar']}\n"
        f"🚚 Status Barang: {DATABASE_ORDER[order_id]['status_barang']}\n\n"
        f"✨ _Terima kasih telah berbelanja di DreamlandFish! Sisa stok produk otomatis diperbarui._"
    )
    
    keyboard_nota = [
        [InlineKeyboardButton("🔍 Cek Status Terkini", callback_data=f"cekstatus_{order_id}")],
        [InlineKeyboardButton("💬 Hubungi Admin", url=f"https://wa.me/{ADMIN_WA if ADMIN_WA else ''}")]
    ]
    
    await query.delete_message()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=nota, reply_markup=InlineKeyboardMarkup(keyboard_nota), parse_mode='Markdown')
    
    # Notifikasi ke Admin
    if ADMIN_ID:
        admin_notif = f"🚨 **ORDER BARU MASUK!** 🚨\nID: {order_id}\nNama: {DATABASE_ORDER[order_id]['nama']}\nTotal: Rp{DATABASE_ORDER[order_id]['total']:,}\n*Stok otomatis terpotong di sistem.*"
        admin_keyboard = [
            [InlineKeyboardButton("✅ Konfirmasi Lunas", callback_data=f"setlunas_{order_id}")],
            [InlineKeyboardButton("🚚 Kirim Barang", callback_data=f"setkirim_{order_id}")]
        ]
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notif, reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode='Markdown')
        except: 
            pass
    
    context.user_data.clear()
    return ConversationHandler.END

# --- CALLBACK GLOBAL ---
async def cek_status_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    order_id = query.data.split("_")[1]
    
    if order_id in DATABASE_ORDER:
        data = DATABASE_ORDER[order_id]
        status_msg = (
            f"🔍 **STATUS UPDATE ({order_id})**\n"
            f"━━━━━━━━━━━━━\n"
            f"💳 PEMBAYARAN: {data['status_bayar']}\n"
            f"🚚 PENGIRIMAN: {data['status_barang']}\n"
            f"━━━━━━━━━━━━━\n"
        )
        await query.message.reply_text(status_msg, parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ Pesanan tidak ditemukan.")

async def admin_update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
        
    action, order_id = query.data.split("_")
    
    if order_id in DATABASE_ORDER:
        if action == "setlunas":
            DATABASE_ORDER[order_id]['status_bayar'] = "✅ LUNAS"
            await query.edit_message_text(f"✅ {order_id} telah di-set LUNAS.")
        elif action == "setkirim":
            DATABASE_ORDER[order_id]['status_barang'] = "🚀 SUDAH DIKIRIM"
            await query.edit_message_text(f"🚀 {order_id} telah di-set DIKIRIM.")

def check_connectivity(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return "✅ ONLINE"
    except Exception:
        return "❌ OFFLINE"

async def get_bot_diagnostics():
    start_time = time.time()
    tg_status = check_connectivity("api.telegram.org", 443)
    google_status = check_connectivity("google.com", 80)
    latency = round((time.time() - start_time) * 1000, 2)
    
    log_size = "0 KB"
    log_path = os.path.join(BASE_DIR, 'bot_errors.log')
    if os.path.exists(log_path):
        log_size = f"{os.path.getsize(log_path) / 1024:.2f} KB"

    report = (
        "<code>[DREAMLAND DIAGNOSTICS]</code>\n"
        "<code>------------------------</code>\n"
        f"🌐 <b>Telegram API:</b> <code>{tg_status}</code>\n"
        f"🌍 <b>Google DNS:</b>   <code>{google_status}</code>\n"
        f"⚡ <b>Latency:</b>      <code>{latency}ms</code>\n"
        f"📁 <b>Log Size:</b>     <code>{log_size}</code>\n"
        f"🤖 <b>AI Status:</b>     <code>{'READY' if GROQ_API_KEY else 'MISSING'}</code>\n"
        "<code>------------------------</code>\n"
        f"⏰ <b>Server Time:</b> <code>{datetime.now().strftime('%H:%M:%S')}</code>"
    )
    return report

# --- FITUR CEK BUG & DOWNLOAD LOG FILE ---
async def admin_cek_bug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not ADMIN_ID or str(update.effective_user.id) != str(ADMIN_ID):
        await query.message.reply_text("⛔ Restricted Area!")
        return

    # Kirim diagnosistem awal ke chat
    status_report = await get_bot_diagnostics()
    await query.message.reply_text(status_report, parse_mode="HTML")

    log_file_path = os.path.join(BASE_DIR, 'bot_errors.log')
    
    # Periksa apakah file log tersedia dan berisi data error
    if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 0:
        with open(log_file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                caption="📄 <b>Ini File Log Error Bot Anda. Silakan diunduh untuk dibaca.</b>",
                parse_mode="HTML"
            )
    else:
        await query.message.reply_text("✨ <b>Terminal Clean:</b> Tidak ditemukan rekaman file error log saat ini.")

# --- FITUR ADMIN UPDATE STOK ---
async def admin_pilih_ikan_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for k, v in KATALOG.items():
        # Menampilkan nama ikan beserta sisa stok yang aktif saat ini
        keyboard.append([InlineKeyboardButton(f"{v['nama']} (Stok: {v.get('stok', 0)})", callback_data=f"upstok_{k}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="start_back")])
    
    await query.edit_message_text("🛠 **ADMIN MODE: UPDATE STOK**\nPilih produk ikan yang ingin diubah jumlah sisa stoknya:", 
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ADMIN_UPDATE_STOK_INPUT

async def admin_input_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ikan_key = query.data.replace("upstok_", "")
    context.user_data['edit_ikan_key'] = ikan_key
    await query.answer()
    
    await query.edit_message_text(f"🔢 Masukkan angka jumlah stok baru untuk **{KATALOG[ikan_key]['nama']}** (Stok saat ini: {KATALOG[ikan_key]['stok']}):", parse_mode='Markdown')
    return ADMIN_UPDATE_STOK_INPUT

async def admin_simpan_stok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("⚠️ Harap masukkan angka bulat saja (contoh: 25)!")
        return ADMIN_UPDATE_STOK_INPUT
    
    ikan_key = context.user_data.get('edit_ikan_key')
    stok_baru = int(text)
    
    if ikan_key in KATALOG:
        # Menyimpan secara permanen ke dictionary KATALOG global
        KATALOG[ikan_key]['stok'] = stok_baru
        await update.message.reply_text(f"✅ Berhasil! Stok **{KATALOG[ikan_key]['nama']}** sekarang diupdate menjadi **{stok_baru}** ekor dan langsung aktif di katalog live user.")
    
    context.user_data.clear()
    
    # Kembali ke menu start awal admin
    return await start(update, context)

# --- MAIN ENGINE ---
def main():
    if not TOKEN:
        print("❌ ERROR DEPLOYMENT: KODE BERHENTI KARENA 'BOT_TOKEN' KOSONG!")
        return

    app = Application.builder().token(TOKEN).build()
    
    # Handlers Global / Command Dasar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern='^start_back$'))
    app.add_handler(CallbackQueryHandler(admin_cek_bug_callback, pattern='^admin_cek_bug$'))
    app.add_handler(CallbackQueryHandler(menu_katalog, pattern='^lihat_katalog$'))
    app.add_handler(CallbackQueryHandler(tampilkan_deskripsi, pattern='^desc_')) 
    app.add_handler(CallbackQueryHandler(cek_status_order, pattern='^cekstatus_'))
    app.add_handler(CallbackQueryHandler(admin_update_status, pattern='^(setlunas_|setkirim_)'))
    app.add_handler(CallbackQueryHandler(bantuan_ai, pattern='^bantuan_ai$'))
    app.add_handler(CallbackQueryHandler(info_toko, pattern='^info_toko$'))

    # Conversation Admin Update Stok
    admin_stok_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_pilih_ikan_stok, pattern='^admin_update_stok$')],
        states={
            ADMIN_UPDATE_STOK_INPUT: [
                CallbackQueryHandler(admin_input_stok, pattern='^upstok_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_simpan_stok)
            ],
        },
        fallbacks=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^start_back$')],
        allow_reentry=True
    )
    app.add_handler(admin_stok_conv)

    # Conversation Flow Pemesanan
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(minta_nama, pattern='^beli_')],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_alamat)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_jumlah)],
            ASKING_QUANTITY: [
                CallbackQueryHandler(minta_pembayaran, pattern='^qty_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, minta_pembayaran)
            ],
            CHOOSING_PAYMENT: [CallbackQueryHandler(buat_nota_akhir, pattern='^buat_nota$')]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    app.add_handler(conv_handler)

    # Chat AI (WAJIB paling bawah)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

    print("🚀 Bot Dreamland RUNNING...")
    app.run_polling()
    
if __name__ == '__main__':
    main()
