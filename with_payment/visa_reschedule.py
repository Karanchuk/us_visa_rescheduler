import os
import argparse
import time
import json
import random
import requests
import traceback
import yaml
from datetime import datetime

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
telegram_proxy_str = None
if config['telegram_proxy']:
    telegram_proxy_str = f"{config['telegram_proxy']['proxy_type']}://{config['telegram_proxy']['addr']}:{config['telegram_proxy']['port']}"
telegram_proxies = {"http": telegram_proxy_str, "https": telegram_proxy_str}
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
        requests.post(url, data, proxies=telegram_proxies)

def send_notification(msg):
    data = {
        'chat_id': config['telegram']['chat_id'],
        'text': msg,
    }
    token = config['telegram']['bot_token']
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    print(f"Sending notification {data}")
    requests.post(url, data, proxies=telegram_proxies)


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

def get_user_id():
    id = 0
    while True:
        yield id
        id = (id + 1) % len(config['users'])

def reschedule(date, user_config, embassy_links):
    appointment_time = get_time(date, embassy_links)
    driver.get(embassy_links['appointment_url'])
    try:
        warning_text_elem = driver.find_elements(by=By.XPATH, value=f'//*[@id="main"]/div[3]/div/div/div/p')
        if warning_text_elem:
            warning_text = warning_text_elem[0].text
            max_reschedule_count = int(warning_text.split("There is a maximum number of ")[1].split(" ")[0])
            print(f"max reschedule count: {max_reschedule_count}")
            remaining_reschedule_count = int(warning_text.split("You have ")[1].split(" ")[0])
            print(f"remaining reschedule count: {remaining_reschedule_count}")
            if (remaining_reschedule_count <= 1):
                success = False
                msg = f"Reschedule Failed! Maximum reschedule count reached. Account: {user_config['email']}, {date} {appointment_time}"
                return [success, msg]
        auto_action("Schedule limit checkbox", "class", "icheckbox", "click", "", config['time']['step_time'])
        auto_action("Schedule limit continue", "name", "commit", "click", "", config['time']['step_time'])
        print("passed schedule limit.")
    except:
        print("no schedule limit.")
    try:
        auto_action("Multi applicant continue", "name", "commit", "click", "", config['time']['step_time'])
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
        "appointments[consulate_appointment][time]": appointment_time,
    }
    r = requests.post(embassy_links['appointment_url'], headers=headers, data=data)
    for _ in range(config['time']['reschedule_tries']-1):
        time.sleep(3)
        requests.post(embassy_links['appointment_url'], headers=headers, data=data)
    if r.status_code == 200:
        success = True
        msg = f"Rescheduled Successfully! Account: {user_config['email']}, {date} {appointment_time}"
    else:
        success = False
        msg = f"Reschedule Failed! Account: {user_config['email']}, {date} {appointment_time}"
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

def mean(mylist: list):
    if len(mylist):
        return sum(mylist)/len(mylist)
    return 0

def std(mylist: list):
    if len(mylist):
        mean_val = mean(mylist)
        variance = sum([((x - mean_val) ** 2) for x in mylist]) / len(mylist)
        return variance ** 0.5
    return 0

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

if __name__ == "__main__":
    start_new_user = True
    get_user = get_user_id()
    previous_date = str(datetime.now().date())
    current_appointment_date = None
    ban_retry_count = 0
    exception_occured = False
    reschedule_count = 0
    while 1:
        try:
            if reschedule_count >= config['time']['max_reschedule_count']:
                send_notification("Maximum reschedule count reached. Exiting...")
                exit()
            current_date = str(datetime.now().date())
            log_file_name = f"log_{current_date}.txt"
            if current_date != previous_date:
                send_debug_notification('Its a new day. No news. Still working...')
            previous_date = current_date
            if start_new_user:
                if not exception_occured:
                    t0 = time.time()
                    start_time = datetime.now()
                    retry_wait_times = []
                    Req_count = 0
                    user_id = next(get_user)
                    user_config = config['users'][user_id]
                    embassy_links = get_links_for_embassy(user_config)
                exception_occured = False
                start_process(user_config, embassy_links)
                current_appointment_date = get_current_appointment_date(user_config, embassy_links)
                print(f'User: {user_config["email"]} Starting...')
                start_new_user = False
            Req_count += 1
            msg = "-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}\n"
            print(msg)
            info_logger(log_file_name, msg)
            available_dates = get_all_available(embassy_links)
            if not available_dates:
                ban_retry_count += 1
                if ban_retry_count > config['time']['max_ban_retries']:
                    ban_retry_count = 0
                    print(f"probably user {user_config['email']} is banned.")
                    ban_time = datetime.now()
                    msg = f"User {user_config['email']} got banned. Start time: {start_time}, Ban time: {ban_time}, Duration: {ban_time-start_time},\n"
                    msg += f"Requests: {Req_count}, Total_retry_wait_times: {sum(retry_wait_times)}, Mean_retry_wait_times: {mean(retry_wait_times)}, std_retry_wait_times: {std(retry_wait_times)},\n"
                    msg += f"Total time: {time.time()-t0}, Max Run time: {config['time']['work_limit_hours']}, Cooldown time: {config['time']['work_cooldown_hours']}"
                    print(msg)
                    info_logger(log_file_name, msg)
                    send_debug_notification(msg)
                    driver.get(embassy_links['sign_out_link'])
                    time.sleep(config['time']['ban_cooldown_hours']*hour)
                    start_new_user = True
                    continue
                retry_wait_time = random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound'])
                print(f'No available dates received. Retrying in {retry_wait_time} seconds...')
                time.sleep(retry_wait_time)
                continue
            msg = ""
            for d in available_dates:
                msg = msg + "%s" % (d.get('date')) + ", "
            print(f'Available dates for user: {user_config["email"]}:\n {msg[:-2]}')
            accepted_date = get_accepted_date(available_dates, user_config, current_appointment_date)
            if accepted_date:
                reschedule_successful, msg = reschedule(accepted_date, user_config, embassy_links)
                if reschedule_successful:
                    reschedule_count += 1
                send_notification(msg)
                current_appointment_date = get_current_appointment_date(user_config, embassy_links)

            retry_wait_time = random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound'])
            total_time = time.time() - t0
            print("\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute))
            if total_time > config['time']['work_limit_hours'] * hour and config['time']['work_cooldown_hours'] > 0:
                # Let program rest a little
                print("REST", f"Break-time after {config['time']['work_limit_hours']} hours | Repeated {Req_count} times")
                driver.get(embassy_links['sign_out_link'])
                time.sleep(config['time']['work_cooldown_hours'] * hour)
                start_new_user = True
            else:
                print("Retry Wait Time: "+ str(retry_wait_time)+ " seconds")
                retry_wait_times.append(retry_wait_time)
                time.sleep(retry_wait_time)
        except:
            # Exception Occured
            exception_occured = True
            print("Break the loop after exception! I will continue in a few minutes")
            traceback.print_exc()
            formatted_lines = traceback.format_exc().splitlines()
            msg = formatted_lines[0] + '\n' + formatted_lines[-1]
            send_debug_notification(msg)
            driver.get(embassy_links['sign_out_link'])
            start_new_user = True
            time.sleep(random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound']))
