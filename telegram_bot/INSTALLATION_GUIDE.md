# دليل تثبيت البوت على سيرفر لينوكس
# Bot Installation Guide for Linux Server

---

## تحذير أمني هام / IMPORTANT SECURITY WARNING

**هذا الملف يحتوي على معلومات حساسة! / This file contains sensitive information!**

1. **غيّر كلمة المرور فوراً بعد أول اتصال** / Change password immediately after first connection
2. **لا تشارك هذا الملف مع أي شخص** / Do not share this file with anyone
3. **احذف هذا الملف بعد التثبيت أو احفظه في مكان آمن** / Delete this file after installation or keep it in a secure location
4. **يُنصح بإنشاء مستخدم جديد بدلاً من استخدام root** / It's recommended to create a new user instead of using root

---

## معلومات السيرفر / Server Information

| المعلومة | القيمة |
|---------|--------|
| IP Address | `162.19.199.122` |
| Port | `56777` |
| Username | `root` |
| Password | `SqTv31MYbLm2fzJ566` |

---

## الخطوة 1: الاتصال بالسيرفر / Step 1: Connect to Server

```bash
ssh -p 56777 root@162.19.199.122
```

---

## الخطوة 2: تحديث النظام / Step 2: Update System

```bash
apt update && apt upgrade -y
```

---

## الخطوة 3: تثبيت المتطلبات / Step 3: Install Dependencies

```bash
apt install -y python3 python3-pip python3-venv git nodejs npm screen ufw
```

---

## الخطوة 4: إنشاء مجلد المشروع / Step 4: Create Project Directory

```bash
mkdir -p /root/telegram_bot
cd /root/telegram_bot
```

---

## الخطوة 5: نقل ملفات المشروع / Step 5: Transfer Project Files

### الطريقة 1: باستخدام SCP (من جهازك المحلي)

```bash
scp -P 56777 -r ./telegram_bot/* root@162.19.199.122:/root/telegram_bot/
```

### الطريقة 2: باستخدام Git (إذا كان المشروع على GitHub)

```bash
git clone <repository_url> /root/telegram_bot
```

---

## الخطوة 6: إعداد بيئة Python / Step 6: Setup Python Environment

```bash
cd /root/telegram_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## الخطوة 7: إعداد واجهة الويب / Step 7: Setup Web Interface

```bash
cd /root/telegram_bot/web_ui
npm install
npm run build
```

---

## الخطوة 8: إعداد BotFather / Step 8: BotFather Setup

### إنشاء بوت جديد

1. افتح تيليجرام وابحث عن **@BotFather**
2. أرسل الأمر `/newbot`
3. أدخل اسم البوت (مثال: `My Proxy Bot`)
4. أدخل username للبوت (يجب أن ينتهي بـ `bot`، مثال: `my_proxy_bot`)
5. سيرسل لك BotFather **Token** - احفظه! (مثال: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### تكوين البوت

1. في BotFather، أرسل `/mybots`
2. اختر البوت الخاص بك
3. اختر **Bot Settings**

#### إعداد زر القائمة (Menu Button)
1. اختر **Menu Button**
2. اختر **Configure menu button**
3. أدخل الرابط: `http://162.19.199.122:5000`

#### إعداد التطبيق المصغر (Mini App) - اختياري
1. من `/mybots` > اختر البوت > **Bot Settings**
2. اختر **Menu Button** أو **Bot Web App**
3. أدخل الرابط: `http://162.19.199.122:5000`

#### إعداد الوصف والصورة
1. `/setdescription` - لإضافة وصف للبوت
2. `/setabouttext` - لإضافة نص "About"
3. `/setuserpic` - لإضافة صورة للبوت

---

## الخطوة 9: تكوين الإعدادات / Step 9: Configure Settings

### إنشاء ملف config.py

```bash
nano /root/telegram_bot/config.py
```

أضف المحتوى التالي (عدّل القيم حسب احتياجاتك):

```python
# Telegram Bot Token (من BotFather)
TOKEN = "YOUR_BOT_TOKEN_HERE"

# كلمة مرور الآدمن (نفسها للبوت والواجهة)
ADMIN_PASSWORD = "sohilSOHIL"

# معرفات المسؤولين (أرقام Telegram IDs)
ADMIN_IDS = [123456789]

# قاعدة البيانات
DATABASE_FILE = "proxy_bot.db"

# رابط التطبيق المصغر
MINIAPP_URL = "http://162.19.199.122:5000"
```

### للحصول على Telegram ID الخاص بك:
1. افتح @userinfobot على تيليجرام
2. سيظهر لك الـ ID الخاص بك

---

## الخطوة 10: تشغيل البوت والواجهة / Step 10: Run Bot and Web UI

### الطريقة 1: استخدام سكريبت التشغيل الموحد

```bash
cd /root
chmod +x start_all.sh
./start_all.sh
```

### الطريقة 2: استخدام Screen (للتشغيل في الخلفية)

#### تشغيل البوت:
```bash
screen -S telegram_bot
cd /root/telegram_bot
source venv/bin/activate
python run.py
# اضغط Ctrl+A ثم D للخروج
```

#### تشغيل واجهة الويب:
```bash
screen -S web_ui
cd /root/telegram_bot/web_ui
ADMIN_PASSWORD="sohilSOHIL" npm run dev
# اضغط Ctrl+A ثم D للخروج
```

---

## الوصول لواجهة الويب / Accessing Web Interface

### عبر المتصفح

افتح الرابط التالي في متصفحك:

```
http://162.19.199.122:5000
```

### بيانات تسجيل الدخول

| البيانات | القيمة |
|----------|--------|
| كلمة المرور | `sohilSOHIL` |

**ملاحظة:** كلمة المرور هذه نفسها المستخدمة في البوت للوصول للوحة الآدمن.

### تغيير كلمة المرور

لتغيير كلمة المرور، عدّل قيمة `ADMIN_PASSWORD` في:
1. ملف `config.py` (للبوت)
2. متغير البيئة `ADMIN_PASSWORD` عند تشغيل الواجهة

---

## فتح البورتات في جدار الحماية / Firewall Configuration

```bash
# تفعيل جدار الحماية
ufw enable

# فتح البورتات المطلوبة
ufw allow 56777/tcp   # SSH
ufw allow 5000/tcp    # واجهة الويب

# إعادة تحميل الإعدادات
ufw reload

# التحقق من الحالة
ufw status
```

---

## أوامر مفيدة / Useful Commands

### إدارة جلسات Screen

```bash
# عرض الجلسات النشطة
screen -ls

# العودة لجلسة البوت
screen -r telegram_bot

# العودة لجلسة الواجهة
screen -r web_ui

# إيقاف جلسة معينة
screen -X -S telegram_bot quit
```

### إعادة تشغيل الخدمات

```bash
# إعادة تشغيل البوت
screen -r telegram_bot
# اضغط Ctrl+C ثم
python run.py

# إعادة تشغيل الواجهة
screen -r web_ui
# اضغط Ctrl+C ثم
npm run dev
```

### عرض السجلات

```bash
# سجلات البوت
tail -f /root/telegram_bot/bot.log

# سجلات النظام
journalctl -f
```

---

## استكشاف الأخطاء / Troubleshooting

### إذا لم يعمل البوت:

1. تأكد من صحة `TOKEN` في `config.py`
2. تحقق من اتصال الإنترنت
3. تأكد من تثبيت جميع المتطلبات:
   ```bash
   pip install -r requirements.txt
   ```

### إذا لم تعمل واجهة الويب:

1. تأكد من أن البورت 5000 مفتوح:
   ```bash
   netstat -tlnp | grep 5000
   ```
2. تحقق من تثبيت Node.js:
   ```bash
   node --version
   npm --version
   ```
3. أعد تثبيت الحزم:
   ```bash
   cd /root/telegram_bot/web_ui
   rm -rf node_modules
   npm install
   ```

### إذا لم تستطع الوصول للواجهة من الخارج:

1. تأكد من فتح البورت في جدار الحماية:
   ```bash
   ufw allow 5000/tcp
   ```
2. تأكد من أن الواجهة تستمع على 0.0.0.0:
   ```bash
   netstat -tlnp | grep 5000
   ```

### إذا ظهرت رسالة "كلمة المرور غير صحيحة":

1. تأكد من أن كلمة المرور هي `sohilSOHIL`
2. تأكد من تمرير متغير البيئة `ADMIN_PASSWORD` عند تشغيل الواجهة

---

## الأمان / Security Recommendations

1. **غيّر كلمة مرور السيرفر فوراً:**
   ```bash
   passwd root
   ```

2. **غيّر كلمة مرور البوت والواجهة:**
   - عدّل `ADMIN_PASSWORD` في `config.py`
   - أعد تشغيل البوت والواجهة

3. **استخدم HTTPS بدلاً من HTTP:**
   - قم بتثبيت Let's Encrypt
   - أو استخدم Cloudflare

4. **فعّل جدار الحماية:**
   ```bash
   ufw enable
   ```

5. **استخدم SSH Keys بدلاً من كلمة المرور:**
   ```bash
   ssh-copy-id -p 56777 root@162.19.199.122
   ```

---

## ملخص سريع / Quick Summary

| العنصر | الرابط/القيمة |
|--------|---------------|
| SSH | `ssh -p 56777 root@162.19.199.122` |
| واجهة الويب | `http://162.19.199.122:5000` |
| كلمة المرور | `sohilSOHIL` |
| مجلد البوت | `/root/telegram_bot` |
| مجلد الواجهة | `/root/telegram_bot/web_ui` |

---

**آخر تحديث:** ديسمبر 2025
