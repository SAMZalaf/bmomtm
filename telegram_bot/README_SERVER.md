# التشغيل على السيرفر - طريقة بسيطة

## الخطوة 1: انقل الملفات للسيرفر

من جهازك المحلي:
```bash
scp -P 56777 -r ./telegram_bot root@162.19.199.122:/root/
```

## الخطوة 2: اتصل بالسيرفر

```bash
ssh -p 56777 root@162.19.199.122
```

## الخطوة 3: شغّل السكريبت

```bash
cd /root/telegram_bot
chmod +x deploy_simple.sh
./deploy_simple.sh
```

## الخطوة 4: افتح في المتصفح

```
http://162.19.199.122:5000
```

كلمة المرور: `sohilSOHIL`

---

## أوامر مفيدة

```bash
# عرض السجلات
tail -f /root/telegram_bot/server.log

# إيقاف التطبيق
kill $(cat /root/telegram_bot/server.pid)

# إعادة التشغيل
./deploy_simple.sh
```
