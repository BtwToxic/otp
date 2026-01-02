FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install pyrogram tgcrypto pymongo
CMD ["python", "bot.py"]
