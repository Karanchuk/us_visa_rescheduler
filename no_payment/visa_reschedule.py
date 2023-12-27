import os
import argparse
import time
import json
import random
import requests
import traceback
import yaml
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
# from selenium.common.exceptions import NoSuchElementException
from embassy import embassies

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

os.environ['TZ'] = config['time']['time_zone']
time.tzset()

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
        requests.post(url, data)

def send_notification(msg):
    data = {
        'chat_id': config['telegram']['chat_id'],
        'text': msg,
    }
    token = config['telegram']['bot_token']
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    print(f"Sending notification {data}")
    requests.post(url, data)


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
    
## This function may need to change based on your Embassy (If your embassy shows more than one date in the payment page.)
def get_first_available_appointments(embassy_links):
    driver.get(embassy_links['payment_url'])
    res = {}
    location = driver.find_elements(by=By.XPATH, value=f'//*[@id="paymentOptions"]/div[2]/table/tbody/tr/td[1]')
    status = driver.find_elements(by=By.XPATH, value=f'//*[@id="paymentOptions"]/div[2]/table/tbody/tr/td[2]')
    if not location or not status:
        return None
    location = location[0].text
    try:
        status = datetime.strptime(status[0].text, "%d %B, %Y").date()
    except ValueError:
        status = status[0].text
    res[location] = status
    return res
        
def get_unpaid_user_id():
    id = 0
    while True:
        yield id
        id = (id + 1) % len(config['unpaid_users'])

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

if config['chrome_driver']['local_use']:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
else:
    driver = webdriver.Remote(command_executor=config['chrome_driver']['hub_address'], options=webdriver.ChromeOptions())

if __name__ == "__main__":
    start_new_user = True
    get_user = get_unpaid_user_id()
    previous_date = str(datetime.now().date())
    prev_available_appointments = None
    current_appointment_date = None
    unpaid_signed_out = True
    ban_timestamps = {}
    banned_count = 0    
    while 1:
        try:
            current_date = str(datetime.now().date())
            log_file_name = f"log_{current_date}.txt"
            if current_date != previous_date:
                send_debug_notification('Its a new day. No news. Still working...')
            previous_date = current_date
            if start_new_user:
                t0 = time.time()
                start_time = datetime.now()
                retry_wait_times = []
                total_time = 0
                Req_count = 0
                user_id = next(get_user)
                user_config = config['unpaid_users'][user_id]
                embassy_links = get_links_for_embassy(user_config)
                start_process(user_config, embassy_links)
                unpaid_signed_out = False
                print(f'User: {user_config["email"]} Starting...')
                start_new_user = False
            if unpaid_signed_out:
                start_process(user_config, embassy_links)
                unpaid_signed_out = False
            Req_count += 1
            msg = "-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}\n"
            print(msg)
            info_logger(log_file_name, msg)
                
            appointments = get_first_available_appointments(embassy_links)
            if appointments is None:
                msg = 'Website did not send appointment data.'
                print(msg)
                info_logger(log_file_name, msg)
                continue
            if all(x == "No Appointments Available" for x in appointments.values()):
                print(f"Probably user {user_config['email']} is banned.")
                ban_time = datetime.now()
                msg = f"User {user_config['email']} got banned. Start time: {start_time}, Ban time: {ban_time}, Duration: {ban_time-start_time},\n"
                msg += f"Requests: {Req_count}, Total_retry_wait_times: {sum(retry_wait_times)}, Mean_retry_wait_times: {mean(retry_wait_times)}, std_retry_wait_times: {std(retry_wait_times)},\n"
                msg += f"Total time: {time.time()-t0}, Max Run time: {config['time']['work_limit_hours']}, Cooldown time: {config['time']['work_cooldown_hours']}"
                print(msg)
                info_logger(log_file_name, msg)
                banned_count += 1
                ban_timestamps[user_id] = ban_time
                driver.get(embassy_links['sign_out_link'])
                unpaid_signed_out = True
                start_new_user = True
                if banned_count == len(config['unpaid_users']):
                    temp = ban_time
                    for id in ban_timestamps:
                        if ban_timestamps[id] < temp:
                            temp = ban_timestamps[id]
                    time_from_first_ban = ban_time-temp
                    time_to_ban = timedelta(hours=config['time']['ban_cooldown_hours']) - time_from_first_ban
                    if time_to_ban > timedelta(0):
                        msg = f"All users are banned, resting for {time_to_ban}"
                        print(msg)
                        info_logger(log_file_name, msg)
                        time.sleep(time_to_ban.total_seconds())
                    banned_count -= 1
                continue
            if appointments != prev_available_appointments:
                msg = 'Found new date(s): '
                for appointment in appointments:
                    msg += str(appointments[appointment]) + ' '
                send_debug_notification(msg[:-1])
                for paid_user_config in config['paid_users']:
                    reschedule_successful = False
                    for new_available_date in appointments.values():
                        if reschedule_successful:
                            break
                        if is_in_period(new_available_date, datetime.strptime(paid_user_config['period_start'], "%Y-%m-%d").date() , datetime.strptime(paid_user_config['period_end'], "%Y-%m-%d").date()):
                            driver.get(embassy_links['sign_out_link'])
                            unpaid_signed_out = True
                            paid_user_embassy_links = get_links_for_embassy(paid_user_config)
                            start_process(paid_user_config, paid_user_embassy_links)
                            current_appointment_date = get_current_appointment_date(paid_user_config, paid_user_embassy_links)
                            reschedule_retry_count = 0
                            while reschedule_successful == False and reschedule_retry_count < config['time']['reschedule_max_retry_count']:
                                available_dates = get_all_available(paid_user_embassy_links)
                                if available_dates:
                                    msg = ""
                                    for d in available_dates:
                                        msg = msg + "%s" % (d.get('date')) + ", "
                                    print(f'Available dates for user: {paid_user_config["email"]}:\n {msg[:-2]}')
                                    accepted_date = get_accepted_date(available_dates, paid_user_config, current_appointment_date)
                                    if accepted_date:
                                        reschedule_successful, msg = reschedule(accepted_date, paid_user_config, paid_user_embassy_links)
                                        send_notification(msg)
                                    else:
                                        send_debug_notification(f"Unpaid account {user_config['email']} found {new_available_date} but it was not available for paid account {paid_user_config['email']}. Rescheduling failed.")
                                else:
                                    send_debug_notification(f"Paid account: {paid_user_config['email']} is banned. Could not reschedule for {new_available_date}")
                                reschedule_retry_count += 1
                            driver.get(paid_user_embassy_links['sign_out_link'])
                        else:
                            print(f"found new date {new_available_date} but is not in the selected period of {paid_user_config['email']}.")
            retry_wait_time = random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound'])
            t1 = time.time()
            total_time = t1 - t0
            print("\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute))
            if total_time > config['time']['work_limit_hours'] * hour and config['time']['work_cooldown_hours'] > 0:
                # Let program rest a little
                print("REST", f"Break-time after {config['time']['work_limit_hours']} hours | Repeated {Req_count} times")
                driver.get(embassy_links['sign_out_link'])
                time.sleep(config['time']['work_cooldown_hours'] * hour)
                start_new_user = True
                unpaid_signed_out = True
            else:
                print("Retry Wait Time: "+ str(retry_wait_time)+ " seconds")
                retry_wait_times.append(retry_wait_time)
                time.sleep(retry_wait_time)
            prev_available_appointments = appointments            
        except:
            # Exception Occured
            print(f"Break the loop after exception! I will continue in a few minutes\n")
            traceback.print_exc()
            formatted_lines = traceback.format_exc().splitlines()
            msg = formatted_lines[0] + '\n' + formatted_lines[-1]
            send_debug_notification(msg)
            time.sleep(random.randint(config['time']['retry_lower_bound'], config['time']['retry_upper_bound']))
