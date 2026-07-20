"""
Noon to'lov boti — Telegram xabarlarini Notion "Noon" bazasiga yozadi.

Ishchi 3 qatorli xabar yuboradi:
    <summa>
    <tolov vaqti>
    <№>

Masalan:
    200
    10:12
    344

Bot avtomatik qo'shadi:
    Sana        = xabar kelgan kun
    Xabar vaqti = xabar kelgan vaqt
    Status      = "Not started"
"""

import os
import re
import logging
from datetime import datetime, timezone, timedelta

import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ---------------------------------------------------------------------------
# Sozlamalar (Railway'da Environment Variables sifatida beriladi)
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATA_SOURCE_ID = os.environ.get(
    "NOTION_DATA_SOURCE_ID", "5b33d198-322c-40a3-9e4f-594dc88b3ccf"
)

# Ruxsat etilgan chat ID'lari (ixtiyoriy). Bo'sh bo'lsa — hamma yozishi mumkin.
# Masalan: ALLOWED_CHAT_IDS="-1001234567890,-1009876543210"
_allowed = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS = {int(x) for x in _allowed.split(",") if x.strip()} if _allowed else None

# Tasdiq/xato xabarlari yuboriladigan guruh (ixtiyoriy).
# Kanalning o'ziga bot javob yoza olmaydi, shuning uchun bu yerga
# alohida guruh yoki shaxsiy chat ID'sini qo'ying. Bo'sh bo'lsa — jim ishlaydi.
_log_chat = os.environ.get("LOG_CHAT_ID", "").strip()
LOG_CHAT_ID = int(_log_chat) if _log_chat else None

# O'zbekiston vaqti (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

NOTION_API = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"

# "Berilmadi" larni ro'yxatlash uchun database ID (data source emas).
# Kerak bo'lsa Railway'da NOTION_DATABASE_ID orqali o'zgartiring.
NOTION_DATABASE_ID = os.environ.get(
    "NOTION_DATABASE_ID", "f000feae-4072-46df-b120-3f98ec527b21"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("noon-bot")


# ---------------------------------------------------------------------------
# Xabarni tahlil qilish
# ---------------------------------------------------------------------------
def parse_message(text: str):
    """
    Xabar matnidan summa, to'lov vaqti va № ni ajratadi.
    Bo'sh qatorlarga chidamli. Muvaffaqiyatsiz bo'lsa (xato_matn) qaytaradi.
    Muvaffaqiyatli bo'lsa (summa, tolov_vaqti, nomer) qaytaradi.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return None, (
            "❌ Xabar 3 qatordan iborat bo'lishi kerak:\n"
            "<summa>\n<to'lov vaqti>\n<№>\n\n"
            "Masalan:\n200\n10:12\n344"
        )

    summa_raw, vaqt_raw, nomer_raw = lines[0], lines[1], lines[2]

    # Summa — faqat raqam (bo'sh joy/'so'm' ni tozalaymiz)
    summa_clean = re.sub(r"[^\d]", "", summa_raw)
    if not summa_clean:
        return None, f"❌ Summa noto'g'ri: «{summa_raw}»"
    summa = int(summa_clean)

    # To'lov vaqti — HH:MM yoki HH.MM
    vaqt_match = re.search(r"(\d{1,2})[:.](\d{2})", vaqt_raw)
    if not vaqt_match:
        return None, f"❌ To'lov vaqti noto'g'ri: «{vaqt_raw}» (masalan 10:12)"
    tolov_vaqti = f"{int(vaqt_match.group(1)):02d}:{vaqt_match.group(2)}"

    # № — faqat raqam
    nomer_clean = re.sub(r"[^\d]", "", nomer_raw)
    if not nomer_clean:
        return None, f"❌ № noto'g'ri: «{nomer_raw}»"
    nomer = nomer_clean

    return (summa, tolov_vaqti, nomer), None


# ---------------------------------------------------------------------------
# Notionga yozish
# ---------------------------------------------------------------------------
def add_to_notion(nomer: str, summa: int, tolov_vaqti: str, xabar_vaqti: str, sana: str):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"type": "data_source_id", "data_source_id": NOTION_DATA_SOURCE_ID},
        "properties": {
            "Name": {"title": [{"text": {"content": nomer}}]},
            "Summa": {"number": summa},
            "Tolov vaqti": {"rich_text": [{"text": {"content": tolov_vaqti}}]},
            "Xabar vaqti": {"rich_text": [{"text": {"content": xabar_vaqti}}]},
            "Sana": {"date": {"start": sana}},
            "Status": {"status": {"name": "Berilmadi"}},
        },
    }
    resp = requests.post(NOTION_API, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_berilmadi_list():
    """
    Barcha "Berilmadi" statusli yozuvlarni Notiondan o'qiydi.
    (№, summa) juftliklari ro'yxatini qaytaradi, № bo'yicha o'sish tartibida.
    """
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    body = {
        "filter": {"property": "Status", "status": {"equals": "Berilmadi"}},
        "page_size": 100,
    }

    items = []
    start_cursor = None
    while True:
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for row in data.get("results", []):
            props = row.get("properties", {})
            # Name (title)
            title_arr = props.get("Name", {}).get("title", [])
            nomer = title_arr[0]["plain_text"] if title_arr else "?"
            # Summa (number)
            summa = props.get("Summa", {}).get("number")
            summa = summa if summa is not None else 0
            items.append((nomer, summa))

        if data.get("has_more"):
            start_cursor = data.get("next_cursor")
        else:
            break

    # № bo'yicha raqamli tartiblash (raqam bo'lmasa oxiriga)
    def sort_key(item):
        try:
            return (0, int(item[0]))
        except ValueError:
            return (1, 0)

    items.sort(key=sort_key)
    return items


def format_berilmadi(items):
    """Berilmadi ro'yxatini Telegram uchun matn qilib formatlaydi."""
    if not items:
        return "📋 Berilmaganlar yo'q."
    lines = ["📋 Berilmaganlar:"]
    total = 0
    for nomer, summa in items:
        lines.append(f"№ {nomer} — {summa}")
        total += summa
    lines.append("")
    lines.append(f"JAMI: {total}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram handlerlar
# ---------------------------------------------------------------------------
async def notify(context, text):
    """Tasdiq/xato xabarini log guruhiga yuboradi (agar sozlangan bo'lsa)."""
    if LOG_CHAT_ID is None:
        return
    try:
        await context.bot.send_message(chat_id=LOG_CHAT_ID, text=text)
    except Exception:
        logger.exception("Log guruhiga yuborishda xato")


async def reply_or_notify(context, msg, text):
    """
    Avval xabarning o'ziga izoh (reply) qilib tasdiq beradi.
    Kanalda bot admin bo'lsa, bu post ostida ko'rinadi.
    Agar reply imkoni bo'lmasa, log guruhiga yuboradi.
    """
    try:
        await msg.reply_text(text)
    except Exception:
        logger.info("Reply ishlamadi, log guruhiga yuborilyapti")
        await notify(context, text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kanal posti channel_post sifatida keladi, oddiy chat message sifatida
    msg = update.message or update.channel_post
    if msg is None:
        return

    # Rasm bilan kelgan xabarda matn caption ichida bo'ladi
    text = msg.text or msg.caption
    if not text:
        return

    # Faqat ruxsat etilgan chatlar (agar belgilangan bo'lsa)
    if ALLOWED_CHAT_IDS is not None and msg.chat_id not in ALLOWED_CHAT_IDS:
        logger.info("Ruxsatsiz chat: %s", msg.chat_id)
        return

    parsed, error = parse_message(text)
    if error:
        # Kanaldagi postga izoh (reply) qilib xatoni ko'rsatadi
        await reply_or_notify(context, msg, f"⚠️ № aniqlanmadi.\n{error}")
        return

    summa, tolov_vaqti, nomer = parsed

    # Sana va xabar vaqti — Toshkent vaqti bo'yicha
    now = datetime.now(TASHKENT_TZ)
    sana = now.strftime("%Y-%m-%d")
    xabar_vaqti = now.strftime("%H:%M")

    try:
        add_to_notion(nomer, summa, tolov_vaqti, xabar_vaqti, sana)
    except Exception as e:
        logger.exception("Notion xatosi")
        await reply_or_notify(context, msg, f"❌ № {nomer} — Notionga yozilmadi:\n{e}")
        return

    logger.info("Qo'shildi: № %s, summa %s", nomer, summa)

    # Berilmadi ro'yxatini o'qib, tasdiqqa qo'shamiz
    try:
        berilmadi = get_berilmadi_list()
        royxat = format_berilmadi(berilmadi)
    except Exception:
        logger.exception("Berilmadi ro'yxatini o'qishda xato")
        royxat = "(ro'yxatni o'qib bo'lmadi)"

    await reply_or_notify(
        context,
        msg,
        f"✅ № {nomer} qo'shildi\n\n{royxat}",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men Noon to'lov botiman.\n\n"
        "To'lovni qo'shish uchun 3 qatorli xabar yuboring:\n"
        "<summa>\n<to'lov vaqti>\n<№>\n\n"
        "Masalan:\n200\n10:12\n344"
    )


async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chat ID'ni bilish uchun yordamchi buyruq."""
    msg = update.message or update.channel_post
    if msg is None:
        return
    logger.info("Chat ID so'raldi: %s", msg.chat_id)
    # Guruhda javob yozadi; kanalda log guruhiga yuboradi
    try:
        await msg.reply_text(f"Chat ID: {msg.chat_id}")
    except Exception:
        await notify(context, f"Chat ID: {msg.chat_id}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chatid", chatid))
    # Matnli xabarlar VA rasm/hujjat bilan kelgan (caption'li) xabarlar.
    # filters.CAPTION — rasm tagida yozilgan matnni ham qamrab oladi.
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            handle_message,
        )
    )
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
