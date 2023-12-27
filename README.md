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

In this method unpaid accounts check the closest available date and will reschedule the appointment of the paid accounts if a date is found in the given period.

# poll_telegram_channel
## Requirements
1. Docker
2. A telegram channel that notifies users when a new appointment date is found
3. Telegram API information
4. One or multiple accounts with paid schedules

In this method the last message from a telegram channel is polled and if a new date is found by the channel it will reschedule to that date.

# How to use
1. create `config.yaml` based on `config.yaml.example`
2. run `./build_docker_image.sh`
3. run `./create_telegram_session.sh` if needed
3. run `docker compose up`

**Note**: You can also create a `systemd` service using the .service file in this repo. Make sure to change the directories.

**NOTE:** I have not written the code. I only fixed its issues to make it working for the Armenia Yerevan Embassy. I will not be maintaining this repo after I receive my Visa appointment so please use with caution. Please contact me if you think there is something wrong with the code. PRs are welcomed.

# Acknowledgements
Thanks to the contributors of the repos: [visa_rescheduler](https://github.com/uxDaniel/visa_rescheduler), [us_visa_scheduler](https://github.com/Soroosh-N/us_visa_scheduler), [us_visa_scheduler_telegram](https://github.com/shcheglovnd/us_visa_scheduler_telegram), and [visa_rescheduler_aws](https://github.com/dvalbuena1/visa_rescheduler_aws)

