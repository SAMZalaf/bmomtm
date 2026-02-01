#!/bin/bash
# ============================================
# سكريبت إيقاف البوت وواجهة الويب
# آمن - يوقف هذا البوت فقط عبر PID
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

echo "إيقاف خدمات هذا البوت فقط..."

# إيقاف البوت عبر PID
if [ -f "$LOG_DIR/bot.pid" ]; then
    BOT_PID=$(cat "$LOG_DIR/bot.pid")
    if kill -0 "$BOT_PID" 2>/dev/null; then
        kill "$BOT_PID" 2>/dev/null
        echo "✓ تم إيقاف البوت (PID: $BOT_PID)"
    else
        echo "البوت غير نشط (PID: $BOT_PID)"
    fi
    rm -f "$LOG_DIR/bot.pid"
else
    echo "لم يتم العثور على PID البوت"
fi

# إيقاف الواجهة عبر PID
if [ -f "$LOG_DIR/web.pid" ]; then
    WEB_PID=$(cat "$LOG_DIR/web.pid")
    if kill -0 "$WEB_PID" 2>/dev/null; then
        kill "$WEB_PID" 2>/dev/null
        echo "✓ تم إيقاف الواجهة (PID: $WEB_PID)"
    else
        echo "الواجهة غير نشطة (PID: $WEB_PID)"
    fi
    rm -f "$LOG_DIR/web.pid"
else
    echo "لم يتم العثور على PID الواجهة"
fi

# إزالة ملف القفل
rm -f "$SCRIPT_DIR/bot.lock"

echo ""
echo "تم الإيقاف بنجاح"
