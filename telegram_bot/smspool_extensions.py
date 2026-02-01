#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smspool_extensions.py - إضافات وتوسعات لـ SMSPool Service

هذا الملف يحتوي على الدوال الإضافية التي تُضاف إلى SMSPoolDB class
للحصول على تكافؤ كامل مع NonVoip functionality
"""

import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def add_rentals_methods(db_class):
    """إضافة دوال Rentals إلى SMSPoolDB"""
    
    def create_rental(self, user_id: int, rental_code: str, rental_id: int,
                      number: str, country: str, service: str, service_id: str,
                      cost_price: float, sale_price: float, expires_at: str) -> Optional[int]:
        """إنشاء سجل إيجار جديد"""
        try:
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO smspool_rentals
                (user_id, rental_code, rental_id, number, country, service,
                 service_id, cost_price, sale_price, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, rental_code, rental_id, number, country, service,
                  service_id, cost_price, sale_price, expires_at))
            
            rental_db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created SMSPool rental {rental_code} for user {user_id}")
            return rental_db_id
            
        except Exception as e:
            logger.error(f"Error creating rental: {e}")
            return None
    
    def get_rental_by_code(self, rental_code: str) -> Optional[Dict]:
        """جلب إيجار بواسطة rental_code"""
        from smspool_service import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM smspool_rentals WHERE rental_code = ?
        """, (rental_code,))
        result = cursor.fetchone()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            conn.close()
            return dict(zip(columns, result))
        conn.close()
        return None
    
    def get_user_rentals(self, user_id: int, status: Optional[str] = None,
                         limit: int = 10) -> List[Dict]:
        """جلب إيجارات المستخدم"""
        from smspool_service import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM smspool_rentals
                WHERE user_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, status, limit))
        else:
            cursor.execute("""
                SELECT * FROM smspool_rentals
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in results]
    
    def update_rental_status(self, rental_code: str, status: str,
                             messages_today: int = None, messages_total: int = None) -> bool:
        """تحديث حالة الإيجار"""
        try:
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if messages_today is not None and messages_total is not None:
                cursor.execute("""
                    UPDATE smspool_rentals
                    SET status = ?, messages_today = ?, messages_total = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE rental_code = ?
                """, (status, messages_today, messages_total, rental_code))
            else:
                cursor.execute("""
                    UPDATE smspool_rentals
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE rental_code = ?
                """, (status, rental_code))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating rental status: {e}")
            return False
    
    def extend_rental_expiry(self, rental_code: str, new_expiry: str) -> bool:
        """تمديد فترة الإيجار"""
        try:
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE smspool_rentals
                SET expires_at = ?, extended = 1, updated_at = CURRENT_TIMESTAMP
                WHERE rental_code = ?
            """, (new_expiry, rental_code))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error extending rental: {e}")
            return False
    
    # إضافة الدوال إلى الـ class
    db_class.create_rental = create_rental
    db_class.get_rental_by_code = get_rental_by_code
    db_class.get_user_rentals = get_user_rentals
    db_class.update_rental_status = update_rental_status
    db_class.extend_rental_expiry = extend_rental_expiry


def add_messages_methods(db_class):
    """إضافة دوال Messages إلى SMSPoolDB"""
    
    def save_message(self, user_id: int, message_text: str, code: str = None,
                     sender: str = None, order_id: str = None, 
                     rental_code: str = None) -> bool:
        """حفظ رسالة جديدة مع الاحتفاظ بآخر 3 رسائل فقط"""
        try:
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO smspool_messages
                (user_id, message_text, code, sender, order_id, rental_code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, message_text, code, sender, order_id, rental_code))
            
            # حذف الرسائل القديمة (الاحتفاظ بآخر 3 فقط)
            if order_id:
                cursor.execute("""
                    SELECT COUNT(*) FROM smspool_messages WHERE order_id = ?
                """, (order_id,))
                count = cursor.fetchone()[0]
                
                if count > 3:
                    cursor.execute("""
                        DELETE FROM smspool_messages
                        WHERE id IN (
                            SELECT id FROM smspool_messages
                            WHERE order_id = ?
                            ORDER BY received_at ASC
                            LIMIT ?
                        )
                    """, (order_id, count - 3))
            
            elif rental_code:
                cursor.execute("""
                    SELECT COUNT(*) FROM smspool_messages WHERE rental_code = ?
                """, (rental_code,))
                count = cursor.fetchone()[0]
                
                if count > 3:
                    cursor.execute("""
                        DELETE FROM smspool_messages
                        WHERE id IN (
                            SELECT id FROM smspool_messages
                            WHERE rental_code = ?
                            ORDER BY received_at ASC
                            LIMIT ?
                        )
                    """, (rental_code, count - 3))
            
            conn.commit()
            conn.close()
            logger.info(f"Message saved for order_id={order_id}, rental_code={rental_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
    
    def get_messages(self, order_id: str = None, rental_code: str = None,
                     limit: int = 3) -> List[Dict]:
        """جلب آخر N رسائل"""
        from smspool_service import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if order_id:
            cursor.execute("""
                SELECT * FROM smspool_messages
                WHERE order_id = ?
                ORDER BY received_at DESC LIMIT ?
            """, (order_id, limit))
        elif rental_code:
            cursor.execute("""
                SELECT * FROM smspool_messages
                WHERE rental_code = ?
                ORDER BY received_at DESC LIMIT ?
            """, (rental_code, limit))
        else:
            conn.close()
            return []
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in results]
    
    # إضافة الدوال إلى الـ class
    db_class.save_message = save_message
    db_class.get_messages = get_messages


def add_logging_methods(db_class):
    """إضافة دوال Logging إلى SMSPoolDB"""
    
    def log_operation(self, user_id: int, operation_type: str, 
                      operation_category: str, order_id: str = None,
                      rental_code: str = None, amount: float = 0,
                      status: str = 'success', details: str = None,
                      error_message: str = None) -> bool:
        """تسجيل عملية في الـ log"""
        try:
            from smspool_service import get_db_connection, get_syria_time
            conn = get_db_connection()
            cursor = conn.cursor()
            
            syria_time = get_syria_time()
            
            cursor.execute("""
                INSERT INTO smspool_operations_log
                (user_id, operation_type, operation_category, order_id, rental_code,
                 amount, status, details, error_message, syria_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, operation_type, operation_category, order_id, rental_code,
                  amount, status, details, error_message, syria_time))
            
            conn.commit()
            conn.close()
            
            logger.info(f"LOG [{syria_time}] User:{user_id} | {operation_type} | {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging operation: {e}")
            return False
    
    # إضافة الدوال إلى الـ class
    db_class.log_operation = log_operation


def add_statistics_methods(db_class):
    """إضافة دوال Statistics إلى SMSPoolDB"""
    
    def update_statistics(self, is_rental: bool, sale_price: float, 
                          cost_price: float) -> bool:
        """تحديث الإحصائيات (يومي، أسبوعي، شهري، كلي)"""
        try:
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            for stat_type in ['daily', 'weekly', 'monthly', 'total']:
                if is_rental:
                    cursor.execute("""
                        INSERT OR REPLACE INTO smspool_statistics
                        (stat_date, stat_type, orders_count, rentals_count, 
                         total_revenue, total_cost, updated_at)
                        VALUES (
                            ?, ?,
                            COALESCE((SELECT orders_count FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0),
                            COALESCE((SELECT rentals_count FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + 1,
                            COALESCE((SELECT total_revenue FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                            COALESCE((SELECT total_cost FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                            CURRENT_TIMESTAMP
                        )
                    """, (today, stat_type, today, stat_type, today, stat_type,
                          today, stat_type, sale_price, today, stat_type, cost_price))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO smspool_statistics
                        (stat_date, stat_type, orders_count, rentals_count, 
                         total_revenue, total_cost, updated_at)
                        VALUES (
                            ?, ?,
                            COALESCE((SELECT orders_count FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + 1,
                            COALESCE((SELECT rentals_count FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0),
                            COALESCE((SELECT total_revenue FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                            COALESCE((SELECT total_cost FROM smspool_statistics 
                                     WHERE stat_date = ? AND stat_type = ?), 0) + ?,
                            CURRENT_TIMESTAMP
                        )
                    """, (today, stat_type, today, stat_type, today, stat_type,
                          today, stat_type, sale_price, today, stat_type, cost_price))
            
            conn.commit()
            conn.close()
            logger.info(f"Statistics updated: {'rental' if is_rental else 'order'} - ${sale_price}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """جلب الإحصائيات الكاملة"""
        from smspool_service import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        stats = {
            'daily': {'orders': 0, 'rentals': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'weekly': {'orders': 0, 'rentals': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'monthly': {'orders': 0, 'rentals': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0},
            'total': {'orders': 0, 'rentals': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0}
        }
        
        for stat_type in ['daily', 'weekly', 'monthly', 'total']:
            cursor.execute("""
                SELECT orders_count, rentals_count, total_revenue, total_cost
                FROM smspool_statistics
                WHERE stat_date = ? AND stat_type = ?
            """, (today, stat_type))
            
            row = cursor.fetchone()
            if row:
                stats[stat_type] = {
                    'orders': row[0] or 0,
                    'rentals': row[1] or 0,
                    'revenue': row[2] or 0.0,
                    'cost': row[3] or 0.0,
                    'profit': (row[2] or 0.0) - (row[3] or 0.0)
                }
        
        conn.close()
        return stats
    
    # إضافة الدوال إلى الـ class
    db_class.update_statistics = update_statistics
    db_class.get_statistics = get_statistics


def add_notification_methods(db_class):
    """إضافة دوال Notification Tracking إلى SMSPoolDB"""
    
    def check_notification_sent(self, notification_type: str, message_content: str,
                                order_id: str = None, rental_code: str = None) -> bool:
        """التحقق من إرسال رسالة مماثلة مسبقاً"""
        try:
            message_hash = hashlib.md5(message_content.encode('utf-8')).hexdigest()
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM smspool_sent_notifications
                WHERE notification_type = ? AND message_hash = ?
                AND (order_id = ? OR rental_code = ?)
            """, (notification_type, message_hash, order_id, rental_code))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking notification: {e}")
            return False
    
    def mark_notification_sent(self, user_id: int, notification_type: str,
                               message_content: str, order_id: str = None,
                               rental_code: str = None) -> bool:
        """تسجيل إرسال رسالة لمنع التكرار"""
        try:
            message_hash = hashlib.md5(message_content.encode('utf-8')).hexdigest()
            from smspool_service import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO smspool_sent_notifications
                (order_id, rental_code, user_id, notification_type, message_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (order_id, rental_code, user_id, notification_type, message_hash))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Notification marked as sent: {notification_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification: {e}")
            return False
    
    # إضافة الدوال إلى الـ class
    db_class.check_notification_sent = check_notification_sent
    db_class.mark_notification_sent = mark_notification_sent


def apply_all_extensions(db_class):
    """تطبيق جميع التوسعات على SMSPoolDB class"""
    add_rentals_methods(db_class)
    add_messages_methods(db_class)
    add_logging_methods(db_class)
    add_statistics_methods(db_class)
    add_notification_methods(db_class)
    logger.info("✅ All SMSPool extensions applied successfully")


# تطبيق التوسعات تلقائياً عند الاستيراد
try:
    from smspool_service import SMSPoolDB
    apply_all_extensions(SMSPoolDB)
    logger.info("SMSPoolDB enhanced with full functionality")
except ImportError:
    logger.warning("SMSPoolDB not found, extensions will be applied later")
