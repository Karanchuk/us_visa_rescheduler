# visa_rescheduler
The visa_rescheduler is a bot for US VISA (usvisa-info.com) appointment rescheduling. This bot can help you reschedule your appointment to your desired time period.

Supported embassies can be found in `embassy.py`. Feel free to add any additional ones using the method explained [here](https://github.com/Soroosh-N/us_visa_scheduler).

There are three approaches you can use:

# with_payment
## Requirements
1. Docker
2. One or multiple accounts with paid schedules

In this method only the paid account checks the available dates and will reschedule the appointment if a date is found in the given period.

# no_payment
## Requirements
1. Docker
2. One or multiple accounts without paid schedules
3. One or multiple accounts with paid schedules

In this method unpaid accounts check the closest available date and will reschedule the appointment of the paid accounts if a date is found in the given period. Please note that the date that the unpaid accounts show may not be accurate.

# poll_telegram_channel (Special Case)
## Requirements
1. Docker
2. A telegram channel that sends a message when a new appointment date is found
3. Your Telegram API information
4. One or multiple accounts with paid schedules

In this method if a new message is sent in a specific telegram channel that includes a new schedule date, the script will read the message, extract the date, and reschedule to that date. 
This method is a special case for people who are joined in a telegram channel ran by a bot that notifies users when a new schedule date is available.

# How to use
1. create `config.yaml` based on `config.yaml.example`
2. run `./build_docker_image.sh`
3. run `./create_telegram_session.sh` if needed
4. run `docker compose up`

**Note**: You can also create a `systemd` service using the .service file in this repo. Make sure to change the directories.

# Disclamer
I have not tested the parts of the code that do the rescheduling (I copied those parts from other repos). I only made the code working for the Armenia Yerevan Embassy. You may need small modifications to make it work for your own embassy.
I will not be maintaining this repo after I receive my Visa appointment so please use with caution. Feel free to open issues if you think there is something wrong with the code. PRs are welcomed.

# Acknowledgements
Thanks to the contributors of the repos: [visa_rescheduler](https://github.com/uxDaniel/visa_rescheduler), [us_visa_scheduler](https://github.com/Soroosh-N/us_visa_scheduler), [us_visa_scheduler_telegram](https://github.com/shcheglovnd/us_visa_scheduler_telegram), and [visa_rescheduler_aws](https://github.com/dvalbuena1/visa_rescheduler_aws)

# Donations
Consider buying me a coffee if this helped you.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/aflt)

