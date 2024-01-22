from telethon.sync import TelegramClient
import argparse
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.yaml')
args = parser.parse_args()

config = {}
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.loader.SafeLoader)

TelegramClient(config['telegram']['session'], config['telegram']['api_id'], config['telegram']['api_hash'], proxy=config['connection_proxy']).start(phone=config['telegram']['phone_number'])
print('.session file created successfully. DO NOT SHARE IT!')
