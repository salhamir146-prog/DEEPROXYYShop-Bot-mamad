import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask
from threading import Thread

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ========== تنظیمات اولیه ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# اطلاعات ربات
TOKEN = "8936476742:AAFsqNnErOQVbyvZ_OMSuMrfZdq_osOa2sw"
ADMIN_IDS = [8706836237, 8911508795]

# اطلاعات فروشنده
CARD_NUMBER = "6219861950901305"
CARD_HOLDER = "محمد مهدی جاودان"
PRICE = 300000

# فایل ذخیره‌سازی
DATA_FILE = "data.json"

# دستور مخفی ادمین
SECRET_ADMIN_COMMAND = "HUIOTguuuuuuuuuuufg9dpgppmamaddd1212"

# ========== Keep Alive برای Render ==========
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "ربات فروش اپل آیدی در حال اجراست! ✅"

def run_flask():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ========== مدیریت داده‌ها ==========
class BotData:
    def __init__(self):
        self.accounts: List[str] = []
        self.pending_orders: Dict[int, dict] = {}
        self.load_data()
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accounts = data.get('accounts', [])
                    self.pending_orders = {
                        int(k): v for k, v in data.get('pending_orders', {}).items()
                    }
            except Exception as e:
                logger.error(f"خطا در بارگذاری داده‌ها: {e}")
                self.accounts = []
                self.pending_orders = {}
        else:
            self.accounts = []
            self.pending_orders = {}
            self.save_data()
    
    def save_data(self):
        try:
            data = {
                'accounts': self.accounts,
                'pending_orders': {str(k): v for k, v in self.pending_orders.items()}
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره داده‌ها: {e}")
            return False
    
    def add_account(self, email: str, password: str) -> bool:
        account = f"{email}:{password}"
        if account not in self.accounts:
            self.accounts.append(account)
            self.save_data()
            return True
        return False
    
    def get_next_account(self) -> Optional[str]:
        if self.accounts:
            account = self.accounts.pop(0)
            self.save_data()
            return account
        return None
    
    def get_accounts_count(self) -> int:
        return len(self.accounts)
    
    def add_pending_order(self, user_id: int, user_info: dict):
        self.pending_orders[user_id] = user_info
        self.save_data()
    
    def remove_pending_order(self, user_id: int):
        if user_id in self.pending_orders:
            del self.pending_orders[user_id]
            self.save_data()
    
    def get_pending_order(self, user_id: int) -> Optional[dict]:
        return self.pending_orders.get(user_id)

bot_data = BotData()

# ========== توابع کمکی ==========
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_price(price: int) -> str:
    return f"{price:,}".replace(',', '،')

def create_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛒 خرید اکانت", callback_data="buy"),
            InlineKeyboardButton("💳 اطلاعات پرداخت", callback_data="payment_info")
        ],
        [
            InlineKeyboardButton("📊 موجودی", callback_data="inventory")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_admin_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 موجودی اکانت‌ها", callback_data="admin_inventory"),
            InlineKeyboardButton("➕ افزودن اکانت", callback_data="admin_add_account")
        ],
        [
            InlineKeyboardButton("📋 سفارشات در انتظار", callback_data="admin_pending_orders")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منوی کاربری", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_pending_order_keyboard(user_id: int):
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید سفارش", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== هندلرهای دستورات ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"""
سلام {user.first_name} عزیز! 👋

به ربات فروش اپل آیدی خوش آمدید.

💰 قیمت هر اکانت: {format_price(PRICE)} تومان
📱 اکانت‌های معتبر و فعال

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=create_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 راهنمای استفاده از ربات:

🛒 خرید اکانت:
- روی دکمه "خرید اکانت" کلیک کنید
- اطلاعات پرداخت به شما نمایش داده می‌شود
- تصویر رسید را ارسال کنید

💳 اطلاعات پرداخت:
- شماره کارت و اطلاعات واریز را مشاهده کنید

📊 موجودی:
- تعداد اکانت‌های موجود را مشاهده کنید
"""
    await update.message.reply_text(help_text)

async def secret_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.delete()
        return
    
    await update.message.delete()
    
    panel_text = """
🔐 **پنل مدیریت مخفی**

سلام ادمین عزیز! 👋

از این پنل می‌توانید:
• موجودی اکانت‌ها را مشاهده کنید
• اکانت جدید اضافه کنید
• سفارشات در انتظار را مدیریت کنید
"""
    await update.message.reply_text(
        panel_text,
        reply_markup=create_admin_keyboard(),
        parse_mode='Markdown'
    )

# ========== هندلرهای دکمه‌ها ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "payment_info":
        payment_text = f"""
💳 **اطلاعات پرداخت**

شماره کارت:
`{CARD_NUMBER}`

نام صاحب حساب:
{CARD_HOLDER}

مبلغ قابل پرداخت:
{format_price(PRICE)} تومان

📌 **نکات مهم:**
1. مبلغ دقیق {format_price(PRICE)} تومان را واریز کنید
2. پس از واریز، تصویر رسید را ارسال کنید
3. اکانت پس از تایید ادمین ارسال می‌شود
"""
        await query.edit_message_text(
            payment_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ])
        )
    
    elif data == "buy":
        if bot_data.get_accounts_count() == 0:
            await query.edit_message_text(
                "😞 متاسفانه در حال حاضر اکانتی موجود نیست.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
                ])
            )
            return
        
        buy_text = f"""
🛒 **خرید اکانت اپل آیدی**

💰 قیمت: {format_price(PRICE)} تومان

📌 مراحل خرید:
1. مبلغ {format_price(PRICE)} تومان را به شماره کارت زیر واریز کنید:
`{CARD_NUMBER}`

2. تصویر رسید را برای ربات ارسال کنید

3. پس از تایید ادمین، اکانت برای شما ارسال می‌شود

✅ لطفاً پس از واریز، تصویر رسید را ارسال کنید.
"""
        await query.edit_message_text(
            buy_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 مشاهده اطلاعات پرداخت", callback_data="payment_info")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ])
        )
        context.user_data['waiting_for_receipt'] = True
    
    elif data == "inventory":
        count = bot_data.get_accounts_count()
        inventory_text = f"""
📊 **موجودی اکانت‌ها**

تعداد اکانت‌های موجود: {count} عدد

💰 قیمت هر اکانت: {format_price(PRICE)} تومان
"""
        await query.edit_message_text(
            inventory_text,
            parse_mode='Markdown',
            reply_markup=create_main_keyboard()
        )
    
    elif data == "admin_inventory":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        count = bot_data.get_accounts_count()
        pending_count = len(bot_data.pending_orders)
        
        inventory_text = f"""
📊 **مدیریت موجودی**

تعداد اکانت‌های موجود: {count} عدد
سفارشات در انتظار: {pending_count} عدد

💰 قیمت هر اکانت: {format_price(PRICE)} تومان
"""
        await query.edit_message_text(
            inventory_text,
            reply_markup=create_admin_keyboard()
        )
    
    elif data == "admin_add_account":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        await query.edit_message_text(
            "➕ **افزودن اکانت جدید**\n\n"
            "لطفاً اکانت را به فرمت زیر ارسال کنید:\n"
            "`email:password`\n\n"
            "مثال: `example@gmail.com:password123`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]
            ])
        )
        context.user_data['adding_account'] = True
    
    elif data == "admin_pending_orders":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        if not bot_data.pending_orders:
            await query.edit_message_text(
                "📋 هیچ سفارش در انتظاری وجود ندارد.",
                reply_markup=create_admin_keyboard()
            )
            return
        
        text = "📋 **سفارشات در انتظار تایید:**\n\n"
        for uid, info in bot_data.pending_orders.items():
            text += f"👤 کاربر: {info.get('name', 'ناشناس')}\n"
            text += f"🆔 آیدی: `{uid}`\n"
            text += f"💰 مبلغ: {format_price(PRICE)} تومان\n"
            text += f"📅 تاریخ: {info.get('date', 'نامشخص')}\n"
            text += f"-------------------\n"
        
        first_user_id = list(bot_data.pending_orders.keys())[0]
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=create_pending_order_keyboard(first_user_id)
        )
    
    elif data.startswith("confirm_"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        target_user_id = int(data.split("_")[1])
        order_info = bot_data.get_pending_order(target_user_id)
        
        if not order_info:
            await query.edit_message_text("❌ این سفارش دیگر موجود نیست!")
            return
        
        account = bot_data.get_next_account()
        if not account:
            await query.edit_message_text(
                "❌ متاسفانه اکانتی برای ارسال وجود ندارد!",
                reply_markup=create_admin_keyboard()
            )
            return
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"""
✅ **اکانت شما آماده است!**

🔑 اطلاعات اکانت:
`{account}`

📌 نکات مهم:
• از این اکانت فقط یکبار می‌توانید استفاده کنید
• پس از استفاده، اکانت قابل بازگشت نیست
• در صورت مشکل با ادمین تماس بگیرید

موفق باشید! 🍀
""",
                parse_mode='Markdown'
            )
            
            bot_data.remove_pending_order(target_user_id)
            
            await query.edit_message_text(
                f"✅ سفارش کاربر با آیدی {target_user_id} تایید شد!\nاکانت ارسال شد.",
                reply_markup=create_admin_keyboard()
            )
            
        except Exception as e:
            logger.error(f"خطا در ارسال اکانت: {e}")
            await query.edit_message_text(
                f"❌ خطا در ارسال اکانت!",
                reply_markup=create_admin_keyboard()
            )
    
    elif data.startswith("reject_"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        target_user_id = int(data.split("_")[1])
        order_info = bot_data.get_pending_order(target_user_id)
        
        if not order_info:
            await query.edit_message_text("❌ این سفارش دیگر موجود نیست!")
            return
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="""
❌ متاسفانه سفارش شما رد شد.

دلایل احتمالی:
• رسید نامعتبر یا ناخوانا
• مبلغ واریز شده اشتباه است

لطفاً مجدداً اقدام کنید.
"""
            )
            
            bot_data.remove_pending_order(target_user_id)
            
            await query.edit_message_text(
                f"❌ سفارش کاربر با آیدی {target_user_id} رد شد!",
                reply_markup=create_admin_keyboard()
            )
            
        except Exception as e:
            logger.error(f"خطا در ارسال پیام رد: {e}")
            await query.edit_message_text(
                f"❌ خطا در ارسال پیام رد!",
                reply_markup=create_admin_keyboard()
            )
    
    elif data == "back_to_main":
        await query.edit_message_text(
            "🔙 به منوی اصلی بازگشتید.",
            reply_markup=create_main_keyboard()
        )
    
    elif data == "admin_panel":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        await query.edit_message_text(
            "🔐 **پنل مدیریت مخفی**",
            parse_mode='Markdown',
            reply_markup=create_admin_keyboard()
        )

# ========== هندلر پیام‌ها ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message
    
    if context.user_data.get('adding_account') and is_admin(user_id):
        text = message.text.strip()
        if ':' in text:
            parts = text.split(':', 1)
            email = parts[0].strip()
            password = parts[1].strip()
            
            if bot_data.add_account(email, password):
                await message.reply_text(
                    f"✅ اکانت با موفقیت اضافه شد!\n"
                    f"📧 ایمیل: {email}\n"
                    f"تعداد اکانت‌های موجود: {bot_data.get_accounts_count()}",
                    reply_markup=create_admin_keyboard()
                )
                context.user_data['adding_account'] = False
            else:
                await message.reply_text(
                    "❌ این اکانت قبلاً موجود است!",
                    reply_markup=create_admin_keyboard()
                )
        else:
            await message.reply_text(
                "❌ فرمت اشتباه! به فرمت `email:password` ارسال کنید.",
                parse_mode='Markdown'
            )
        return
    
    if context.user_data.get('waiting_for_receipt'):
        if message.photo:
            photo = message.photo[-1]
            file_id = photo.file_id
            
            user_info = {
                'user_id': user_id,
                'name': message.from_user.full_name,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'photo_id': file_id
            }
            
            bot_data.add_pending_order(user_id, user_info)
            
            for admin_id in ADMIN_IDS:
                try:
                    caption = f"""
📨 **رسید جدید برای تایید**

👤 کاربر: {message.from_user.full_name}
🆔 آیدی: `{user_id}`
💰 مبلغ: {format_price(PRICE)} تومان
📅 تاریخ: {user_info['date']}
"""
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=file_id,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=create_pending_order_keyboard(user_id)
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال رسید به ادمین: {e}")
            
            await message.reply_text(
                "✅ رسید شما دریافت شد!\n⏳ در حال بررسی توسط ادمین...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]
                ])
            )
            
            context.user_data['waiting_for_receipt'] = False
            
        else:
            await message.reply_text(
                "❌ لطفاً تصویر رسید را ارسال کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="back_to_main")]
                ])
            )
        return
    
    await message.reply_text(
        "لطفاً از دکمه‌های زیر استفاده کنید:",
        reply_markup=create_main_keyboard()
    )

# ========== تابع اصلی ==========
async def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(SECRET_ADMIN_COMMAND, secret_admin_panel))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("ربات شروع به کار کرد...")
    logger.info(f"دستور مخفی ادمین: /{SECRET_ADMIN_COMMAND}")
    await application.run_polling()

if __name__ == '__main__':
    keep_alive()  # برای روشن موندن در Render
    asyncio.run(main())
