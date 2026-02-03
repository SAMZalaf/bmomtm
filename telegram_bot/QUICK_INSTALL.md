# دليل التثبيت السريع - الطريقة البديلة
# Quick Installation Guide - Alternative Method

---

## معلومات السيرفر

| المعلومة | القيمة |
|---------|--------|
| IP Address | `162.19.199.122` |
| SSH Port | `56777` |
| Web Port | `5000` |

---

## الخطوة 1: الاتصال بالسيرفر

```bash
ssh -p 56777 root@162.19.199.122
```

---

## الخطوة 2: تحديث النظام وتثبيت المتطلبات

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nodejs npm ufw curl git
```

---

## الخطوة 3: نقل ملفات المشروع

### من جهازك المحلي (في terminal جديد):

```bash
scp -P 56777 -r ./telegram_bot root@162.19.199.122:/root/
```

---

## الخطوة 4: إعداد البيئة على السيرفر

```bash
cd /root/telegram_bot

# إعداد Python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# إعداد واجهة الويب
cd web_ui
npm install
```

---

## الخطوة 5: فتح البورتات

```bash
ufw allow 56777/tcp
ufw allow 5000/tcp
ufw --force enable
ufw status
```

---

## الخطوة 6: التشغيل

### الطريقة 1: سكريبت بسيط (للاختبار)

```bash
cd /root/telegram_bot
chmod +x start_services.sh stop_services.sh
./start_services.sh
```

### الطريقة 2: systemd (للإنتاج - موصى به)

```bash
cd /root/telegram_bot
chmod +x install_systemd.sh
./install_systemd.sh
```

**مميزات systemd:**
- تشغيل تلقائي عند إعادة تشغيل السيرفر
- إعادة تشغيل تلقائي عند حدوث خطأ
- سهولة المراقبة والتحكم

---

## الوصول لواجهة الويب

افتح في المتصفح:
```
http://162.19.199.122:5000
```

**كلمة المرور:** `sohilSOHIL`

---

## أوامر مفيدة

### الطريقة 1 (سكريبت):

```bash
# إيقاف الخدمات
./stop_services.sh

# تشغيل الخدمات
./start_services.sh

# عرض السجلات
tail -f /root/telegram_bot/logs/bot.log
tail -f /root/telegram_bot/logs/web.log
```

### الطريقة 2 (systemd):

```bash
# حالة الخدمات
systemctl status telegram-bot
systemctl status telegram-web

# إعادة تشغيل
systemctl restart telegram-bot
systemctl restart telegram-web

# إيقاف
systemctl stop telegram-bot
systemctl stop telegram-web

# السجلات
journalctl -u telegram-bot -f
journalctl -u telegram-web -f
```

---

## استكشاف الأخطاء

### إذا لم تعمل واجهة الويب:

```bash
# تحقق من البورت
netstat -tlnp | grep 5000

# تحقق من جدار الحماية
ufw status

# أعد تشغيل الخدمات
systemctl restart telegram-web
```

### إذا لم يعمل البوت:

```bash
# تحقق من السجلات
journalctl -u telegram-bot -n 50

# أو
tail -50 /root/telegram_bot/logs/bot.log
```

---

**آخر تحديث:** ديسمبر 2025
