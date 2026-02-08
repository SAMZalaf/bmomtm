Luxury Support:
🔐 API key for user 8491106530:
Bearer: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NDkxMTA2NTMwIiwiZXhwIjoxODEyNTU3MDA3fQ.j1nNqJinrSqOdQ_DepE8iPH8gdI-iK6HBhaPMvi3owE

http://165.22.199.159:3536/docs#





FastAPI
 0.1.0 
OAS 3.1
/openapi.json

Authorize
v1


GET
/api/v1/socks/proxy
Proxy Counts


Retrieve proxy counts by continent.

Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_country
Get Country List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_state
Get State List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_city
Get City List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_zip
Get Zip List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_isp
Get Isp List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/search
Search Proxy


Parameters
Try it out
Name	Description
ip
string | (string | null)
(query)
Search by IP address

ip
limit
integer
(query)
Number of proxies to return

Default value : 10

10
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
page
integer
(query)
Page number for pagination

Default value : 0

0
radius
integer | (integer | null)
(query)
Radius for proximity searches

radius
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/check_ip
Check Ip


Parameters
Try it out
Name	Description
proxy_id *
string
(query)
proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

POST
/api/v1/socks/buy
Buy


Buy proxy by proxy_id

If daily_buy is True, a 24-hour proxy will be purchased, and the IP address can be changed. If daily_buy is False, a 4-hour proxy will be purchased, and the IP address cannot be changed.

By default, daily_buy is True.

Parameters
Try it out
No parameters

Request body

application/json
Example Value
Schema
{
  "proxy_id": "string",
  "daily_buy": true
}
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

POST
/api/v1/socks/refund
Refund


Parameters
Try it out
No parameters

Request body

application/json
Example Value
Schema
{
  "record_id": 0
}
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/records_by_user
Get Records By User


Parameters
Try it out
Name	Description
limit *
integer
(query)
limit
page *
integer
(query)
page
record_id
any
(query)
record_id
country_code
any
(query)
country_code
real_ip
any
(query)
real_ip
state
any
(query)
state
city
any
(query)
city
isp
any
(query)
isp
zip
any
(query)
zip
proxy_id
any
(query)
proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/balance
Get Balance


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/v2/search
Search Proxy V2


Search for proxies using the provided filters.

Args: ip (str, optional): Search by IP address. limit (int, optional): Number of proxies to return. country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL'). isp (str, optional): Filter by ISP. state (str, optional): Filter by state. city (str, optional): Filter by city. zip_code (str, optional): Filter by ZIP code. page (int, optional): Page number for pagination. radius (int, optional): Radius for proximity searches.

Returns: List or Dict: The filtered list of proxies, or any structure you choose.

Parameters
Try it out
Name	Description
ip
string | (string | null)
(query)
Search by IP address

ip
limit
integer
(query)
Number of proxies to return

Default value : 10

10
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
page
integer
(query)
Page number for pagination

Default value : 1

1
radius
integer | (integer | null)
(query)
Radius for proximity searches

radius
proxy_id
string | (string | null)
(query)
Search by unique proxy id

proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_country
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_state
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
state
string | (string | null)
(query)
Filter by state

state
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_city
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
city
string | (string | null)
(query)
Filter by city.

city
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v3/search
Search Proxy V3


Search for proxies using the provided filters.

Args: ip (str, optional): Search by IP address. limit (int, optional): Number of proxies to return. country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL'). isp (str, optional): Filter by ISP. state (str, optional): Filter by state. city (str, optional): Filter by city. zip_code (str, optional): Filter by ZIP code. page (int, optional): Page number for pagination. radius (int, optional): Radius for proximity searches.

Returns: List or Dict: The filtered list of proxies, or any structure you choose.

Parameters
Try it out
Name	Description
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links
socks


GET
/api/v1/socks/proxy
Proxy Counts


Retrieve proxy counts by continent.

Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_country
Get Country List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_state
Get State List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_city
Get City List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_zip
Get Zip List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/list_isp
Get Isp List


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/search
Search Proxy


Parameters
Try it out
Name	Description
ip
string | (string | null)
(query)
Search by IP address

ip
limit
integer
(query)
Number of proxies to return

Default value : 10

10
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
page
integer
(query)
Page number for pagination

Default value : 0

0
radius
integer | (integer | null)
(query)
Radius for proximity searches

radius
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/check_ip
Check Ip


Parameters
Try it out
Name	Description
proxy_id *
string
(query)
proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

POST
/api/v1/socks/buy
Buy


Buy proxy by proxy_id

If daily_buy is True, a 24-hour proxy will be purchased, and the IP address can be changed. If daily_buy is False, a 4-hour proxy will be purchased, and the IP address cannot be changed.

By default, daily_buy is True.

Parameters
Try it out
No parameters

Request body

application/json
Example Value
Schema
{
  "proxy_id": "string",
  "daily_buy": true
}
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

POST
/api/v1/socks/refund
Refund


Parameters
Try it out
No parameters

Request body

application/json
Example Value
Schema
{
  "record_id": 0
}
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/records_by_user
Get Records By User


Parameters
Try it out
Name	Description
limit *
integer
(query)
limit
page *
integer
(query)
page
record_id
any
(query)
record_id
country_code
any
(query)
country_code
real_ip
any
(query)
real_ip
state
any
(query)
state
city
any
(query)
city
isp
any
(query)
isp
zip
any
(query)
zip
proxy_id
any
(query)
proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/balance
Get Balance


Parameters
Try it out
No parameters

Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links

GET
/api/v1/socks/v2/search
Search Proxy V2


Search for proxies using the provided filters.

Args: ip (str, optional): Search by IP address. limit (int, optional): Number of proxies to return. country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL'). isp (str, optional): Filter by ISP. state (str, optional): Filter by state. city (str, optional): Filter by city. zip_code (str, optional): Filter by ZIP code. page (int, optional): Page number for pagination. radius (int, optional): Radius for proximity searches.

Returns: List or Dict: The filtered list of proxies, or any structure you choose.

Parameters
Try it out
Name	Description
ip
string | (string | null)
(query)
Search by IP address

ip
limit
integer
(query)
Number of proxies to return

Default value : 10

10
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
page
integer
(query)
Page number for pagination

Default value : 1

1
radius
integer | (integer | null)
(query)
Radius for proximity searches

radius
proxy_id
string | (string | null)
(query)
Search by unique proxy id

proxy_id
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_country
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_state
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
state
string | (string | null)
(query)
Filter by state

state
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v2/mapp_city
Search Proxy V2


Search for proxies using the provided filters.

Args: country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL').

Returns: List or Dict: The filtered list of states.

Parameters
Try it out
Name	Description
city
string | (string | null)
(query)
Filter by city.

city
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

GET
/api/v1/socks/v3/search
Search Proxy V3


Search for proxies using the provided filters.

Args: ip (str, optional): Search by IP address. limit (int, optional): Number of proxies to return. country_code (str, optional): Country code(s) to filter by (e.g. 'IT', 'CA', 'PL'). isp (str, optional): Filter by ISP. state (str, optional): Filter by state. city (str, optional): Filter by city. zip_code (str, optional): Filter by ZIP code. page (int, optional): Page number for pagination. radius (int, optional): Radius for proximity searches.

Returns: List or Dict: The filtered list of proxies, or any structure you choose.

Parameters
Try it out
Name	Description
country_code
string | (string | null)
(query)
Country code(s) to filter by (e.g. 'IT', 'CA', 'PL')

country_code
isp
string | (string | null)
(query)
Filter by ISP

isp
state
string | (string | null)
(query)
Filter by state

state
city
string | (string | null)
(query)
Filter by city

city
zip_code
string | (string | null)
(query)
Filter by ZIP code

zip_code
Responses
Code	Description	Links
200	
Successful Response

Media type

application/json
Controls Accept header.
Example Value
Schema
"string"
No links
422	
Validation Error

Media type

application/json
Example Value
Schema
{
  "detail": [
    {
      "loc": [
        "string",
        0
      ],
      "msg": "string",
      "type": "string"
    }
  ]
}
No links

Schemas
BuyDataExpand allobject
HTTPValidationErrorExpand allobject
RefundDataExpand allobject
ValidationErrorExpand allobject










Python-telegram-bot




import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ==========================================
# إعدادات التكوين (يجب تعديلها)
# ==========================================
API_BASE_URL = "http://165.22.199.159:3536"  # ضع رابط الـ API الخاص بك هنا
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"      # ضع توكن البوت هنا
USER_API_KEY = "YOUR_BEARER_TOKEN"         # مفتاح التوثيق الخاص بالمستخدم (Bearer)

# ==========================================
# إعدادات السجل (Logging)
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==========================================
# دوال الاتصال بالـ API
# ==========================================
def api_request(method, endpoint, params=None, data=None):
    headers = {
        "Authorization": f"Bearer {USER_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        
        # إذا كانت الاستجابة ناجحة
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            return {"error": True, "status": response.status_code, "detail": response.text}
    except Exception as e:
        return {"error": True, "detail": str(e)}

# ==========================================
# معالجات الأوامر (Command Handlers)
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب والقائمة الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("💰 رصيدي", callback_data='balance')],
        [InlineKeyboardButton("🔎 بحث عن بروكسي", callback_data='search_menu')],
        [InlineKeyboardButton("📜 سجل طلباتي", callback_data='history')],
        [InlineKeyboardButton("🌍 قوائم (دول/مدن)", callback_data='lists_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 أهلاً بك في بوت خدمات SOCKS Proxy.\nاختر خدمة من القائمة أدناه:",
        reply_markup=reply_markup
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع الأزرار"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'balance':
        res = api_request("GET", "/api/v1/socks/balance")
        if "error" in res:
            text = f"❌ خطأ: {res.get('detail')}"
        else:
            # افتراض أن الرصيد يأتي في حقل 'balance' أو مشابه، حسب التوثيق الاستجابة string أحياناً
            text = f"💰 رصيدك الحالي: {res}"
        
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))

    elif data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("💰 رصيدي", callback_data='balance')],
            [InlineKeyboardButton("🔎 بحث عن بروكسي", callback_data='search_menu')],
            [InlineKeyboardButton("📜 سجل طلباتي", callback_data='history')],
            [InlineKeyboardButton("🌍 قوائم (دول/مدن)", callback_data='lists_menu')],
        ]
        await query.edit_message_text("القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'lists_menu':
        keyboard = [
            [InlineKeyboardButton("الدول المتوفرة", callback_data='list_country')],
            [InlineKeyboardButton("الولايات", callback_data='list_state')],
            [InlineKeyboardButton("مقدمي الخدمة (ISP)", callback_data='list_isp')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')],
        ]
        await query.edit_message_text("اختر القائمة التي تريد عرضها:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('list_'):
        endpoint_map = {
            'list_country': '/api/v1/socks/list_country',
            'list_state': '/api/v1/socks/list_state',
            'list_isp': '/api/v1/socks/list_isp'
        }
        endpoint = endpoint_map.get(data)
        res = api_request("GET", endpoint)
        if "error" in res:
            await query.edit_message_text(f"حدث خطأ: {res.get('detail')}")
        else:
            # عرض أول 20 نتيجة فقط لتجنب تعليق البوت
            items = res if isinstance(res, list) else []
            display_text = "\n".join([str(i) for i in items[:20]])
            await query.edit_message_text(f"أحدث النتائج:\n{display_text}\n...", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='lists_menu')]]))

    elif data == 'search_menu':
        text = (
            "🔎 **طريقة البحث**:\n\n"
            "أرسل أمر البحث بالتنسيق التالي:\n"
            "`/search US` - للبحث بكود الدولة\n"
            "`/searchip 1.1.1.1` - للبحث بـ IP معين\n"
            "`/searchstate California` - للبحث بالولاية"
        )
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))

    elif data == 'history':
        # جلب السجلات
        res = api_request("GET", "/api/v1/socks/records_by_user", params={"limit": 5, "page": 0})
        if "error" in res:
             await query.edit_message_text(f"خطأ: {res.get('detail')}")
             return

        records = res if isinstance(res, list) else res.get('items', []) # تعديل حسب هيكل الرد الفعلي
        
        if not records:
            await query.edit_message_text("لا توجد سجلات سابقة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='main_menu')]]))
            return

        for rec in records:
            # زر للاسترجاع (Refund) لكل عملية
            rec_id = rec.get('id') or rec.get('record_id')
            proxy_info = rec.get('proxy', 'Proxy Info')
            keyboard = [[InlineKeyboardButton("🔄 استرجاع (Refund)", callback_data=f"refund_{rec_id}")]]
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"📄 طلب رقم: {rec_id}\nبروكسي: {proxy_info}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith('buy_'):
        # تنسيق البيانات: buy_PROXYID
        proxy_id = data.split('_')[1]
        
        # تنفيذ الشراء
        payload = {"proxy_id": proxy_id, "daily_buy": True} # افتراض الشراء يومي
        res = api_request("POST", "/api/v1/socks/buy", data=payload)
        
        if "error" in res:
            await query.answer(f"❌ فشل الشراء: {res.get('detail')}", show_alert=True)
        else:
            await query.edit_message_text(f"✅ تم الشراء بنجاح!\nالرد: {res}")

    elif data.startswith('refund_'):
        record_id = data.split('_')[1]
        payload = {"record_id": int(record_id)}
        res = api_request("POST", "/api/v1/socks/refund", data=payload)
        
        if "error" in res:
             await query.answer(f"❌ فشل الاسترجاع: {res.get('detail')}", show_alert=True)
        else:
             await query.edit_message_text(f"✅ تم استرجاع الطلب {record_id} بنجاح.")

# ==========================================
# دوال البحث (Search Logic)
# ==========================================

async def search_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة البحث المتقدم V3"""
    query_text = update.message.text
    args = context.args
    
    if not args:
        await update.message.reply_text("⚠️ يرجى تحديد كود الدولة. مثال: `/search US`")
        return

    country_code = args[0]
    
    # استخدام الإصدار الثالث V3 كما هو في التوثيق
    params = {
        "country_code": country_code,
        "limit": 5,
        "page": 0
    }
    
    msg = await update.message.reply_text("⏳ جاري البحث...")
    res = api_request("GET", "/api/v1/socks/v3/search", params=params)
    
    if "error" in res:
        await msg.edit_text(f"❌ خطأ في البحث: {res.get('detail')}")
        return
    
    results = res if isinstance(res, list) else res.get('data', []) # يعتمد على شكل الرد JSON
    
    if not results:
        await msg.edit_text("🚫 لم يتم العثور على بروكسيات بهذا البحث.")
        return

    await msg.delete()
    
    for proxy in results:
        # استخراج البيانات (تعديل المفاتيح حسب الاستجابة الفعلية)
        p_id = proxy.get('id') or proxy.get('proxy_id')
        ip = proxy.get('ip', 'N/A')
        country = proxy.get('country_code', 'N/A')
        isp = proxy.get('isp', 'N/A')
        
        text = (
            f"🌐 **Proxy Found**\n"
            f"IP: `{ip}`\n"
            f"Country: {country}\n"
            f"ISP: {isp}\n"
        )
        
        # زر الشراء
        keyboard = [[InlineKeyboardButton("🛒 شراء (Buy)", callback_data=f"buy_{p_id}")]]
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ==========================================
# التشغيل الرئيسي
# ==========================================

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # الأوامر الأساسية
    application.add_handler(CommandHandler('start', start))
    
    # أوامر البحث
    application.add_handler(CommandHandler('search', search_proxy)) # مثال: /search US

    # معالجة الأزرار
    application.add_handler(CallbackQueryHandler(menu_callback))

    print("🤖 Bot is running...")
    application.run_polling() 