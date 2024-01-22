import os
import argparse
import time
import json
import random
import requests
import traceback
import yaml
from datetime import datetime
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.core.http import HttpClient
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.download_manager import WDMDownloadManager
from requests import Response
import urllib3
# from selenium.common.exceptions import NoSuchElementException
from telethon import TelegramClient, events
from embassy import embassies

os.environ['WDM_SSL_VERIFY'] = '0'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

os.environ['TZ'] = config['time']['time_zone']
time.tzset()

download_proxy_str = None
if config['download_proxy']:
    download_proxy_str = f"{config['download_proxy']['proxy_type']}://{config['download_proxy']['addr']}:{config['download_proxy']['port']}"
download_proxies = {"http": download_proxy_str, "https": download_proxy_str}
connection_proxy_str = None
if config['connection_proxy']:
    connection_proxy_str = f"{config['connection_proxy']['proxy_type']}://{config['connection_proxy']['addr']}:{config['connection_proxy']['port']}"
connection_proxies = {"http": connection_proxy_str, "https": connection_proxy_str}

# Time Section:
minute = 60
hour = 60 * minute

def get_embassy_info(embassy):
    return embassies[embassy]

def get_links_for_embassy(user_config):
    schedule_id = user_config['schedule_id']
    group_id = user_config['group_id']
    embassy_info = get_embassy_info(user_config['embassy'])
    country_code = embassy_info['country_code']
    facility_id = embassy_info['facility_id']
    return {
        'sign_in_link': f"https://ais.usvisa-info.com/{country_code}/niv/users/sign_in",
        'appointment_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment",
        'payment_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/payment",
        'date_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment/days/{facility_id}.json?appointments[expedite]=false",
        'time_url': f"https://ais.usvisa-info.com/{country_code}/niv/schedule/{schedule_id}/appointment/times/{facility_id}.json?date=%s&appointments[expedite]=false",
        'sign_out_link': f"https://ais.usvisa-info.com/{country_code}/niv/users/sign_out",
        'group_link': f"https://ais.usvisa-info.com/{country_code}/niv/groups/{group_id}",
    }

JS_SCRIPT = ("var req = new XMLHttpRequest();"
             f"req.open('GET', '%s', false);"
             "req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');"
             "req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');"
             f"req.setRequestHeader('Cookie', '_yatri_session=%s');"
             "req.send(null);"
             "return req.responseText;")

def send_debug_notification(msg):
    if config['telegram']['debug_chat_id']:
        data = {
            'chat_id': config['telegram']['debug_chat_id'],
            'text': msg,
        }
        token = config['telegram']['bot_token']
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        print(f"Sending debug notification {data}")
        requests.post(url, data, proxies=connection_proxies)

def send_notification(msg):
    data = {
        'chat_id': config['telegram']['chat_id'],
        'text': msg,
    }
    token = config['telegram']['bot_token']
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    print(f"Sending notification {data}")
    requests.post(url, data, proxies=connection_proxies)


def auto_action(label, find_by, el_type, action, value, sleep_time=0):
    print("\t"+ label +":", end="")
    match find_by.lower():
        case 'id':
            item = driver.find_element(By.ID, el_type)
        case 'name':
            item = driver.find_element(By.NAME, el_type)
        case 'class':
            item = driver.find_element(By.CLASS_NAME, el_type)
        case 'xpath':
            item = driver.find_element(By.XPATH, el_type)
        case _:
            return 0
    # Do Action:
    match action.lower():
        case 'send':
            item.send_keys(value)
        case 'click':
            item.click()
        case _:
            return 0
    print("\t\tCheck!")
    if sleep_time:
        time.sleep(sleep_time)


def start_process(user_config, embassy_links):
    # Bypass reCAPTCHA
    driver.get(embassy_links['sign_in_link'])
    time.sleep(config['time']['step_time'])
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", config['time']['step_time'])
    auto_action("Email", "id", "user_email", "send", user_config['email'], config['time']['step_time'])
    auto_action("Password", "id", "user_password", "send", user_config['password'], config['time']['step_time'])
    auto_action("Privacy", "class", "icheckbox", "click", "", config['time']['step_time'])
    auto_action("Enter Panel", "name", "commit", "click", "", config['time']['step_time'])
    Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), '" + get_embassy_info(user_config['embassy'])['regex_continue'] + "')]")))
    print("\n\tlogin successful!\n")

def reschedule(date, user_config, embassy_links):
    time = get_time(date, embassy_links)
    driver.get(embassy_links['appointment_url'])
    try:
        btn = driver.find_element(By.XPATH, '//*[@id="main"]/div[3]/form/div[2]/div/input')
        btn.click()
        print("multiple applicants.")
    except:
        print("single applicants.")
    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": embassy_links['appointment_url'],
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }
    data = {
        "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": get_embassy_info(user_config['embassy'])['facility_id'],
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }
    r = requests.post(embassy_links['appointment_url'], headers=headers, data=data)
    if r.status_code == 200:
        success = True
        msg = f"Rescheduled Successfully! Account: {user_config['email']}, {date} {time}"
    else:
        success = False
        msg = f"Reschedule Failed! Account: {user_config['email']}, {date} {time}"
    return [success, msg]


def get_all_available(embassy_links):
    # Requesting to get the whole available dates
    session = driver.get_cookie("_yatri_session")["value"]
    script = JS_SCRIPT % (embassy_links['date_url'], session)
    content = driver.execute_script(script)
    return json.loads(content)

def get_time(date, embassy_links):
    time_url = embassy_links['time_url'] % date
    session = driver.get_cookie("_yatri_session")["value"]
    script = JS_SCRIPT % (str(time_url), session)
    content = driver.execute_script(script)
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time

def get_current_appointment_date(user_config, embassy_links):
    driver.get(embassy_links['group_link'])
    elements = driver.find_elements(by=By.CLASS_NAME, value="consular-appt")
    if not elements:
        return datetime.strptime(user_config['period_end'], "%Y-%m-%d").date()
    date_str = ' '.join(elements[0].text.split(' ')[2:5])
    return datetime.strptime(date_str, '%d %B, %Y,').date()

def is_in_period(date, start, end):
    return (end > date and date >= start)

def get_accepted_date(dates, user_config, current_appointment_date):
    end_date = datetime.strptime(user_config['period_end'], "%Y-%m-%d").date()
    if current_appointment_date:
        end_date = min(end_date, current_appointment_date)
    start_date = datetime.strptime(user_config['period_start'], "%Y-%m-%d").date()
    for d in dates:
        date = d.get('date')
        if is_in_period(datetime.strptime(date, "%Y-%m-%d").date(), start_date, end_date):
            return date
    print(f"\n\nNo available dates between ({start_date}) and ({end_date})!")
    return None


def info_logger(file_path, log):
    with open(file_path, "a") as file:
        file.write(str(datetime.now().time()) + ":\n" + log + "\n")

## Change this function based on your target telegram channel
def get_date_from_telegram_message(message):
    if 'First Available Appointment' in message.text:
        text = re.split(' |\n', message.text)
        for i, element in enumerate(text):
            if str(datetime.now().year) in element or str(datetime.now().year+1) in element:
                return datetime.strptime(f'{text[i-2]} {text[i-1]} {text[i]}', '%d %B %Y').date()
    return None

class CustomHttpClient(HttpClient):
    def get(self, url, params=None) -> Response:
        return requests.get(url, params, verify=False, proxies=download_proxies)

if config['chrome_driver']['local_use']:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if config['connection_proxy']:
        options.add_argument(f"--proxy-server=\"{connection_proxy_str}\"")
    http_client = CustomHttpClient()
    download_manager = WDMDownloadManager(http_client)
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(download_manager=download_manager).install()), options=options)
else:
    driver = webdriver.Remote(command_executor=config['chrome_driver']['hub_address'], options=webdriver.ChromeOptions())

tele_client = TelegramClient(config['telegram']['session'], config['telegram']['api_id'], config['telegram']['api_hash'], proxy=config['connection_proxy']).start(phone=config['telegram']['phone_number'])
    
@tele_client.on(events.NewMessage(chats=[config['telegram']['channel_id']]))
async def handler(event):
    try:
        new_date = get_date_from_telegram_message(event)
        if new_date is None:
            msg = 'New message received but found no date.\n'
            msg += f'Message: {event.text}'
            print(msg)
            send_debug_notification(msg)
        else:
            msg = f'Found new date from channel: {new_date}.'
            print(msg)
            send_debug_notification(msg)
            for user_config in config['users']:
                if is_in_period(new_date, datetime.strptime(user_config['period_start'], "%Y-%m-%d").date() , datetime.strptime(user_config['period_end'], "%Y-%m-%d").date()):
                    send_notification(msg)
                    embassy_links = get_links_for_embassy(user_config)
                    start_process(user_config, embassy_links)
                    current_appointment_date = get_current_appointment_date(user_config, embassy_links)
                    available_dates = get_all_available(embassy_links)
                    if not available_dates:
                        print(f"Probably user {user_config['email']} is banned.")
                        msg = f"User {user_config['email']} got banned. Ban time: {datetime.now()}"
                        print(msg)
                        current_date = str(datetime.now().date())
                        log_file_name = f"log_{current_date}.txt"
                        info_logger(log_file_name, msg)
                        send_debug_notification(msg)
                        driver.get(embassy_links['sign_out_link'])
                        continue
                    msg = ""
                    for d in available_dates:
                        msg = msg + "%s" % (d.get('date')) + ", "
                    print(f'Available dates for user: {user_config["email"]}:\n {msg[:-2]}')
                    accepted_date = get_accepted_date(available_dates, user_config, current_appointment_date)
                    if accepted_date:
                        _ , msg = reschedule(accepted_date, user_config, embassy_links)
                        send_notification(msg)
                    driver.get(embassy_links['sign_out_link'])
    except:
        print(f"Exception occured!")
        traceback.print_exc()
        formatted_lines = traceback.format_exc().splitlines()
        msg = formatted_lines[0] + '\n' + formatted_lines[-1]
        send_debug_notification(msg)
        
        
if __name__ == "__main__":
    msg = 'Started workings!'
    print(msg)
    send_debug_notification(msg)
    tele_client.run_until_disconnected()
