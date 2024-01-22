 docker run --rm -it  -v "$PWD":/app -w /app --network host usvs_telegram_channel python3 create_telegram_session.py --config config.yaml
 