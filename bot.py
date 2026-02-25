import os
import logging
import requests
import xml.etree.ElementTree as ET
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# منابع RSS گسترده فارسی و انگلیسی
SOURCES = {
    'ai': 'https://www.zoomit.ir/ai/rss/',
    'tech': 'https://www.digiato.com/feed',
    'sport': 'https://www.varzesh3.com/rss/all',
    'economy': 'https://www.donya-e-eqtesad.com/fa/tiny/news-1/rss',
    'cinema': 'https://www.zoomg.ir/cinema/rss/',
    'health': 'https://www.isna.ir/rss/tp/21',
    'global_tech': 'https://www.theverge.com/rss/index.xml',
    'global_science': 'https://www.sciencedaily.com/rss/top/science.xml'
}

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🤖 هوش مصنوعی", callback_data='get_ai'), InlineKeyboardButton("💻 تکنولوژی", callback_data='get_tech')],
        [InlineKeyboardButton("⚽ ورزش ۳", callback_data='get_sport'), InlineKeyboardButton("📈 اقتصاد", callback_data='get_economy')],
        [InlineKeyboardButton("🎬 سینما/گیم", callback_data='get_cinema'), InlineKeyboardButton("🏥 پزشکی", callback_data='get_health')],
        [InlineKeyboardButton("🌐 Tech (EN)", callback_data='get_global_tech'), InlineKeyboardButton("🔬 Science (EN)", callback_data='get_global_science')],
        [InlineKeyboardButton("⏰ تنظیم ارسال خودکار (تایمر)", callback_data='setup_auto')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **به مرکز خبر پیشرفته خوش آمدید**\n\nیک دسته را انتخاب کنید تا ۱۰ خبر آخر را دریافت کنید یا تایمر را فعال کنید:", 
                                   reply_markup=main_menu(), parse_mode='Markdown')

async def send_10_news(message_obj, url):
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:10] # دریافت ۱۰ خبر آخر
        
        if not items: # برخی فیدها از تگ entry استفاده می‌کنند (Atom)
            items = root.findall('{http://www.w3.org/2005/Atom}entry')[:10]

        for item in items:
            title = item.find('title').text if item.find('title') is not None else "بدون تیتر"
            link = item.find('link').text if item.find('link') is not None else item.find('{http://www.w3.org/2005/Atom}link').attrib['href']
            
            msg = f"🔴 **{title.strip()}**\n\n🔗 [ادامه مطلب]({link})"
            await message_obj.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await message_obj.reply_text("❌ خطا در لود اخبار. منبع ممکن است موقتاً در دسترس نباشد.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('get_'):
        cat = query.data.split('_')[1]
        await query.message.reply_text(f"⏳ در حال استخراج ۱۰ خبر برتر در حوزه {cat}...")
        await send_10_news(query.message, SOURCES[cat])
        
    elif query.data == 'setup_auto':
        await query.message.reply_text("⏱ **تنظیم تایمر:**\n\nبرای فعالسازی ارسال خودکار، این دستور را در چت بفرستید:\n`set 10 ai`\n\n(بجای ۱۰ عدد دقیقه و بجای ai موضوع را بنویسید)")

# مکانیزم ارسال خودکار (Job Queue)
async def auto_news_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await send_10_news(context.bot, SOURCES.get(job.data['topic'], SOURCES['tech']))

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # دستور: set 10 ai
        args = context.args
        due = float(args[0]) * 60 # تبدیل دقیقه به ثانیه
        topic = args[1]
        
        if topic not in SOURCES:
            await update.message.reply_text("❌ موضوع نامعتبر! موضوعات موجود: ai, tech, sport, economy, cinema, health")
            return

        # حذف تایمر قبلی اگر وجود داشت
        job_removed = remove_job_if_exists(str(update.effective_chat.id), context)
        
        context.job_queue.run_repeating(auto_news_job, interval=due, first=10, 
                                        chat_id=update.effective_chat.id, 
                                        name=str(update.effective_chat.id), 
                                        data={'topic': topic})

        await update.message.reply_text(f"✅ ارسال خودکار فعال شد!\nهر {args[0]} دقیقه آخرین اخبار {topic} ارسال می‌شود.")
    except (IndexError, ValueError):
        await update.message.reply_text("💡 روش استفاده: `set 10 ai` (برای ارسال هر ۱۰ دقیقه)")

def remove_job_if_exists(name, context):
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def main():
    # فعالسازی JobQueue برای تایمر
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set", set_timer)) # هندلر برای دستور تایمر
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # جستجوی جهانی با NewsAPI
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: send_10_news(u.message, f"https://newsapi.org/v2/everything?q={u.message.text}&apiKey={NEWS_API_KEY}")))

    print("Bot is up and running with Auto-Post...")
    app.run_polling()

if __name__ == '__main__':
    main()
