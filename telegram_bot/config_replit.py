#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
📍 ملف الإعدادات والقواميس - config.py
============================================
يحتوي على:
1. كلاس Config - الإعدادات الأساسية
2. قواميس الدول والولايات
3. قاموس الرسائل (عربي/إنجليزي)
4. نظام FAQ
5. دوال مساعدة
============================================
"""

import os
import sqlite3
import logging
from typing import Optional, List, Dict, Tuple, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# ============================================
# 📍 قسم 1: Config class (الإعدادات الأساسية)
# ============================================

class Config:
    """
    إدارة مركزية لجميع الإعدادات والرموز السرية في البوت
    Central management for all bot settings and secrets
    """
    
    # ========== معلومات البوت ==========
    TOKEN: str = "7751227560:AAFovxVRR7dA1x7cqsJ3wsc4MPhttU4UeJU"
    
    # كلمة مرور الآدمن
    ADMIN_PASSWORD: str = "sohilSOHIL"
    
    # ========== قاعدة البيانات ==========
    DATABASE_FILE: str = "proxy_bot.db"
    
    # ========== NonVoip API Credentials ==========
    NVUEMAIL: str = "Mohamadzalaf2017@gmail.com"
    NVUPASS: str = "sohilSOHIL"
    
    # ========== الإعدادات العامة ==========
    TIMEZONE: str = "Asia/Damascus"
    DEFAULT_LANGUAGE: str = "ar"
    
    # ========== إعدادات الأسعار ==========
    DEFAULT_CREDIT_VALUE: float = 1.0
    DEFAULT_NONVOIP_MARGIN_PERCENT: float = 20.0
    
    # ========== معرفات المسؤولين ==========
    ADMIN_IDS: List[int] = []  # أضف معرفات المسؤولين هنا
    
    # ========== رابط التطبيق المصغر (Mini App) ==========
    MINIAPP_URL: str = "https://02c45ba9-afeb-4b70-8d29-318cd1262c48-00-2tt0f0w5iz7g3.kirk.replit.dev"
    
    @classmethod
    def validate(cls) -> bool:
        """التحقق من وجود جميع المتغيرات الضرورية"""
        missing_vars = []
        
        if not cls.TOKEN:
            missing_vars.append("TOKEN")
        if not cls.ADMIN_PASSWORD:
            missing_vars.append("ADMIN_PASSWORD")
        if not cls.NVUEMAIL:
            missing_vars.append("NVUEMAIL")
        if not cls.NVUPASS:
            missing_vars.append("NVUPASS")
        
        if missing_vars:
            print(f"⚠️ تحذير: المتغيرات التالية غير محددة:")
            for var in missing_vars:
                print(f"  - {var}")
            return False
        return True
    
    @classmethod
    def get_nonvoip_credentials(cls) -> dict:
        """الحصول على بيانات تسجيل الدخول لـ NonVoip"""
        return {
            "email": cls.NVUEMAIL,
            "password": cls.NVUPASS
        }


DATABASE_FILE = Config.DATABASE_FILE
DB_PATH = Config.DATABASE_FILE  # اسم مستعار لمسار قاعدة البيانات
ADMIN_IDS = Config.ADMIN_IDS  # معرفات المسؤولين
BOT_TOKEN = Config.TOKEN  # توكن البوت للـ Mini App
MINIAPP_URL = Config.MINIAPP_URL  # رابط التطبيق المصغر


# ============================================
# 📍 قسم 2: قواميس الدول للبروكسي
# ============================================

# دول الستاتيك بروكسي
STATIC_COUNTRIES = {
    'ar': {
        'US': '🇺🇸 الولايات المتحدة',
        'UK': '🇬🇧 بريطانيا',
        'FR': '🇫🇷 فرنسا',
        'DE': '🇩🇪 ألمانيا',
        'AT': '🇦🇹 النمسا'
    },
    'en': {
        'US': '🇺🇸 United States',
        'UK': '🇬🇧 United Kingdom',
        'FR': '🇫🇷 France',
        'DE': '🇩🇪 Germany',
        'AT': '🇦🇹 Austria'
    }
}

# دول السوكس بروكسي
SOCKS_COUNTRIES = {
    'ar': {
        'US': '🇺🇸 الولايات المتحدة',
        'FR': '🇫🇷 فرنسا',
        'ES': '🇪🇸 إسبانيا',
        'UK': '🇬🇧 بريطانيا',
        'CA': '🇨🇦 كندا',
        'DE': '🇩🇪 ألمانيا',
        'IT': '🇮🇹 إيطاليا',
        'SE': '🇸🇪 السويد',
        'UA': '🇺🇦 أوكرانيا',
        'PL': '🇵🇱 بولندا',
        'NL': '🇳🇱 هولندا',
        'RO': '🇷🇴 رومانيا',
        'BG': '🇧🇬 بلغاريا',
        'RS': '🇷🇸 صربيا',
        'CZ': '🇨🇿 التشيك',
        'AE': '🇦🇪 الإمارات العربية المتحدة',
        'FI': '🇫🇮 فنلندا',
        'BE': '🇧🇪 بلجيكا',
        'HU': '🇭🇺 المجر',
        'PT': '🇵🇹 البرتغال',
        'GR': '🇬🇷 اليونان',
        'NO': '🇳🇴 النرويج',
        'AT': '🇦🇹 النمسا',
        'BY': '🇧🇾 بيلاروسيا',
        'SK': '🇸🇰 سلوفاكيا',
        'AL': '🇦🇱 ألبانيا',
        'MD': '🇲🇩 مولدوفا',
        'LT': '🇱🇹 ليتوانيا',
        'CH': '🇨🇭 سويسرا',
        'DK': '🇩🇰 الدنمارك',
        'IE': '🇮🇪 أيرلندا',
        'EE': '🇪🇪 إستونيا',
        'MT': '🇲🇹 مالطا',
        'LU': '🇱🇺 لوكسمبورغ',
        'CY': '🇨🇾 قبرص',
        'BA': '🇧🇦 البوسنة والهرسك',
        'SY': '🇸🇾 سوريا',
        'IS': '🇮🇸 أيسلندا',
        'MK': '🇲🇰 مقدونيا الشمالية'
    },
    'en': {
        'US': '🇺🇸 United States',
        'FR': '🇫🇷 France',
        'ES': '🇪🇸 Spain',
        'UK': '🇬🇧 United Kingdom',
        'CA': '🇨🇦 Canada',
        'DE': '🇩🇪 Germany',
        'IT': '🇮🇹 Italy',
        'SE': '🇸🇪 Sweden',
        'UA': '🇺🇦 Ukraine',
        'PL': '🇵🇱 Poland',
        'NL': '🇳🇱 Netherlands',
        'RO': '🇷🇴 Romania',
        'BG': '🇧🇬 Bulgaria',
        'RS': '🇷🇸 Serbia',
        'CZ': '🇨🇿 Czechia',
        'AE': '🇦🇪 United Arab Emirates',
        'FI': '🇫🇮 Finland',
        'BE': '🇧🇪 Belgium',
        'HU': '🇭🇺 Hungary',
        'PT': '🇵🇹 Portugal',
        'GR': '🇬🇷 Greece',
        'NO': '🇳🇴 Norway',
        'AT': '🇦🇹 Austria',
        'BY': '🇧🇾 Belarus',
        'SK': '🇸🇰 Slovakia',
        'AL': '🇦🇱 Albania',
        'MD': '🇲🇩 Moldova',
        'LT': '🇱🇹 Lithuania',
        'CH': '🇨🇭 Switzerland',
        'DK': '🇩🇰 Denmark',
        'IE': '🇮🇪 Ireland',
        'EE': '🇪🇪 Estonia',
        'MT': '🇲🇹 Malta',
        'LU': '🇱🇺 Luxembourg',
        'CY': '🇨🇾 Cyprus',
        'BA': '🇧🇦 Bosnia and Herzegovina',
        'SY': '🇸🇾 Syria',
        'IS': '🇮🇸 Iceland',
        'MK': '🇲🇰 North Macedonia'
    }
}


# ============================================
# 📍 قسم 3: ولايات أمريكا للسوكس
# ============================================

US_STATES_SOCKS = {
    'ar': {
        'AL': 'ألاباما',
        'AK': 'ألاسكا', 
        'AZ': 'أريزونا',
        'AR': 'أركنساس',
        'CA': 'كاليفورنيا',
        'CO': 'كولورادو',
        'CT': 'كونيتيكت',
        'DE': 'ديلاوير',
        'FL': 'فلوريدا',
        'GA': 'جورجيا',
        'HI': 'هاواي',
        'ID': 'أيداهو',
        'IL': 'إلينوي',
        'IN': 'إنديانا',
        'IA': 'أيوا',
        'KS': 'كانساس',
        'KY': 'كنتاكي',
        'LA': 'لويزيانا',
        'ME': 'مين',
        'MD': 'ماريلاند',
        'MA': 'ماساتشوستس',
        'MI': 'ميشيغان',
        'MN': 'مينيسوتا',
        'MS': 'ميسيسيبي',
        'MO': 'ميزوري',
        'MT': 'مونتانا',
        'NE': 'نبراسكا',
        'NV': 'نيفادا',
        'NH': 'نيو هامبشير',
        'NJ': 'نيو جيرسي',
        'NM': 'نيو مكسيكو',
        'NY': 'نيويورك',
        'NC': 'كارولينا الشمالية',
        'ND': 'داكوتا الشمالية',
        'OH': 'أوهايو',
        'OK': 'أوكلاهوما',
        'OR': 'أوريغون',
        'PA': 'بنسلفانيا',
        'RI': 'رود آيلاند',
        'SC': 'كارولينا الجنوبية',
        'SD': 'داكوتا الجنوبية',
        'TN': 'تينيسي',
        'TX': 'تكساس',
        'UT': 'يوتا',
        'VT': 'فيرمونت',
        'VA': 'فيرجينيا',
        'WA': 'واشنطن',
        'WV': 'فيرجينيا الغربية',
        'WI': 'ويسكونسن',
        'WY': 'وايومنغ'
    },
    'en': {
        'AL': 'Alabama',
        'AK': 'Alaska',
        'AZ': 'Arizona',
        'AR': 'Arkansas',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'HI': 'Hawaii',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'IA': 'Iowa',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'ME': 'Maine',
        'MD': 'Maryland',
        'MA': 'Massachusetts',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MS': 'Mississippi',
        'MO': 'Missouri',
        'MT': 'Montana',
        'NE': 'Nebraska',
        'NV': 'Nevada',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NY': 'New York',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VT': 'Vermont',
        'VA': 'Virginia',
        'WA': 'Washington',
        'WV': 'West Virginia',
        'WI': 'Wisconsin',
        'WY': 'Wyoming'
    }
}

# للتوافق مع الأكواد الموجودة
US_STATES = US_STATES_SOCKS


# ============================================
# 📍 قسم 4: ولايات الستاتيك حسب المزود
# ============================================

# ولايات الستاتيك Verizon ريزيدنتال الشهري - $4
US_STATES_STATIC_VERIZON = {
    'ar': {
        'NY': 'نيويورك',
        'VA': 'فيرجينيا',
        'WA': 'واشنطن',
        'IL': 'إلينوي'
    },
    'en': {
        'NY': 'New York',
        'VA': 'Virginia',
        'WA': 'Washington',
        'IL': 'Illinois'
    }
}

# ولايات الستاتيك Crocker ريزيدنتال الشهري - $4
US_STATES_STATIC_CROCKER = {
    'ar': {
        'MA': 'ماساتشوستس'
    },
    'en': {
        'MA': 'Massachusetts'
    }
}

# ولايات الستاتيك Level 3 ISP ريزيدنتال الشهري - $4
US_STATES_STATIC_LEVEL3 = {
    'ar': {
        'NY': 'نيويورك'
    },
    'en': {
        'NY': 'New York'
    }
}

# ولايات الستاتيك Frontier Communications ريزيدنتال الشهري - $4
US_STATES_STATIC_FRONTIER = {
    'ar': {
        'VT': 'فيرمونت'
    },
    'en': {
        'VT': 'Vermont'
    }
}

# مواقع إنجلترا للستاتيك NTT ريزيدنتال الشهري - $4
ENGLAND_STATIC_NTT = {
    'ar': {
        'ENG': 'إنجلترا'
    },
    'en': {
        'ENG': 'England'
    }
}

# الدول للتوسع المستقبلي
RESIDENTIAL_4_COUNTRIES = {
    'ar': {
        'US': 'الولايات المتحدة',
        'England': 'إنجلترا',
        'Austria': 'النمسا',
        'Canada': 'كندا',
        'Spain': 'إسبانيا',
        'Italy': 'إيطاليا',
        'Netherlands': 'هولندا',
        'Poland': 'بولندا',
        'Romania': 'رومانيا',
        'Turkey': 'تركيا',
        'Ukraine': 'أوكرانيا',
        'Israel': 'إسرائيل',
        'India': 'الهند',
        'Hong Kong': 'هونغ كونغ',
        'Thailand': 'تايلاند',
        'Singapore': 'سنغافورة',
        'Taiwan': 'تايوان'
    },
    'en': {
        'US': 'United States',
        'England': 'England',
        'Austria': 'Austria',
        'Canada': 'Canada',
        'Spain': 'Spain',
        'Italy': 'Italy',
        'Netherlands': 'Netherlands',
        'Poland': 'Poland',
        'Romania': 'Romania',
        'Turkey': 'Turkey',
        'Ukraine': 'Ukraine',
        'Israel': 'Israel',
        'India': 'India',
        'Hong Kong': 'Hong Kong',
        'Thailand': 'Thailand',
        'Singapore': 'Singapore',
        'Taiwan': 'Taiwan'
    }
}

# ولايات الستاتيك الأسبوعي - $2.5
STATIC_WEEKLY_LOCATIONS = {
    'ar': {
        'US': {
            'NY': 'نيويورك',
            'VA': 'فيرجينيا',
            'WA': 'واشنطن'
        }
    },
    'en': {
        'US': {
            'NY': 'New York',
            'VA': 'Virginia', 
            'WA': 'Washington'
        }
    }
}

# ولايات الستاتيك اليومي - $0.25
STATIC_DAILY_LOCATIONS = {
    'ar': {
        'US': {
            'VA': 'فيرجينيا'
        }
    },
    'en': {
        'US': {
            'VA': 'Virginia'
        }
    }
}

# خدمات ISP الأمريكية - Residential 6$
US_RESIDENTIAL_ISP_SERVICES = {
    'ar': {
        'CO_EB': 'كولورادو - Elite Broadband',
        'VA_WS': 'فيرجينيا - Windstream',
        'VA_CC': 'فيرجينيا - Cox Communication',
        'VA_FC': 'فيرجينيا - Frontier Communications',
        'TX_JY': 'تكساس - JY Mobile Communication',
        'NY_WS': 'نيويورك - WS Telcom',
        'NY_CL': 'نيويورك - Century Link Perfect',
        'IL_AT': 'إلينوي - Access Telcom',
        'AZ_JY': 'أريزونا - JY Mobile Communication'
    },
    'en': {
        'CO_EB': 'Colorado - Elite Broadband',
        'VA_WS': 'Virginia - Windstream',
        'VA_CC': 'Virginia - Cox Communication',
        'VA_FC': 'Virginia - Frontier Communications',
        'TX_JY': 'Texas - JY Mobile Communication',
        'NY_WS': 'New York - WS Telcom',
        'NY_CL': 'New York - Century Link Perfect',
        'IL_AT': 'Illinois - Access Telcom',
        'AZ_JY': 'Arizona - JY Mobile Communication'
    }
}

# القاموس القديم للتوافق مع الأكواد الموجودة
US_STATES_STATIC_RESIDENTIAL = {
    'ar': {
        'NY': 'نيويورك',
        'AZ': 'أريزونا', 
        'CO': 'كولورادو',
        'DE': 'ديلاوير',
        'IL': 'إلينوي',
        'TX': 'تكساس',
        'VA': 'فيرجينيا',
        'WA': 'واشنطن'
    },
    'en': {
        'NY': 'New York',
        'AZ': 'Arizona',
        'CO': 'Colorado',
        'DE': 'Delaware',
        'IL': 'Illinois',
        'TX': 'Texas',
        'VA': 'Virginia',
        'WA': 'Washington'
    }
}

# ستاتيك ISP
US_STATES_STATIC_ISP = {
    'ar': {
        'ATT': 'ISP (عشوائي الموقع)'
    },
    'en': {
        'ATT': 'ISP (Random Location)'
    }
}


# ============================================
# 📍 قسم 5: خدمات المملكة المتحدة
# ============================================

# خدمات المملكة المتحدة - 7 خدمات
UK_RESIDENTIAL_ISP_SERVICES = {
    'ar': {
        'UK_BC': 'British Communications',
        'UK_PS': 'Proper Support LLP',
        'UK_UK': 'UKR Telcom',
        'UK_LW': 'Link Web Fiber ISP',
        'UK_WS': 'WS Telcom',
        'UK_BA': 'Base Communication LLP',
        'UK_VM': 'Virgin Media'
    },
    'en': {
        'UK_BC': 'British Communications',
        'UK_PS': 'Proper Support LLP',
        'UK_UK': 'UKR Telcom',
        'UK_LW': 'Link Web Fiber ISP',
        'UK_WS': 'WS Telcom',
        'UK_BA': 'Base Communication LLP',
        'UK_VM': 'Virgin Media'
    }
}

# القاموس القديم للتوافق
UK_STATES_STATIC_RESIDENTIAL = {
    'ar': {
        'BC': 'British Communications',
        'PS': 'Proper Support LLP',
        'UK': 'UKR Telcom',
        'LW': 'Link Web Fiber ISP',
        'WS': 'WS Telcom',
        'BA': 'Base Communication LLP',
        'VM': 'Virgin Media'
    },
    'en': {
        'BC': 'British Communications',
        'PS': 'Proper Support LLP',
        'UK': 'UKR Telcom',
        'LW': 'Link Web Fiber ISP',
        'WS': 'WS Telcom',
        'BA': 'Base Communication LLP',
        'VM': 'Virgin Media'
    }
}

# مناطق المملكة المتحدة
UK_STATES = {
    'ar': {
        'ENG': 'إنجلترا',
        'SCT': 'اسكتلندا',
        'WAL': 'ويلز',
        'NIR': 'أيرلندا الشمالية'
    },
    'en': {
        'ENG': 'England',
        'SCT': 'Scotland',
        'WAL': 'Wales', 
        'NIR': 'Northern Ireland'
    }
}


# ============================================
# 📍 قسم 6: مناطق الدول الأخرى
# ============================================

# مناطق ألمانيا
DE_STATES = {
    'ar': {
        'BW': 'بادن فورتمبيرغ',
        'BY': 'بافاريا',
        'BE': 'برلين',
        'BB': 'براندنبورغ',
        'HB': 'بريمن',
        'HH': 'هامبورغ',
        'HE': 'هيسن',
        'NI': 'ساكسونيا السفلى',
        'NW': 'شمال الراين وستفاليا',
        'RP': 'راينلاند بالاتينات',
        'SL': 'سارلاند',
        'SN': 'ساكسونيا',
        'ST': 'ساكسونيا أنهالت',
        'SH': 'شليسفيغ هولشتاين',
        'TH': 'تورينغن'
    },
    'en': {
        'BW': 'Baden-Württemberg',
        'BY': 'Bavaria',
        'BE': 'Berlin',
        'BB': 'Brandenburg',
        'HB': 'Bremen',
        'HH': 'Hamburg',
        'HE': 'Hesse',
        'NI': 'Lower Saxony',
        'NW': 'North Rhine-Westphalia',
        'RP': 'Rhineland-Palatinate',
        'SL': 'Saarland',
        'SN': 'Saxony',
        'ST': 'Saxony-Anhalt',
        'SH': 'Schleswig-Holstein',
        'TH': 'Thuringia'
    }
}

# مناطق فرنسا
FR_STATES = {
    'ar': {
        'ARA': 'أوفيرن رون ألب',
        'BFC': 'بورغونيا فرانش كونته',
        'BRE': 'بريتاني',
        'CVL': 'وسط وادي اللوار',
        'COR': 'كورسيكا',
        'GES': 'الألزاس الشرقي',
        'HDF': 'هو دو فرانس',
        'IDF': 'إيل دو فرانس',
        'NOR': 'نورماندي',
        'NAQ': 'آكيتين الجديدة',
        'OCC': 'أوكسيتانيا',
        'PDL': 'باي دو لا لوار',
        'PAC': 'بروفانس ألب كوت دازور'
    },
    'en': {
        'ARA': 'Auvergne-Rhône-Alpes',
        'BFC': 'Burgundy-Franche-Comté',
        'BRE': 'Brittany',
        'CVL': 'Centre-Val de Loire',
        'COR': 'Corsica',
        'GES': 'Grand Est',
        'HDF': 'Hauts-de-France',
        'IDF': 'Île-de-France',
        'NOR': 'Normandy',
        'NAQ': 'Nouvelle-Aquitaine',
        'OCC': 'Occitania',
        'PDL': 'Pays de la Loire',
        'PAC': "Provence-Alpes-Côte d'Azur"
    }
}

# مناطق إيطاليا
IT_STATES = {
    'ar': {
        'ABR': 'أبروتسو',
        'BAS': 'باسيليكاتا',
        'CAL': 'كالابريا',
        'CAM': 'كامبانيا',
        'EMR': 'إميليا رومانيا',
        'FVG': 'فريولي فينيتسيا جوليا',
        'LAZ': 'لاتسيو',
        'LIG': 'ليغوريا',
        'LOM': 'لومبارديا',
        'MAR': 'ماركي',
        'MOL': 'موليسي',
        'PIE': 'بيدمونت',
        'PUG': 'بوليا',
        'SAR': 'سردينيا',
        'SIC': 'صقلية',
        'TOS': 'توسكانا',
        'TRE': 'ترينتينو ألتو أديجي',
        'UMB': 'أومبريا',
        'VDA': 'وادي أوستا',
        'VEN': 'فينيتو'
    },
    'en': {
        'ABR': 'Abruzzo',
        'BAS': 'Basilicata',
        'CAL': 'Calabria',
        'CAM': 'Campania',
        'EMR': 'Emilia-Romagna',
        'FVG': 'Friuli-Venezia Giulia',
        'LAZ': 'Lazio',
        'LIG': 'Liguria',
        'LOM': 'Lombardy',
        'MAR': 'Marche',
        'MOL': 'Molise',
        'PIE': 'Piedmont',
        'PUG': 'Puglia',
        'SAR': 'Sardinia',
        'SIC': 'Sicily',
        'TOS': 'Tuscany',
        'TRE': 'Trentino-Alto Adige',
        'UMB': 'Umbria',
        'VDA': 'Aosta Valley',
        'VEN': 'Veneto'
    }
}

# ولايات الهند
IN_STATES = {
    'ar': {
        'DL': 'دلهي',
        'MH': 'ماهاراشترا (مومباي)',
        'KA': 'كارناتاكا (بنغالور)',
        'TN': 'تاميل نادو (تشيناي)',
        'WB': 'البنغال الغربية (كولكاتا)',
        'GJ': 'غوجارات',
        'RJ': 'راجاستان',
        'UP': 'أوتار براديش',
        'TG': 'تيلانغانا (حيدر أباد)',
        'AP': 'أندرا براديش',
        'KL': 'كيرالا',
        'OR': 'أوديشا',
        'JH': 'جهارخاند',
        'AS': 'آسام',
        'PB': 'البنجاب'
    },
    'en': {
        'DL': 'Delhi',
        'MH': 'Maharashtra (Mumbai)',
        'KA': 'Karnataka (Bangalore)',
        'TN': 'Tamil Nadu (Chennai)',
        'WB': 'West Bengal (Kolkata)',
        'GJ': 'Gujarat',
        'RJ': 'Rajasthan',
        'UP': 'Uttar Pradesh',
        'TG': 'Telangana (Hyderabad)',
        'AP': 'Andhra Pradesh',
        'KL': 'Kerala',
        'OR': 'Odisha',
        'JH': 'Jharkhand',
        'AS': 'Assam',
        'PB': 'Punjab'
    }
}


# ============================================
# 📍 قسم 7: قاعدة بيانات Area Codes للولايات الأمريكية
# ============================================

US_STATE_AREA_CODES = {
    'California': ['209', '213', '279', '310', '323', '408', '415', '424', '442', '510', '530', '559', '562', '619', '626', '628', '650', '657', '661', '669', '707', '714', '747', '760', '805', '818', '831', '858', '909', '916', '925', '949', '951'],
    'Texas': ['210', '214', '254', '281', '325', '346', '361', '409', '430', '432', '469', '512', '682', '713', '726', '737', '806', '817', '830', '832', '903', '915', '936', '940', '956', '972', '979'],
    'New York': ['212', '315', '332', '347', '516', '518', '585', '607', '631', '646', '680', '716', '718', '838', '845', '914', '917', '929', '934'],
    'Florida': ['239', '305', '321', '352', '386', '407', '561', '727', '754', '772', '786', '813', '850', '863', '904', '941', '954'],
    'Illinois': ['217', '224', '309', '312', '331', '618', '630', '708', '773', '779', '815', '847', '872'],
    'Pennsylvania': ['215', '223', '267', '272', '412', '445', '484', '570', '582', '610', '717', '724', '814', '878'],
    'Ohio': ['216', '220', '234', '330', '380', '419', '440', '513', '567', '614', '740', '937'],
    'Georgia': ['229', '404', '470', '478', '678', '706', '762', '770', '912'],
    'North Carolina': ['252', '336', '704', '743', '828', '910', '919', '980', '984'],
    'Michigan': ['231', '248', '269', '313', '517', '586', '616', '734', '810', '906', '947', '989'],
    'New Jersey': ['201', '551', '609', '640', '732', '848', '856', '862', '908', '973'],
    'Virginia': ['276', '434', '540', '571', '703', '757', '804'],
    'Washington': ['206', '253', '360', '425', '509', '564'],
    'Arizona': ['480', '520', '602', '623', '928'],
    'Massachusetts': ['339', '351', '413', '508', '617', '774', '781', '857', '978'],
    'Indiana': ['219', '260', '317', '463', '574', '765', '812', '930'],
    'Tennessee': ['423', '615', '629', '731', '865', '901', '931'],
    'Missouri': ['314', '417', '573', '636', '660', '816'],
    'Maryland': ['240', '301', '410', '443', '667'],
    'Wisconsin': ['262', '274', '414', '534', '608', '715', '920'],
    'Colorado': ['303', '719', '720', '970'],
    'Minnesota': ['218', '320', '507', '612', '651', '763', '952'],
    'South Carolina': ['803', '839', '843', '854', '864'],
    'Alabama': ['205', '251', '256', '334', '938'],
    'Louisiana': ['225', '318', '337', '504', '985'],
    'Kentucky': ['270', '364', '502', '606', '859'],
    'Oregon': ['458', '503', '541', '971'],
    'Oklahoma': ['405', '539', '580', '918'],
    'Connecticut': ['203', '475', '860', '959'],
    'Utah': ['385', '435', '801'],
    'Iowa': ['319', '515', '563', '641', '712'],
    'Nevada': ['702', '725', '775'],
    'Arkansas': ['479', '501', '870'],
    'Mississippi': ['228', '601', '662', '769'],
    'Kansas': ['316', '620', '785', '913'],
    'New Mexico': ['505', '575'],
    'Nebraska': ['308', '402', '531'],
    'West Virginia': ['304', '681'],
    'Idaho': ['208', '986'],
    'Hawaii': ['808'],
    'New Hampshire': ['603'],
    'Maine': ['207'],
    'Rhode Island': ['401'],
    'Montana': ['406'],
    'Delaware': ['302'],
    'South Dakota': ['605'],
    'North Dakota': ['701'],
    'Alaska': ['907'],
    'Vermont': ['802'],
    'Wyoming': ['307']
}

# الولايات الأكثر شعبية
POPULAR_US_STATES = [
    'California', 'Texas', 'New York', 'Florida', 'Illinois',
    'Pennsylvania', 'Ohio', 'Georgia', 'North Carolina', 'Michigan'
]

# الأسماء بالعربية للولايات الشائعة
US_STATE_NAMES_AR = {
    'California': 'كاليفورنيا',
    'Texas': 'تكساس',
    'New York': 'نيويورك',
    'Florida': 'فلوريدا',
    'Illinois': 'إلينوي',
    'Pennsylvania': 'بنسلفانيا',
    'Ohio': 'أوهايو',
    'Georgia': 'جورجيا',
    'North Carolina': 'كارولينا الشمالية',
    'Michigan': 'ميشيغان',
    'Virginia': 'فيرجينيا',
    'Washington': 'واشنطن',
    'Arizona': 'أريزونا',
    'Massachusetts': 'ماساتشوستس'
}


# ============================================
# 📍 قسم 8: قاموس الرسائل (عربي/إنجليزي)
# ============================================

MESSAGES = {
    'ar': {
        'welcome': """✨ ━━━━━━━━━━━━━━━ ✨

🌟 مرحباً بك في Static_Bot 🌟

✨ ━━━━━━━━━━━━━━━ ✨

💎 أفضل خدمات البروكسي الاحترافية 💎

🚀 اختر الخدمة المطلوبة من الأزرار أدناه:""",
        'static_package': """📦 باكج البروكسي الستاتيك

━━━━━━━━━━━━━━━
📋 بعد اختيار الخدمة:
✅ سيستقبل الأدمن طلبك
⚡ سنعالج الطلب ونرسل لك البروكسي
📬 ستصلك رسالة تأكيد عند الانتهاء

معرف الطلب: {order_id}""",
        'socks_package': """📦 باكج البروكسي السوكس
🌍 جميع دول العالم | اختيار الولاية والمزود

🔹 الأسعار المتوفرة:
• بروكسي واحد: {single_price}$
• بروكسيان اثنان: {double_price}$  
• باكج 5 بروكسيات يومية: {five_price}$
• باكج 10 بروكسيات يومية: {ten_price}$

━━━━━━━━━━━━━━━
📋 بعد اختيار الخدمة:
✅ سيستقبل الأدمن طلبك
⚡ سنعالج الطلب ونرسل لك البروكسي
📬 ستصلك رسالة تأكيد عند الانتهاء

معرف الطلب: {order_id}""",
        'select_country': 'اختر الدولة:',
        'select_state': 'اختر الولاية:',
        'payment_methods': 'اختر طريقة الدفع:',
        'send_payment_proof': 'يرجى إرسال إثبات الدفع (صورة فقط):',
        'order_received': '✅ تم استلام طلبك بنجاح!\n\n📋 سيتم معالجة الطلب يدوياً من الأدمن بأقرب وقت.\n\n📧 ستصلك تحديثات الحالة تلقائياً.',
        'main_menu_buttons': ['🔒 طلب بروكسي ستاتيك', '📡 طلب بروكسي سوكس', '🎁 تجربة ستاتيك مجانا', '💰 الرصيد', '📋 طلباتي', '⚙️ الإعدادات', '📱 أرقام Non-VoIP', '💱 سعر الصرف', '📖 لمحة عن خدماتنا'],
        'admin_main_buttons': ['📋 إدارة الطلبات', '💰 إدارة الأموال', '👥 الإحالات', '📢 البث', '⚙️ الإعدادات'],
        'change_password': 'تغيير كلمة المرور',
        'password_changed': 'تم تغيير كلمة المرور بنجاح ✅',
        'invalid_password': 'كلمة المرور غير صحيحة!',
        'enter_new_password': 'يرجى إدخال كلمة المرور الجديدة:',
        'withdrawal_processing': 'جاري معالجة طلب سحب رصيدك من قبل الأدمن...',
        'admin_contact': 'ستتواصل الإدارة معك قريباً لتسليمك مكافأتك.',
        'language_change_success': 'تم تغيير اللغة إلى العربية ✅\nيرجى استخدام الأمر /start لإعادة تحميل القوائم',
        'admin_panel': '🔧 لوحة الأدمن',
        'manage_orders': 'إدارة الطلبات',
        'pending_orders': 'الطلبات المعلقة',
        'admin_login_prompt': 'يرجى إدخال كلمة المرور:',
        'order_processing': '⚙️ جاري معالجة طلبك الآن من قبل الأدمن...',
        'order_success': '✅ تم إنجاز طلبك بنجاح! تم إرسال تفاصيل البروكسي إليك.',
        'order_failed': '❌ تم رفض طلبك. يرجى التحقق من إثبات الدفع والمحاولة مرة أخرى.',
        'about_bot': """🤖 حول البوت

📦 بوت بيع البروكسي وإدارة البروكسي
🔢 الإصدار: 1.1.0

━━━━━━━━━━━━━━━
🧑‍💻 طُور بواسطة: Mohamad Zalaf

📞 معلومات الاتصال:
📱 تليجرام: @MohamadZalaf
📧 البريد الإلكتروني: 
   • MohamadZalaf@outlook.com
   • Mohamadzalaf2017@gmail.com

━━━━━━━━━━━━━━━
© Mohamad Zalaf 2025""",
        'proxy_quantity': '🔢 أدخل عدد البروكسيات المطلوبة\n\n📝 يجب أن يكون رقماً صحيحاً بين 1 و 99\n\nمثال: 5',
        'invalid_quantity': '❌ عدد غير صحيح!\n\n🔢 يرجى إدخال رقم صحيح بين 1 و 99 فقط\n❌ لا تستخدم فواصل أو نصوص\n\nمثال صحيح: 5\nمثال خاطئ: 2.5 أو خمسة',
        'services_info': 'هذه رسالة الخدمات الافتراضية. يمكن للإدارة تعديلها.',
        'balance_menu_buttons': ['💳 شحن رصيد', '💰 رصيدي', '👥 الإحالات', '↩️ العودة للقائمة الرئيسية'],
        'balance_menu_title': '💰 إدارة الرصيد\n\nاختر العملية المطلوبة:',
        'current_balance': '''💰 رصيدك الحالي:
        
━━━━━━━━━━━━━━━
💳 رصيد الشحن: {charged_balance:.2f} كريديت
👥 رصيد الإحالات: {referral_balance:.2f} كريديت
━━━━━━━━━━━━━━━
🔢 الرصيد الإجمالي: {total_balance:.2f} كريديت''',
        'recharge_request': '''💳 طلب شحن رصيد
        
💎 قيمة الكريديت الواحد: ${credit_price:.2f}

اختر طريقة الدفع للمتابعة:''',
        'enter_recharge_amount': '💎 أدخل قيمة المبلغ المراد شحنه بالدولار:\n\nمثال: 10',
        'invalid_recharge_amount': '❌ قيمة غير صحيحة! يرجى إدخال رقم صحيح أكبر من 0',
        'recharge_proof_request': 'يرجى إرسال إثبات الدفع (صورة فقط):',
        'recharge_order_created': '✅ تم إنشاء طلب شحن الرصيد بنجاح!\n\n🆔 معرف الطلب: {order_id}\n💰 المبلغ: ${amount:.2f}\n💎 الكريديتات المتوقعة: {points:.2f} كريديت\n\n📋 سيقوم الأدمن بمراجعة الطلب',
        'orders_menu_title': '📋 إدارة الطلبات\nاختر العملية المطلوبة:',
        'orders_menu_buttons': ['📋 الطلبات المعلقة', '🔍 استعلام عن طلب', '🗑️ حذف الطلبات المعالجة', '🗑️ حذف جميع الطلبات', '🔙 العودة للقائمة الرئيسية'],
        'money_menu_title': '💰 إدارة الأموال\nاختر العملية المطلوبة:',
        'money_menu_buttons': ['📊 إحصائيات المبيعات', '📱 إحصائيات NonVoipUsNumber', '💲 إدارة الأسعار', '🔙 العودة للقائمة الرئيسية'],
        'referrals_menu_title': '👥 الإحالات\nاختر العملية المطلوبة:',
        'referrals_menu_buttons': ['💵 تحديد مبلغ الإحالة', '📊 إحصائيات المستخدمين', '🗑️ إعادة تعيين رصيد المستخدم', '🔙 العودة للقائمة الرئيسية'],
        'settings_menu_title': '⚙️ الإعدادات\nاختر العملية المطلوبة:',
        'settings_menu_buttons': ['🌐 تغيير اللغة', '🔐 تغيير كلمة المرور', '🔔 إدارة الإشعارات', '📝 تحرير رسالة الخدمات', '💱 تحرير رسالة سعر الصرف', '📜 تعديل رسالة الشروط والأحكام', '🗃️ إدارة قاعدة البيانات', '🔙 العودة للقائمة الرئيسية'],
        'back_to_main': '🔙 العودة للقائمة الرئيسية'
    },
    'en': {
        'welcome': """✨ ━━━━━━━━━━━━━━━ ✨

🌟 Welcome to Static_Bot 🌟

✨ ━━━━━━━━━━━━━━━ ✨

💎 Best Professional Proxy Services 💎

🚀 Choose the required service from the buttons below:""",
        'static_package': """📦 Static Proxy Package

━━━━━━━━━━━━━━━
📋 After selecting service:
✅ Admin will receive your order
⚡ We'll process and send you the proxy
📬 You'll get confirmation when ready

Order ID: {order_id}""",
        'socks_package': """📦 SOCKS Proxy Package
🌍 All Countries | State & Provider Selection

🔹 Available Prices:
• Single Proxy: {single_price}$
• Two Proxies: {double_price}$  
• 5 Daily Proxies Package: {five_price}$
• 10 Daily Proxies Package: {ten_price}$

━━━━━━━━━━━━━━━
📋 After selecting service:
✅ Admin will receive your order
⚡ We'll process and send you the proxy
📬 You'll get confirmation when ready

Order ID: {order_id}""",
        'select_country': 'Select Country:',
        'select_state': 'Select State:',
        'payment_methods': 'Choose payment method:',
        'send_payment_proof': 'Please send payment proof (image only):',
        'order_received': '✅ Your order has been received successfully!\n\n📋 Admin will process it manually soon.\n\n📧 You will receive status updates automatically.',
        'main_menu_buttons': ['🔒 Request Static Proxy', '📡 Request Socks Proxy', '🎁 Free Static Trial', '💰 Balance', '📋 My Orders', '⚙️ Settings', '📱 Non-VoIP Numbers', '💱 Exchange Rate', '📖 About Our Services'],
        'admin_main_buttons': ['📋 Manage Orders', '💰 Manage Money', '👥 Referrals', '📢 Broadcast', '⚙️ Settings'],
        'change_password': 'Change Password',
        'password_changed': 'Password changed successfully ✅',
        'invalid_password': 'Invalid password!',
        'enter_new_password': 'Please enter new password:',
        'withdrawal_processing': 'Your withdrawal request is being processed by admin...',
        'admin_contact': 'Admin will contact you soon to deliver your reward.',
        'language_change_success': 'Language changed to English ✅\nPlease use /start command to reload menus',
        'admin_panel': '🔧 Admin Panel',
        'manage_orders': 'Manage Orders',
        'pending_orders': 'Pending Orders',
        'admin_login_prompt': 'Please enter password:',
        'order_processing': '⚙️ Your order is now being processed by admin...',
        'order_success': '✅ Your order has been completed successfully! Proxy details have been sent to you.',
        'order_failed': '❌ Your order has been rejected. Please check your payment proof and try again.',
        'about_bot': """🤖 About Bot

📦 Proxy Sales & Management Bot
🔢 Version: 1.1.0

━━━━━━━━━━━━━━━
🧑‍💻 Developed by: Mohamad Zalaf

📞 Contact Information:
📱 Telegram: @MohamadZalaf
📧 Email: 
   • MohamadZalaf@outlook.com
   • Mohamadzalaf2017@gmail.com

━━━━━━━━━━━━━━━
© Mohamad Zalaf 2025""",
        'proxy_quantity': '🔢 Enter the number of proxies needed\n\n📝 Must be a whole number between 1 and 99\n\nExample: 5',
        'invalid_quantity': '❌ Invalid number!\n\n🔢 Please enter a whole number between 1 and 99 only\n❌ Don\'t use decimals or text\n\nCorrect example: 5\nWrong example: 2.5 or five',
        'services_info': 'This is the default services message. Admin can modify it.',
        'balance_menu_buttons': ['💳 Recharge Balance', '💰 My Balance', '👥 Referrals', '↩️ Back to Main Menu'],
        'balance_menu_title': '💰 Balance Management\n\nChoose the required operation:',
        'current_balance': '''💰 Your Current Balance:
        
━━━━━━━━━━━━━━━
💳 Charged Balance: {charged_balance:.2f} credits
👥 Referral Balance: {referral_balance:.2f} credits
━━━━━━━━━━━━━━━
🔢 Total Balance: {total_balance:.2f} credits''',
        'recharge_request': '''💳 Balance Recharge Request
        
💎 Credit Price: ${credit_price:.2f} per credit

Choose payment method to continue:''',
        'enter_recharge_amount': '💎 Enter the amount to recharge in USD:\n\nExample: 10',
        'invalid_recharge_amount': '❌ Invalid amount! Please enter a valid number greater than 0',
        'recharge_proof_request': 'Please send payment proof (image only):',
        'recharge_order_created': '✅ Balance recharge request created successfully!\n\n🆔 Order ID: {order_id}\n💰 Amount: ${amount:.2f}\n💎 Expected Credits: {points:.2f} credits\n\n📋 Admin will review the request',
        'orders_menu_title': '📋 Manage Orders\nChoose the required operation:',
        'orders_menu_buttons': ['📋 Pending Orders', '🔍 Order Inquiry', '🗑️ Delete Processed Orders', '🗑️ Delete All Orders', '🔙 Back to Main Menu'],
        'money_menu_title': '💰 Manage Finances\nChoose the required operation:',
        'money_menu_buttons': ['📊 Sales Statistics', '📱 NonVoipUsNumber Statistics', '💲 Manage Prices', '🔙 Back to Main Menu'],
        'referrals_menu_title': '👥 Referrals\nChoose the required operation:',
        'referrals_menu_buttons': ['💵 Set Referral Amount', '📊 User Statistics', '🗑️ Reset User Balance', '🔙 Back to Main Menu'],
        'settings_menu_title': '⚙️ Settings\nChoose the required operation:',
        'settings_menu_buttons': ['🌐 Change Language', '🔐 Change Password', '🔔 Manage Notifications', '📝 Edit Services Message', '💱 Edit Exchange Rate Message', '📜 Edit Terms and Conditions', '🗃️ Database Management', '🔙 Back to Main Menu'],
        'back_to_main': '🔙 Back to Main Menu'
    }
}


# ============================================
# 📍 قسم 9: نظام الأسئلة الشائعة (FAQ)
# ============================================

def init_faq_database():
    """إنشاء جدول الأسئلة الشائعة في قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faq_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            question_ar TEXT NOT NULL,
            question_en TEXT NOT NULL,
            answer_ar TEXT NOT NULL,
            answer_en TEXT NOT NULL,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ تم إنشاء جدول faq_content بنجاح")


def insert_faq_content():
    """إدراج محتوى الأسئلة الشائعة في قاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM faq_content")
    
    faq_data = [
        (
            "bot_function",
            "ما وظيفة هذا البوت؟",
            "What is this bot's function?",
            """🤖 **وظيفة البوت**

نحن نوفر لك منصة متكاملة للحصول على:

✅ **أرقام افتراضية** من آلاف الخدمات العالمية
✅ **بروكسي عالي الجودة** (Static, SOCKS, Premium Residential)

🎯 **المميزات:**
• أسعار تنافسية لا تقبل المنافسة
• خدمة سريعة وموثوقة 24/7
• دعم فني متخصص لكل خدمة
• واجهة سهلة الاستخدام""",
            """🤖 **Bot Function**

We provide you with an integrated platform to get:

✅ **Virtual Numbers** from thousands of global services
✅ **High-Quality Proxies** (Static, SOCKS, Premium Residential)

🎯 **Features:**
• Unbeatable competitive prices
• Fast and reliable 24/7 service
• Specialized technical support for each service
• Easy-to-use interface""",
            1
        ),
        (
            "balance_recharge",
            "كيف أشحن رصيدي؟",
            "How do I recharge my balance?",
            """💰 **شحن الرصيد والأموال**

**طرق الدفع المتوفرة:**
• تحويل بنكي
• محافظ إلكترونية
• عملات رقمية (حسب التوفر)

⚠️ **ملاحظات هامة:**
• الشحن يدوي (يتم بواسطة فريقنا)
• نحن محدودو المسؤولية
• **لا يتم إعادة الأموال** في معظم الحالات
• لا يتم إعادة المنتجات مقابل استرداد الأموال

📋 **للمزيد من التفاصيل:** راجع /terms

**خطوات الشحن:**
1️⃣ اختر طريقة الدفع المناسبة
2️⃣ قم بالتحويل للحساب المحدد
3️⃣ أرسل إثبات الدفع للدعم
4️⃣ انتظر التأكيد (عادة خلال ساعات)
5️⃣ سيتم إضافة الرصيد تلقائياً

🔔 **مدة المعالجة:** 1-24 ساعة عمل""",
            """💰 **Balance Recharge**

**Available Payment Methods:**
• Bank Transfer
• E-Wallets
• Cryptocurrencies (subject to availability)

⚠️ **Important Notes:**
• Manual recharge (processed by our team)
• We have limited liability
• **No refunds** in most cases
• Products cannot be returned for refund

📋 **For more details:** See /terms

**Recharge Steps:**
1️⃣ Choose your preferred payment method
2️⃣ Transfer to the specified account
3️⃣ Send payment proof to support
4️⃣ Wait for confirmation (usually within hours)
5️⃣ Balance will be added automatically

🔔 **Processing Time:** 1-24 business hours""",
            2
        ),
        (
            "buy_static_proxy",
            "كيف أشتري بروكسي ستاتيك؟",
            "How do I buy Static Proxy?",
            """🌐 **شراء بروكسي ستاتيك**

**المميزات:**
✨ أفضل جودة من بين آلاف المصادر
💎 أقل تكلفة للزبون
⚡ سرعة عالية واستقرار ممتاز
🔒 خصوصية وأمان كاملين

**خطوات الشراء:**
1️⃣ اختر "🌐 شراء بروكسي"
2️⃣ حدد النوع "Static Proxy"
3️⃣ اختر الدولة المطلوبة
4️⃣ حدد الكمية
5️⃣ أكد الطلب والدفع
6️⃣ استلم البروكسي فوراً

💡 **نصيحة:** نوفر أفضل الأسعار مع جودة لا تضاهى!""",
            """🌐 **Buy Static Proxy**

**Features:**
✨ Best quality from thousands of sources
💎 Lowest cost for customers
⚡ High speed and excellent stability
🔒 Complete privacy and security

**Purchase Steps:**
1️⃣ Choose "🌐 Buy Proxy"
2️⃣ Select type "Static Proxy"
3️⃣ Choose desired country
4️⃣ Set quantity
5️⃣ Confirm order and payment
6️⃣ Receive proxy instantly

💡 **Tip:** We offer the best prices with unmatched quality!""",
            3
        ),
        (
            "buy_socks",
            "كيف أشتري SOCKS؟",
            "How do I buy SOCKS?",
            """🧦 **شراء SOCKS Proxy**

**المميزات:**
⚡ أداء عالي وسرعة فائقة
🌍 تغطية عالمية واسعة
💰 أسعار تنافسية جداً
🔐 حماية قصوى للخصوصية

**خطوات الشراء:**
1️⃣ اختر "🌐 شراء بروكسي"
2️⃣ حدد النوع "SOCKS"
3️⃣ اختر الدولة
4️⃣ حدد الكمية المطلوبة
5️⃣ أكد وادفع
6️⃣ استلم الخدمة فوراً

🎯 **الجودة:** نقدم أفضل SOCKS بأقل الأسعار في السوق!""",
            """🧦 **Buy SOCKS Proxy**

**Features:**
⚡ High performance and super speed
🌍 Wide global coverage
💰 Very competitive prices
🔐 Maximum privacy protection

**Purchase Steps:**
1️⃣ Choose "🌐 Buy Proxy"
2️⃣ Select type "SOCKS"
3️⃣ Choose country
4️⃣ Set desired quantity
5️⃣ Confirm and pay
6️⃣ Receive service instantly

🎯 **Quality:** We provide the best SOCKS at the lowest market prices!""",
            4
        ),
        (
            "why_choose_us",
            "لماذا أختار هذا البوت؟",
            "Why choose this bot?",
            """⭐ **لماذا تختارنا؟**

نحن الخيار الأمثل لأننا نقدم:

🏆 **أفضل الأسعار:**
• أقل من المنافسين بنسبة تصل لـ 40%
• عروض وخصومات مستمرة
• لا رسوم خفية

⚡ **خدمة فورية:**
• استلام فوري للأرقام والبروكسي
• دعم فني سريع ومتخصص
• متوفرون 24/7

🌟 **جودة عالية:**
• أفضل مصادر البروكسي عالمياً
• آلاف الخدمات للأرقام الافتراضية
• نسبة نجاح عالية جداً

🔒 **أمان وخصوصية:**
• حماية كاملة لبياناتك
• لا نحفظ معلومات حساسة
• سرية تامة في جميع المعاملات

💎 **موثوقية:**
• سنوات من الخبرة
• آلاف العملاء الراضين
• سمعة ممتازة في السوق

💬 **نحن هنا لخدمتك!**""",
            """⭐ **Why Choose Us?**

We are the best choice because we offer:

🏆 **Best Prices:**
• Up to 40% cheaper than competitors
• Continuous offers and discounts
• No hidden fees

⚡ **Instant Service:**
• Immediate number and proxy delivery
• Fast specialized technical support
• Available 24/7

🌟 **High Quality:**
• Best proxy sources globally
• Thousands of virtual number services
• Very high success rate

🔒 **Security & Privacy:**
• Complete data protection
• No sensitive information stored
• Total confidentiality in all transactions

💎 **Reliability:**
• Years of experience
• Thousands of satisfied customers
• Excellent market reputation

💬 **We are here to serve you!**""",
            5
        ),
        (
            "developer",
            "من هو المطور؟",
            "Who is the developer?",
            """👨‍💻 **معلومات المطور**

للمزيد من المعلومات عن البوت والفريق، استخدم الأمر:

/about

ستجد هناك:
• معلومات مفصلة عن الخدمات
• طرق التواصل مع الفريق
• تاريخ التطوير
• الرؤية المستقبلية

📧 **للاستفسارات والدعم الفني:**
تواصل معنا عبر الأوامر الموجودة في /help""",
            """👨‍💻 **Developer Information**

For more information about the bot and team, use the command:

/about

You will find there:
• Detailed service information
• Team contact methods
• Development history
• Future vision

📧 **For inquiries and technical support:**
Contact us via commands in /help""",
            6
        )
    ]
    
    cursor.executemany("""
        INSERT INTO faq_content 
        (category, question_ar, question_en, answer_ar, answer_en, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, faq_data)
    
    conn.commit()
    conn.close()
    logger.info(f"✅ تم إدراج {len(faq_data)} سؤال في قاعدة البيانات")


def get_user_language(user_id: int) -> str:
    """الحصول على لغة المستخدم من قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'ar'
    except Exception as e:
        logger.error(f"خطأ في جلب لغة المستخدم: {e}")
        return 'ar'


def get_faq_questions(language: str = 'ar') -> List[Tuple[int, str]]:
    """جلب جميع الأسئلة الشائعة"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        question_col = 'question_ar' if language == 'ar' else 'question_en'
        cursor.execute(f"SELECT id, {question_col} FROM faq_content ORDER BY display_order")
        
        questions = cursor.fetchall()
        conn.close()
        return questions
    except Exception as e:
        logger.error(f"خطأ في جلب الأسئلة: {e}")
        return []


def get_faq_answer(faq_id: int, language: str = 'ar') -> Optional[str]:
    """جلب إجابة سؤال معين"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        answer_col = 'answer_ar' if language == 'ar' else 'answer_en'
        cursor.execute(f"SELECT {answer_col} FROM faq_content WHERE id = ?", (faq_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"خطأ في جلب الإجابة: {e}")
        return None


async def show_faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الأسئلة الشائعة"""
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    questions = get_faq_questions(language)
    
    if not questions:
        init_faq_database()
        insert_faq_content()
        questions = get_faq_questions(language)
    
    keyboard = []
    for faq_id, question in questions:
        keyboard.append([InlineKeyboardButton(question, callback_data=f"faq_{faq_id}")])
    
    back_text = "🔙 العودة" if language == 'ar' else "🔙 Back"
    keyboard.append([InlineKeyboardButton(back_text, callback_data="back_to_main")])
    
    title = "❓ الأسئلة الشائعة" if language == 'ar' else "❓ FAQ"
    subtitle = "اختر سؤالاً للاطلاع على الإجابة:" if language == 'ar' else "Choose a question to see the answer:"
    
    message_text = f"{title}\n\n{subtitle}"
    
    query = update.callback_query
    if query:
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغط زر سؤال FAQ"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    language = get_user_language(user_id)
    
    faq_id = int(query.data.replace("faq_", ""))
    answer = get_faq_answer(faq_id, language)
    
    if answer:
        back_text = "🔙 العودة للأسئلة" if language == 'ar' else "🔙 Back to FAQ"
        keyboard = [[InlineKeyboardButton(back_text, callback_data="show_faq")]]
        
        await query.edit_message_text(
            text=answer,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        error_text = "❌ عذراً، لم يتم العثور على الإجابة." if language == 'ar' else "❌ Sorry, answer not found."
        await query.edit_message_text(text=error_text)


def setup_faq_system():
    """تهيئة نظام الأسئلة الشائعة"""
    try:
        init_faq_database()
        
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM faq_content")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            insert_faq_content()
            
        logger.info("✅ تم تهيئة نظام FAQ بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة نظام FAQ: {e}")


# ============================================
# 📍 قسم 10: دوال مساعدة للوصول للقواميس
# ============================================

def get_country_name(country_code: str, language: str = 'ar', proxy_type: str = 'static') -> str:
    """الحصول على اسم الدولة حسب الكود واللغة ونوع البروكسي"""
    if proxy_type == 'static':
        countries = STATIC_COUNTRIES
    else:
        countries = SOCKS_COUNTRIES
    
    return countries.get(language, {}).get(country_code, country_code)


def get_state_name(state_code: str, language: str = 'ar', country: str = 'US') -> str:
    """الحصول على اسم الولاية حسب الكود واللغة"""
    states = US_STATES_SOCKS if country == 'US' else UK_STATES
    return states.get(language, {}).get(state_code, state_code)


def get_message(key: str, language: str = 'ar', **kwargs) -> str:
    """الحصول على رسالة من قاموس الرسائل مع إمكانية التنسيق"""
    message = MESSAGES.get(language, MESSAGES['ar']).get(key, '')
    if kwargs and message:
        try:
            return message.format(**kwargs)
        except KeyError:
            return message
    return message


def get_all_country_codes(proxy_type: str = 'static') -> list:
    """الحصول على جميع أكواد الدول المتاحة"""
    if proxy_type == 'static':
        return list(STATIC_COUNTRIES.get('en', {}).keys())
    else:
        return list(SOCKS_COUNTRIES.get('en', {}).keys())


def get_all_us_state_codes() -> list:
    """الحصول على جميع أكواد الولايات الأمريكية"""
    return list(US_STATES_SOCKS.get('en', {}).keys())


def load_admin_ids() -> list:
    """
    تحميل قائمة معرفات المسؤولين
    Load list of admin IDs
    
    Returns:
        list: قائمة معرفات المسؤولين
    """
    return Config.ADMIN_IDS if hasattr(Config, 'ADMIN_IDS') else []


# التحقق من صحة الإعدادات عند استيراد الملف
if __name__ != "__main__":
    Config.validate()
