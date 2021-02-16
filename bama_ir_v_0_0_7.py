# فراخوانی کتاب‌خانه‌ها
import requests
import re
import html
import mysql.connector

# تعریف تابع جهت انتخاب از بین گزینه‌ها (برند و مدل اتومبیل‌ها)
def selection(list, item):
    print(f'{item} موردنظر خود را از فهرست زیر انتخاب و شماره‌ی ردیف آن را وارد نمایید: ')
    for row, name in enumerate(list, 1):
        print(f'{row}: {name[1]}')
    selected_row = int(input()) -1
    selection = list[selected_row][0]
    return selection

# تابع جهت استخراج برند و مدل ماشین‌ها از سایت باما
def scraping(url, regex):
    result = []
    page = requests.get(url)
    page_html = page.text
    page_regexed = re.findall(regex, page_html)
    for item in page_regexed:
        result.append([html.unescape(item[0]), html.unescape(item[1])])
    return result

# جهت استخراج پیشنهادهای ارائه شده: حذف موارد فاقد قیمت یا فاقد کارکرد (موارد دارای کارکرد صفر حذف نشده‌اند) در صورتی که موارد مفید به ۲۰ نرسیده باشد یک‌صفحه‌ی دیگر بررسی می‌شود
def offers_scraping(url, regex, limit=None):
    done_flag = False
    cpage = 1
    result = []
    while not done_flag:
        page = requests.get(url)
        page_html = page.text
        page_regexed = re.findall(regex, page_html)
        for item in page_regexed:
            result_item = []
            price_flag = False
            odometer_flag = False
            odometer = html.unescape(item[0])
            price = html.unescape(item[1])
            if re.search(r'کارکرد .* کیلومتر', odometer):
                odometer = re.findall(r'کارکرد (.*) کیلومتر', odometer)[0]
                if odometer == 'صفر':
                    odometer = '0'
                odometer_flag = True
                result_item.append(odometer)
            if price == '0':
                price_flag = False
            else:
                price_flag = True
                result_item.append(price)
            if odometer_flag and price_flag:
                result.append(result_item)
        if not limit:
            done_flag = True
            return result
        else:
            if len(result) < limit:
                url += ('/?page=' + str(cpage+1))
                cpage += 1
            else:
                done_flag = True
                return result

# تعریف regex و فراخوانی تابع جهت استخراج نام و لینک برندها
brands_regex = r'<a href=\"\/car\/(.*)\" onclick=\"return false;\" onmousedown=\"onmouseDownBrand\(\'.*\',\'\d*\',event\);\">\s*<span class=\"home-brand-model-title nav-sub-brand-name-show-text\">(.*)<\/span>'
list_of_brands = scraping('https://bama.ir/', brands_regex)
brand_url = selection(list_of_brands, 'برند')

# تعریف regex و فراخوانی تابع جهت استخراج نام و لینک مدل‌ها
models_regex = r'<a href=\"\/car\/' + re.escape(brand_url) + r'\/([^"]*)\"[\s\S]*?home-brand-model-title\">(.*)<\/span>'
list_of_models = scraping(f'https://bama.ir/', models_regex)
model_url = selection(list_of_models, 'مدل')

# تعریف regex و فراخوانی تابع جهت استخراج پیشنهادها
offer_regex = r'<p class=\"price hidden-xs\">(.*)?<\/p>[\s\S]*?<span itemprop=\"price\" content=\"([\d]*)\">'
list_of_offers = offers_scraping(f'https://bama.ir/car/{brand_url}/{model_url}', offer_regex, 140)

# ایجاد پایگاه‌داده bama_ir و بستن اتصال
connection = mysql.connector.connect(user='user', password='password', host='127.0.0.1')
cursor = connection.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS bama_ir;")
connection.commit()
connection.close()

# ایجاد جدول odometer_price و بستن اتصال
connection = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='bama_ir')
cursor = connection.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS odometer_price (brand TEXT, model TEXT, odometer BIGINT, price BIGINT);")
connection.commit()
connection.close()

# به تعداد ۲۰ عدد پیشنهاد اتصال به پایگاه داده و پایگاه از پیش موجود و وارد کردن اطلاعات گرفته شده
for offer in list_of_offers[:140]:
    odometer = int(''.join(re.findall(r'(\d+)', offer[0])))
    price = offer[1]
    connection = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='bama_ir')
    cursor = connection.cursor()
    cursor.execute(f"INSERT INTO odometer_price VALUES ('{brand_url}', '{model_url}', '{odometer}', '{price}');")
    connection.commit()
    connection.close()
