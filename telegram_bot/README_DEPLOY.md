# دليل نشر البوت على السيرفر

## الخطوات السريعة

### 1. رفع المجلد للسيرفر
```bash
# من جهازك المحلي
scp -r telegram_bot user@your-server:/home/user/
```

### 2. الدخول للسيرفر وتشغيل البوت
```bash
ssh user@your-server
cd /home/user/telegram_bot
chmod +x start_all.sh stop_all.sh
./start_all.sh
```

## المتطلبات

### على السيرفر يجب تثبيت:
- **Python 3.10+** 
- **Node.js 20+** (عبر NVM)
- **pip** و **venv**

### تثبيت NVM و Node.js (إذا لم يكن مثبتاً):
```bash
# تثبيت NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc

# تثبيت Node.js
nvm install 20
nvm use 20
```

### تثبيت Python (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

## إعداد ملف config.py

قبل التشغيل، تأكد من إعداد `config.py`:

```python
# config.py
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ADMIN_IDS = [123456789]  # ID المشرفين
# ... باقي الإعدادات
```

## متغيرات البيئة

يمكنك تعديل هذه المتغيرات في `start_all.sh`:

| المتغير | الوصف | القيمة الافتراضية |
|---------|-------|------------------|
| `ADMIN_PASSWORD` | كلمة مرور واجهة الويب | `admin123` |
| `PORT` | منفذ واجهة الويب | `5000` |

## الأوامر المتاحة

```bash
# تشغيل البوت والواجهة
./start_all.sh

# إيقاف جميع الخدمات
./stop_all.sh

# عرض سجلات البوت
tail -f logs/bot.log

# عرض سجلات الواجهة
tail -f logs/web.log
```

## فتح المنفذ في الجدار الناري

```bash
# UFW
sudo ufw allow 5000/tcp

# Firewalld
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## استخدام Caddy (اختياري)

للحصول على HTTPS وإخفاء المنفذ:

```bash
# تثبيت Caddy
sudo apt install caddy

# إعداد Caddyfile
echo 'your-domain.com {
    reverse_proxy localhost:5000
}' | sudo tee /etc/caddy/Caddyfile

# إعادة تشغيل Caddy
sudo systemctl restart caddy
```

## استكشاف الأخطاء

### البوت لا يعمل
```bash
# تحقق من السجلات
tail -100 logs/bot.log

# تأكد من صحة config.py
python3 -c "import config; print(config.BOT_TOKEN)"
```

### الواجهة لا تعمل
```bash
# تحقق من السجلات
tail -100 logs/web.log

# تحقق من المنفذ
ss -tlnp | grep 5000
```

### إعادة تثبيت الحزم
```bash
# Python
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Node.js
cd web_ui
rm -rf node_modules
npm install
```

## هيكل الملفات

```
telegram_bot/
├── bot.py              # البوت الرئيسي
├── config.py           # إعدادات البوت
├── requirements.txt    # متطلبات Python
├── start_all.sh        # سكريبت التشغيل
├── stop_all.sh         # سكريبت الإيقاف
├── logs/               # سجلات التشغيل
│   ├── bot.log
│   └── web.log
└── web_ui/             # واجهة الويب
    ├── package.json
    ├── dist/           # ملفات البناء
    └── server/
```
