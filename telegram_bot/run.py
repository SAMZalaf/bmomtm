#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
خادم Mini App - run.py
============================================
يشغل خادم Flask للـ Mini App لإدارة الأزرار

ملاحظة: البوت الرئيسي (bot.py) يعمل بشكل منفصل
على الخادم الخاص بك. هذا الملف يشغل فقط
واجهة إدارة الأزرار.
============================================
"""

import os
import sys
import logging
import signal

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """معالج إشارات الإيقاف"""
    logger.info("🛑 Shutting down Mini App Server...")
    sys.exit(0)


def main():
    """تشغيل خادم Mini App"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   🎛️  خادم Mini App - إدارة الأزرار الديناميكية                  ║
║                                                                   ║
║   📦 الخدمة: Flask Mini App Server (Port 5000)                    ║
║                                                                   ║
║   📌 ملاحظة: هذا الخادم لواجهة إدارة الأزرار فقط                 ║
║              البوت الرئيسي يعمل بشكل منفصل على خادمك              ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    os.environ['DEV_MODE'] = '1'
    
    from dynamic_buttons import dynamic_buttons_manager
    logger.info("✅ Dynamic buttons database initialized")
    
    from config import load_admin_ids
    admins = load_admin_ids()
    logger.info(f"👥 Loaded {len(admins)} admin(s)")
    
    from miniapp_server import app
    
    port = int(os.environ.get('FLASK_PORT', 5000))
    logger.info(f"🌐 Starting Flask Mini App Server on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )


if __name__ == '__main__':
    main()
