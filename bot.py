import os
import logging
import feedparser
import requests
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# دریافت توکن‌ها از محیط Railway
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# منابع اخبار فارسی (RSS)
RSS_SOURCES = {
    'ai': 'https://www.zoomit.ir/ai/rss/',
    'tech': 'https://www.digiato.com/feed',
    'sport': 'https://www.varzesh3.com/rss/all',
    'economy': 'https://www.donya-e-eqtesad.com/fa/tiny/news-1/rss',
}

def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🤖 هوش مصنوعی (فارسی)", callback_data='rss_ai'),
            InlineKeyboardButton("📱 تکنولوژی (فارسی)", callback_data='rss_tech')
        ],
        [
            InlineKeyboardButton("⚽ ورزش ۳", callback_data='rss_sport'),
            InlineKeyboardButton("💰 اقتصاد", callback_data='rss_economy')
        ],
        [
            InlineKeyboardButton("🌍 اخبار جهانی (English)", callback_data='global_news')
        ],
        [InlineKeyboardButton("🔍 جستجوی موضوع خاص (تایپ کنید)", callback_data='search_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        f"سلام {update.effective_user.first_name} عزیز! 📰\n\n"
        "به ربات جامع خبرخوان خوش آمدی.\n"
        "میتوانی از دسته‌بندی‌های فارسی استفاده کنی یا هر موضوعی که دوست داری را به انگلیسی یا فارسی تایپ کنی تا در کل دنیا جستجو کنم!"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('rss_'):
        category = data.split('_')[1]
        await query.message.reply_text(f"⏳ دریافت آخرین اخبار فارسی در دسته {category}...")
        await fetch_rss(query.message, RSS_SOURCES[category])
        
    elif data == 'global_news':
        await query.message.reply_text("⏳ در حال دریافت اخبار برتر جهان...")
        await fetch_global_api(query.message, "top-headlines")

    elif data == 'search_help':
        await query.message.reply_text("کافیست نام موضوع را بفرستید. مثلاً: Tesla, Bitcoin, یا جنگ...")

async def fetch_rss(message_obj, url):
    feed = feedparser.parse(url)
    for entry in feed.entries[:3]:
        text = f"🔴 *{entry.title}*\n\n🔗 [ادامه مطلب]({entry.link})"
        await message_obj.reply_text(text, parse_mode='Markdown')

async def fetch_global_api(message_obj, query):
    # استفاده از NewsAPI برای جستجوی جهانی
    url = f'https://newsapi.org/v2/everything?q={query}&apiKey={NEWS_API_KEY}&pageSize=3'
    if query == "top-headlines":
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}&pageSize=3'
        
    try:
        response = requests.get(url).json()
        if response.get("articles"):
            for art in response['articles']:
                msg = f"✨ *{art['title']}*\n\n🔹 {art['description'][:150]}...\n🔗 [Read More]({art['url']})"
                await message_obj.reply_text(msg, parse_mode='Markdown')
        else:
            await message_obj.reply_text("نتیجه‌ای در بخش جهانی پیدا نشد.")
    except:
        await message_obj.reply_text("خطا در اتصال به شبکه جهانی.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    # اگر در گروه است و پیامی فرستاده شد، جستجو انجام می‌شود
    await fetch_global_api(update.message, user_text)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot is starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
