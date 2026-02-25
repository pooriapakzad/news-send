import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# دریافت توکن‌ها از Environment Variables (برای امنیت در Railway)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# منوی اصلی جذاب
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🚀 تکنولوژی", callback_data='news_technology'),
            InlineKeyboardButton("⚽ ورزش", callback_data='news_sports')
        ],
        [
            InlineKeyboardButton("💰 اقتصاد", callback_data='news_business'),
            InlineKeyboardButton("🎬 سرگرمی", callback_data='news_entertainment')
        ],
        [InlineKeyboardButton("🔍 جستجوی موضوع دلخواه", callback_data='search_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"سلام {user_name} عزیز! 🌹\n"
        "به ربات خبرخوان پیشرفته خوش آمدی.\n\n"
        "یکی از دسته‌بندی‌های زیر را انتخاب کن یا موضوعی که دوست داری را برام بفرست:"
    )
    # ارسال پیام خوش‌آمدگویی همراه با دکمه‌ها
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'search_help':
        await query.edit_message_text("کافیست اسم موضوع مورد نظرت را تایپ کنی (مثلاً: پایتون یا بورس)")
        return

    # استخراج دسته‌بندی از callback_data
    category = query.data.split('_')[1]
    await query.edit_message_text(f"⏳ در حال دریافت آخرین اخبار {category}...")
    
    await fetch_and_send_news(query.message, category)

async def fetch_and_send_news(message_obj, topic):
    # فراخوانی API
    url = f'https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}&language=en&pageSize=5'
    try:
        response = requests.get(url).json()
        if response.get("status") == "ok" and response.get("articles"):
            for article in response['articles'][:3]:
                text = (
                    f"✨ *{article['title']}*\n\n"
                    f"📝 {article['description'][:200]}...\n\n"
                    f"🔗 [مشاهده کامل خبر]({article['url']})"
                )
                await message_obj.reply_text(text, parse_mode='Markdown')
        else:
            await message_obj.reply_text("❌ متاسفانه خبری پیدا نشد.")
    except Exception as e:
        await message_obj.reply_text("خطا در برقراری ارتباط با سرور اخبار.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # این بخش برای جستجوی متنی (هم در پی‌وی هم در گروه)
    query = update.message.text
    # اگر ربات در گروه است، فقط به پیام‌هایی که ریپلای شده‌اند یا کلمه خاصی دارند جواب دهد (اختیاری)
    await fetch_and_send_news(update.message, query)

def main():
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found!")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()