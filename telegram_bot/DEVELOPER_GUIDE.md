# دليل المطور - Developer Guide
## SMSPool Telegram Bot

---

## نظرة سريعة / Quick Overview

هذا دليل سريع للمطورين للعمل على بوت SMSPool. يحتوي على جميع المعلومات الضرورية للبدء.

This is a quick guide for developers working on the SMSPool bot. It contains all necessary information to get started.

---

## بنية المشروع / Project Structure

```
telegram_bot/
├── bot.py                          # البوت الرئيسي / Main bot
├── smspool_service.py              # وحدة SMSPool / SMSPool module
├── config.py                       # الإعدادات / Configuration
├── bot_utils.py                    # أدوات مساعدة / Helper utilities
├── bot_keyboards.py                # لوحات المفاتيح / Keyboards
├── bot_admin.py                    # لوحة الآدمن / Admin panel
├── bot_customer.py                 # وظائف العملاء / Customer functions
├── start_all.sh                    # سكريبت التشغيل / Start script
├── stop_all.sh                     # سكريبت الإيقاف / Stop script
├── requirements.txt                # المكتبات الأساسية / Basic packages
├── requirementsfull.txt            # جميع المكتبات / All packages
├── proxy_bot.db                    # قاعدة البيانات / Database
├── logs/                           # السجلات / Logs
│   ├── bot.log
│   ├── web.log
│   ├── bot.pid
│   └── web.pid
├── web_ui/                         # واجهة الويب / Web UI
└── static/                         # الملفات الثابتة / Static files
```

---

## التثبيت السريع / Quick Installation

```bash
# Clone or extract the project
cd /path/to/telegram_bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirementsfull.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Start the bot
./start_all.sh
```

---

## المتغيرات البيئية / Environment Variables

```bash
# Required
TOKEN=your_telegram_bot_token
SMSPOOL_API_KEY=your_smspool_api_key

# Optional
DATABASE_FILE=proxy_bot.db
PORT=5000
ADMIN_PASSWORD=your_admin_password
TIMEZONE=Asia/Damascus
```

---

## الأكواد الهامة / Important Code Sections

### 1. تهيئة SMSPool API / SMSPool API Initialization
**الملف:** `smspool_service.py` (Lines 148-164)

```python
class SMSPoolAPI:
    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.api_key = api_key
        elif CONFIG_AVAILABLE and hasattr(Config, 'SMSPOOL_API_KEY'):
            self.api_key = Config.SMSPOOL_API_KEY
        else:
            self.api_key = os.getenv("SMSPOOL_API_KEY")
```

**الاستخدام:**
```python
api = SMSPoolAPI(api_key="your_key")
# أو
api = SMSPoolAPI()  # يقرأ من المتغيرات البيئية
```

---

### 2. البحث عن الدول / Country Search
**الملف:** `smspool_service.py` (Lines 2744-2935)

```python
async def handle_smspool_inline_query(update: Update, context):
    query_text = update.inline_query.query.strip()
    
    if query_text.startswith("sp:"):
        # البحث عن دول
        query_text = query_text[3:].strip()
        countries = api.get_countries()
        # ... معالجة النتائج
```

**الاستخدام:**
- المستخدم يكتب: `sp:united`
- النتيجة: جميع الدول التي تحتوي "united"

---

### 3. البحث عن الخدمات / Service Search
**الملف:** `smspool_service.py` (Lines 2756-2815)

```python
if query_text.startswith("sp_svc:"):
    parts = query_text.split(":")
    country_id = parts[1]
    service_query = parts[2]
    
    services = api.get_services()
    matching = [s for s in services 
                if service_query in s.get('name', '').lower()]
```

**الاستخدام:**
- المستخدم يكتب: `sp_svc:123:whatsapp`
- النتيجة: جميع خدمات WhatsApp في الدولة 123

---

### 4. معالجة الشراء / Purchase Processing
**الملف:** `smspool_service.py` (Lines 1737-1887)

```python
async def process_purchase(update: Update, context,
                          country_id: str, service_id: str):
    # 1. التحقق من الرصيد
    balance = get_user_balance(user_id)
    if balance < sale_price:
        # رفض الشراء
        return
    
    # 2. الشراء من API
    result = api.purchase_sms(country_id, service_id)
    
    # 3. خصم الرصيد
    update_user_balance(user_id, sale_price, 'subtract')
    
    # 4. حفظ في قاعدة البيانات
    smspool_db.create_order(...)
    
    # 5. بدء المراقبة
    context.job_queue.run_repeating(check_sms_job, ...)
```

---

### 5. المراقبة التلقائية / Auto Monitoring
**الملف:** `smspool_service.py` (Lines 1863-1873)

```python
# بدء المراقبة
context.job_queue.run_repeating(
    check_sms_job,
    interval=10,        # كل 10 ثواني
    first=5,            # أول فحص بعد 5 ثواني
    data={
        'order_id': order_id,
        'user_id': user_id,
        'chat_id': chat_id
    },
    name=f"sms_check_{order_id}"
)
```

---

## قاعدة البيانات / Database

### الجداول الرئيسية / Main Tables

#### 1. smspool_orders
```sql
CREATE TABLE IF NOT EXISTS smspool_orders (
    user_id INTEGER NOT NULL,
    order_id TEXT PRIMARY KEY,
    number TEXT NOT NULL,
    country TEXT NOT NULL,
    country_id TEXT,
    service TEXT NOT NULL,
    service_id TEXT,
    pool TEXT,
    cost_price REAL NOT NULL,
    sale_price REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    sms_code TEXT,
    full_sms TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

**الأعمدة:**
- `user_id`: معرف المستخدم
- `order_id`: معرف الطلب من SMSPool
- `number`: رقم الهاتف
- `status`: pending, active, completed, cancelled, expired
- `sms_code`: كود التحقق المستخرج
- `full_sms`: الرسالة الكاملة

#### 2. smspool_settings
```sql
CREATE TABLE IF NOT EXISTS smspool_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT,
    margin_percent REAL DEFAULT 0,
    enabled INTEGER DEFAULT 1
);
```

---

## API الداخلية / Internal API

### SMSPoolDB Class

#### 1. إنشاء طلب / Create Order
```python
smspool_db.create_order(
    user_id=123,
    order_id="abc123",
    number="+1234567890",
    country="United States",
    country_id="1",
    service="WhatsApp",
    service_id="10",
    pool="",
    cost_price=0.50,
    sale_price=0.60,
    expires_in=600
)
```

#### 2. الحصول على طلبات المستخدم / Get User Orders
```python
orders = smspool_db.get_user_orders(user_id=123)
for order in orders:
    print(f"Order {order['order_id']}: {order['status']}")
```

#### 3. تحديث حالة الطلب / Update Order Status
```python
smspool_db.update_order_status(
    order_id="abc123",
    status="completed",
    sms_code="123456",
    full_sms="Your verification code is 123456"
)
```

#### 4. الحصول على/تعيين الإعدادات / Get/Set Settings
```python
# الحصول على API Key
api_key = smspool_db.get_api_key()

# تعيين API Key
smspool_db.set_api_key("new_key")

# الحصول على الهامش
margin = smspool_db.get_margin_percent()

# تعيين الهامش
smspool_db.set_margin_percent(20.0)

# تفعيل/تعطيل
smspool_db.set_enabled(True)
enabled = smspool_db.is_enabled()
```

---

## نظام الترجمة / Translation System

### إضافة رسالة جديدة / Add New Message

**الملف:** `smspool_service.py` (Lines 982-1065)

```python
SMSPOOL_MESSAGES = {
    'ar': {
        'new_message': 'النص بالعربية',
        # ... رسائل أخرى
    },
    'en': {
        'new_message': 'Text in English',
        # ... other messages
    }
}
```

**الاستخدام:**
```python
language = get_user_language(user_id)
text = get_smspool_message('new_message', language)
```

---

## معالجة الأخطاء / Error Handling

### أكواد الأخطاء / Error Codes

```python
ERROR_CODES = {
    '0x0000': 'رصيد الحساب غير كافٍ',
    '0x0001': 'الخدمة غير متوفرة حالياً',
    '0x0002': 'خطأ في الاتصال بالموقع',
    '0x0003': 'تم رفض الطلب',
    '0x0004': 'انتهت مهلة الاتصال',
    '0x0005': 'مفتاح API غير صحيح',
    '0x0006': 'تم تجاوز حد الطلبات',
    '0x0007': 'الطلب غير موجود',
    '0x0008': 'فشل في جلب الرسالة',
    '0x0009': 'خطأ غير متوقع',
    '0x000A': 'الخدمة غير متاحة'
}
```

### استخدام أكواد الأخطاء
```python
try:
    result = api.purchase_sms(country_id, service_id)
except Exception as e:
    error_code = get_error_code_from_message(str(e))
    error_msg = ERROR_CODES.get(error_code, str(e))
    await update.message.reply_text(error_msg)
```

---

## نظام Cache / Cache System

### إعدادات Cache
```python
CACHE = {
    'services': {'data': [], 'last_update': 0},
    'countries': {'data': [], 'last_update': 0},
    'prices': {'data': {}, 'last_update': 0},
    'cache_duration': 300  # 5 دقائق
}
```

### استخدام Cache
```python
def get_services() -> List[Dict]:
    now = time.time()
    cache_duration = CACHE['cache_duration']
    services_cache = CACHE['services']
    
    # إذا كان Cache صالحاً
    if (now - services_cache['last_update'] < cache_duration) \
       and services_cache['data']:
        return services_cache['data']
    
    # جلب من API
    result = self._api_request("service/retrieve_all", method="GET")
    
    # تحديث Cache
    services_cache['data'] = result
    services_cache['last_update'] = now
    
    return result
```

---

## Callbacks Reference

### Callback Data Patterns

```python
# القائمة الرئيسية
"sp_main"           # العودة للقائمة الرئيسية
"sp_menu"           # فتح القائمة

# الشراء
"sp_buy"            # بدء عملية الشراء
"sp_type_temp"      # اختيار رقم مؤقت
"sp_type_rent"      # اختيار إيجار

# الإيجار
"sp_rent_dur_1"     # إيجار ليوم واحد
"sp_rent_dur_3"     # إيجار لثلاثة أيام
"sp_rent_dur_7"     # إيجار لأسبوع
"sp_rent_dur_30"    # إيجار لشهر

# الدول والخدمات
"sp_country_123"    # اختيار دولة (123 = country_id)
"sp_service_select_456"  # اختيار خدمة (456 = service_id)
"sp_buy_123_456"    # شراء (country_id_service_id)

# التأكيد
"sp_confirm_123_456"  # تأكيد الشراء

# إدارة الطلبات
"sp_my_numbers"     # عرض الأرقام النشطة
"sp_history"        # عرض السجل
"sp_check_abc"      # فحص الطلب (abc = order_id)
"sp_cancel_abc"     # إلغاء الطلب
"sp_resend_abc"     # إعادة إرسال
"sp_renew_abc"      # تجديد الطلب

# التنقل
"sp_my_numbers_page_2"   # صفحة 2 من الأرقام
"sp_history_page_3"      # صفحة 3 من السجل
```

---

## Inline Query Patterns

### أنماط البحث / Search Patterns

```python
# البحث عن دول
"sp:"              # عرض الدول الشائعة
"sp:us"            # البحث عن الولايات المتحدة
"sp:united"        # البحث عن United States/Kingdom
"sp:france"        # البحث عن فرنسا

# البحث عن خدمات في دولة معينة
"sp_svc:123:"              # عرض الخدمات الشائعة
"sp_svc:123:whatsapp"      # البحث عن WhatsApp
"sp_svc:123:telegram"      # البحث عن Telegram
"sp_svc:123:google"        # البحث عن Google
```

---

## Logging

### إعداد Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# مثال على الاستخدام
logger.info(f"✅ SMSPool API connection OK. Balance={balance}")
logger.error(f"❌ SMSPool API connection failed: {message}")
logger.warning(f"⚠️ job_queue غير متاح")
```

### مستويات Logging
- `logger.debug()`: معلومات التصحيح
- `logger.info()`: معلومات عامة
- `logger.warning()`: تحذيرات
- `logger.error()`: أخطاء
- `logger.critical()`: أخطاء حرجة

---

## الأوامر الشائعة / Common Commands

### تشغيل وإيقاف / Start & Stop
```bash
# تشغيل
./start_all.sh

# إيقاف
./stop_all.sh

# إعادة التشغيل
./stop_all.sh && ./start_all.sh
```

### مراقبة السجلات / Monitor Logs
```bash
# السجل الرئيسي
tail -f logs/bot.log

# البحث عن أخطاء
grep "ERROR" logs/bot.log

# آخر 100 سطر
tail -n 100 logs/bot.log
```

### قاعدة البيانات / Database
```bash
# فتح قاعدة البيانات
sqlite3 proxy_bot.db

# عرض الجداول
.tables

# عرض بنية جدول
.schema smspool_orders

# استعلام
SELECT * FROM smspool_orders WHERE user_id = 123;

# خروج
.quit
```

---

## نصائح التطوير / Development Tips

### 1. التصحيح / Debugging
```python
# إضافة نقاط توقف
import pdb; pdb.set_trace()

# طباعة متغيرات
print(f"Debug: variable = {variable}")

# استخدام logger
logger.debug(f"Context data: {context.user_data}")
```

### 2. الاختبار / Testing
```python
# اختبار API
api = SMSPoolAPI(api_key="test_key")
success, message, balance = api.test_connection()
print(f"Status: {success}, Message: {message}, Balance: {balance}")

# اختبار قاعدة البيانات
orders = smspool_db.get_user_orders(user_id=123)
print(f"Found {len(orders)} orders")
```

### 3. الأداء / Performance
```python
# قياس الوقت
import time
start = time.time()
# ... code ...
elapsed = time.time() - start
logger.info(f"Operation took {elapsed:.2f} seconds")

# التحقق من Cache
if CACHE['services']['data']:
    logger.info("Using cached services")
else:
    logger.info("Fetching services from API")
```

---

## الأمان / Security

### Best Practices
1. ✅ لا تقم بتسجيل API Keys في السجلات
2. ✅ استخدم متغيرات البيئة للإعدادات الحساسة
3. ✅ تحقق من صلاحيات المستخدم قبل العمليات
4. ✅ قم بتنظيف المدخلات من المستخدمين
5. ✅ استخدم HTTPS فقط للاتصالات
6. ✅ احفظ نسخ احتياطية من قاعدة البيانات

```python
# مثال: تنظيف المدخلات
import re

def sanitize_input(text: str) -> str:
    # إزالة الأحرف الخاصة
    return re.sub(r'[^\w\s-]', '', text)

# مثال: التحقق من الصلاحيات
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
```

---

## استكشاف الأخطاء / Troubleshooting

### مشكلة: البوت لا يستجيب
```bash
# تحقق من العمليات
ps aux | grep bot.py

# تحقق من السجلات
tail -f logs/bot.log

# أعد التشغيل
./stop_all.sh && ./start_all.sh
```

### مشكلة: خطأ في قاعدة البيانات
```bash
# تحقق من وجود الملف
ls -la proxy_bot.db

# تحقق من الأذونات
chmod 664 proxy_bot.db

# افتح القاعدة للفحص
sqlite3 proxy_bot.db
```

### مشكلة: API لا يعمل
```python
# اختبار الاتصال
api = SMSPoolAPI()
success, msg, balance = api.test_connection()
print(f"API Status: {success}, {msg}, Balance: {balance}")

# تحقق من API Key
import os
print(f"API Key: {os.getenv('SMSPOOL_API_KEY')[:10]}...")
```

---

## الموارد / Resources

### الوثائق / Documentation
- [SMSPool API Docs](https://www.smspool.net/article/how-to-use-the-smspool-api)
- [python-telegram-bot Docs](https://docs.python-telegram-bot.org/)
- [SQLite Docs](https://www.sqlite.org/docs.html)

### الملفات المرجعية / Reference Files
- `SMSPOOL_IMPROVEMENTS.md` - دليل الميزات الكامل
- `TESTING_GUIDE.md` - دليل الاختبار الشامل
- `CHANGES_SUMMARY.md` - ملخص التغييرات

---

## جهات الاتصال / Contact

**المطور:** AI Assistant
**التاريخ:** February 3, 2026
**الإصدار:** 2.0

---

**نهاية الدليل / End of Guide**
