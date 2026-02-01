#!/bin/bash
# ============================================
# سكريبت تشغيل البوت وواجهة الويب
# آمن - لا يؤثر على البوتات الأخرى
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/bot.py" ]; then
    echo "خطأ: لم يتم العثور على bot.py"
    exit 1
fi

BOT_DIR="$SCRIPT_DIR"
WEB_DIR="$BOT_DIR/web_ui"
LOG_DIR="$BOT_DIR/logs"

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "     تشغيل بوت تيليجرام وواجهة الويب"
echo "=========================================="
echo ""

# إيقاف العمليات السابقة لهذا البوت فقط (عبر PID)
echo "إيقاف العمليات السابقة لهذا البوت فقط..."
if [ -f "$LOG_DIR/bot.pid" ]; then
    OLD_BOT_PID=$(cat "$LOG_DIR/bot.pid")
    if kill -0 "$OLD_BOT_PID" 2>/dev/null; then
        kill "$OLD_BOT_PID" 2>/dev/null && echo "  تم إيقاف البوت السابق (PID: $OLD_BOT_PID)"
        sleep 2
    fi
    rm -f "$LOG_DIR/bot.pid"
fi

if [ -f "$LOG_DIR/web.pid" ]; then
    OLD_WEB_PID=$(cat "$LOG_DIR/web.pid")
    if kill -0 "$OLD_WEB_PID" 2>/dev/null; then
        kill "$OLD_WEB_PID" 2>/dev/null && echo "  تم إيقاف الواجهة السابقة (PID: $OLD_WEB_PID)"
        sleep 1
    fi
    rm -f "$LOG_DIR/web.pid"
fi

rm -f "$BOT_DIR/bot.lock"

# Node.js لم يعد مطلوباً - نستخدم خادم Python
echo ""

# إعداد Python
echo "إعداد بيئة Python..."
if [ ! -d "$BOT_DIR/venv" ]; then
    echo "إنشاء البيئة الافتراضية..."
    cd "$BOT_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirementsfull.txt
else
    source "$BOT_DIR/venv/bin/activate"
fi

# لا حاجة لـ Node.js - نستخدم Flask

# تشغيل البوت
echo ""
echo "تشغيل بوت تيليجرام..."
cd "$BOT_DIR"
source venv/bin/activate

nohup python3 bot.py > "$LOG_DIR/bot.log" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$LOG_DIR/bot.pid"
echo "  البوت يعمل (PID: $BOT_PID)"

# تشغيل واجهة الويب
echo "تشغيل واجهة الويب..."
cd "$WEB_DIR"

# ============================================
# متغيرات البيئة - Environment Variables
# ============================================
# كلمة مرور لوحة التحكم - تُقرأ من قاعدة البيانات (جدول settings)
# إذا لم توجد في قاعدة البيانات، يُستخدم المتغير البيئي كاحتياطي
export ADMIN_PASSWORD="sohilSOHIL"
# منفذ واجهة الويب
export PORT="${PORT:-5000}"
# مسار مجلد البوت
export BOT_DIR="$BOT_DIR"
# توكن البوت (اختياري - يُقرأ من config.py إذا لم يُحدد)
export TOKEN="${TOKEN:-}"
# ملف قاعدة البيانات
export DATABASE_FILE="${DATABASE_FILE:-proxy_bot.db}"
# بيانات NonVoip (اختياري)
export NVUEMAIL="${NVUEMAIL:-}"
export NVUPASS="${NVUPASS:-}"

# التأكد من وجود ملفات الواجهة
if [ ! -d "$WEB_DIR/dist/public" ]; then
    echo "خطأ: مجلد dist/public غير موجود. يرجى نقل الملفات المبنية من Replit"
    exit 1
fi

# استخدام خادم Python بدلاً من Node.js
source "$BOT_DIR/venv/bin/activate"
nohup python3 web_server.py > "$LOG_DIR/web.log" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$LOG_DIR/web.pid"
echo "  الواجهة تعمل (PID: $WEB_PID)"

sleep 5

echo ""
echo "=========================================="
echo "           تم التشغيل بنجاح!"
echo "=========================================="
echo ""
echo "واجهة الويب: http://127.0.0.1:$PORT"
echo "كلمة المرور: sohilSOHIL"
echo ""
echo "لإيقاف الخدمات: $BOT_DIR/stop_all.sh"
echo ""

# اختبار سريع
if ss -tlnp 2>/dev/null | grep -q ":$PORT"; then
    echo "✓ المنفذ $PORT يعمل"
else
    echo "✗ تحقق من: tail -f $LOG_DIR/web.log"
fi
