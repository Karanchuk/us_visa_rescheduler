# visa_rescheduler
The visa_rescheduler is a bot for US VISA (usvisa-info.com) appointment rescheduling. This bot can help you reschedule your appointment to your desired time period.
 
To avoid banning an account with appointment, I made it so that unpaid accounts look for appointments and if they find one the script logs into a paid account and reschedules to the found date.

Supported embassies can be found in `embassy.py`. Feel free to add any additional ones using the method explained [here](https://github.com/Soroosh-N/us_visa_scheduler).

# Requirements
1. Docker
2. One or multiple accounts without paid schedules
3. One or multiple accounts with paid schedules


# How to use
1. create `config.yaml` based on `config.yaml.example`
2. run `./build_docker_image.sh`
3. run `docker compose up`

**Note**: You can also create a `systemd` service using the .service file in this repo. Make sure to change the directories.

**NOTE:** I have not written the code. I only fixed its issues to make it working for the Armenia Yerevan Embassy. I will not be maintaining this repo after I receive my Visa appointment so please use with caution. Please contact me if you think there is something wrong with the code. PRs are welcomed.

# Acknowledgements
Thanks to the contributors of the repos: [visa_rescheduler](https://github.com/uxDaniel/visa_rescheduler), [us_visa_scheduler](https://github.com/Soroosh-N/us_visa_scheduler), [us_visa_scheduler_telegram](https://github.com/shcheglovnd/us_visa_scheduler_telegram), and [visa_rescheduler_aws](https://github.com/dvalbuena1/visa_rescheduler_aws)

