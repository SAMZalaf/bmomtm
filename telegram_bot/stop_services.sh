#!/bin/bash
# ============================================
# سكريبت إيقاف البوت وواجهة الويب
# ============================================

echo "إيقاف جميع الخدمات..."

pkill -f "python3 bot.py" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "node.*web_ui" 2>/dev/null || true

echo "تم إيقاف جميع الخدمات."
