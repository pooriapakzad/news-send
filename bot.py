import os
import logging
import requests
import xml.etree.ElementTree as ET
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# دیکشنری زبان (برای مدیریت متون ربات)
STRINGS = {
    'fa': {
        'welcome': "✨ **به سوپر ربات خبری خوش آمدید** ✨\n\nزبان فعلی: فارسی 🇮🇷",
        'lang_btn': "🇺🇸 Switch to English",
        'ai': "🤖 هوش مصنوعی", 'tech': "💻 تکنولوژی", 'sport': "⚽ ورزش", 'economy': "📈 اقتصاد",
        'health': "🏥 پزشکی و سلامت", 'cinema': "🎬 سینما و گیم", 'style': "👓 مد و فشن",
        'prices': "💰 نرخ ارز و طلا", 'random': "🎲 خبر تصادفی", 'search': "🔍 جستجوی پیشرفته",
        'timer': "⏰ تنظیم تایمر", 'support': "☎️ پشتیبانی", 'loading': "⏳ در حال استخراج اخبار...",
        'more': "🔗 ادامه مطلب"
    },
    'en': {
        'welcome': "✨ **Welcome to Super News Bot** ✨\n\nCurrent Language: English 🇺🇸",
        'lang_btn': "🇮🇷 تغییر به فارسی",
        'ai': "🤖 AI News", 'tech': "💻 Technology", 'sport': "⚽ Sports", 'economy': "📈 Economy",
        'health': "🏥 Health & Med", 'cinema': "🎬 Movie & Game", 'style': "👓 Fashion & Style",
        'prices': "💰 Market Rates", 'random': "🎲 Random News", 'search': "🔍 Advanced Search",
        'timer': "⏰ Set Timer", 'support': "☎️ Support", 'loading': "⏳ Fetching news...",
        'more': "🔗 Read More"
    }
}

# منابع خبری (ترکیبی فارسی و انگلیسی)
SOURCES = {
    'fa': {
        'ai': ['https://www.zoomit.ir/ai/rss/', 'https://digiato.com/topic/artificial-intelligence/feed'],
        'sport': ['https://www.varzesh3.com/rss/all', 'https://www.isna.ir/rss/tp/24'],
        'tech': ['https://www.digiato.com/feed', 'https://www.zoomit.ir/tech/rss/'],
        'economy': ['https://www.donya-e-eqtesad.com/fa/tiny/news-1/rss', 'https://www.isna.ir/rss/tp/25'],
        'health': ['https://www.isna.ir/rss/tp/21', 'https://www.beytoote.com/health/rss/'],
        'cinema': ['https://www.zoomg.ir/cinema/rss/', 'https://www.filimo.com/shot/feed/'],
        'style': ['https://www.thefashionista.ir/feed/']
    },
    'en': {
        'ai': ['https://machinelearningmastery.com/feed/', 'https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml'],
        'sport': ['https://www.espn.com/espn/rss/news', 'https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml'],
        'tech': ['https://www.theverge.com/rss/index.xml', 'https://www.wired.com/feed/rss'],
        'economy': ['https://www.economist.com/finance-and-economics/rss.xml', 'https://feeds.a.dj.com/rss/WSJBlogEconomy.xml'],
        'health': ['https://www.health.harvard.edu/blog/feed', 'https://rss.nytimes.com/services/xml/rss/nyt/Health.xml'],
        'cinema': ['https://www.hollywoodreporter.com/feed/', 'https://www.empireonline.com/rss/'],
        'style': ['https://www.vogue.com/feed/rss', 'https://www.gq.com/feed/rss']
    }
}

# ذخیره زبان کاربر (در حافظه موقت - برای دائمی شدن نیاز به دیتابیس است)
user_lang = {}

def get_keyboard(chat_id):
    lang = user_lang.get(chat_id, 'fa')
    s = STRINGS[lang]
    keyboard = [
        [InlineKeyboardButton(s['ai'], callback_data='get_ai'), InlineKeyboardButton(s['tech'], callback_data='get_tech')],
        [InlineKeyboardButton(s['sport'], callback_data='get_sport'), InlineKeyboardButton(s['economy'], callback_data='get_economy')],
        [InlineKeyboardButton(s['health'], callback_data='get_health'), InlineKeyboardButton(s['cinema'], callback_data='get_cinema')],
        [InlineKeyboardButton(s['style'], callback_data='get_style'), InlineKeyboardButton(s['prices'], callback_data='get_prices')],
        [InlineKeyboardButton(s['random'], callback_data='get_random'), InlineKeyboardButton(s['search'], callback_data='get_search')],
        [InlineKeyboardButton(s['timer'], callback_data='setup_auto'), InlineKeyboardButton(s['support'], callback_data='support_menu')],
        [InlineKeyboardButton(s['lang_btn'], callback_data='switch_lang')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in user_lang: user_lang[cid] = 'fa'
    await update.message.reply_text(STRINGS[user_lang[cid]]['welcome'], reply_markup=get_keyboard(cid), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cid = query.message.chat_id
    lang = user_lang.get(cid, 'fa')
    await query.answer()
    
    data = query.data
    
    if data == 'switch_lang':
        user_lang[cid] = 'en' if lang == 'fa' else 'fa'
        await query.edit_message_text(STRINGS[user_lang[cid]]['welcome'], reply_markup=get_keyboard(cid), parse_mode='Markdown')
        
    elif data.startswith('get_'):
        cat = data.split('_')[1]
        await query.message.reply_text(STRINGS[lang]['loading'])
        
        if cat == 'prices':
            await fetch_and_send(query.message, 'https://www.donya-e-eqtesad.com/fa/tiny/news-1/rss', limit=5, lang=lang)
        elif cat == 'random':
            rand_cat = random.choice(list(SOURCES[lang].keys()))
            await fetch_and_send(query.message, random.choice(SOURCES[lang][rand_cat]), limit=1, lang=lang)
        elif cat == 'search':
            await query.message.reply_text("🔍 Type your keyword to search...")
        else:
            for url in SOURCES[lang].get(cat, []):
                await fetch_and_send(query.message, url, limit=5, lang=lang)

    elif data == 'support_menu':
        kb = [[InlineKeyboardButton("📢 Channel", url="https://t.me/YourChannel"), InlineKeyboardButton("👤 Admin", url="https://t.me/YourID")]]
        await query.message.reply_text("💎 **Contact Support:**", reply_markup=InlineKeyboardMarkup(kb))

async def fetch_and_send(message_obj, url, limit=10, lang='fa'):
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.content)
        items = root.findall('.//item')[:limit]
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            btn_text = STRINGS[lang]['more']
            await message_obj.reply_text(f"🔴 **{title.strip()}**\n\n🔗 [{btn_text}]({link})", parse_mode='Markdown')
    except:
        pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # جستجوی هوشمند بر اساس زبان ربات
    lang = user_lang.get(update.effective_chat.id, 'fa')
    search_url = f"https://news.google.com/rss/search?q={query}&hl={'fa' if lang=='fa' else 'en'}&ceid={'IR:fa' if lang=='fa' else 'US:en'}"
    await update.message.reply_text(f"🔎 Searching for '{query}'...")
    await fetch_and_send(update.message, search_url, limit=5, lang=lang)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot is Running in Professional Multi-Lang Mode...")
    app.run_polling()

if __name__ == '__main__':
    main()
