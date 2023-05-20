import gc
import html
import json
import os
import re
from datetime import datetime

import cv2
import editdistance
import pytesseract
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

BOT_TOKEN = os.environ['BOT_TOKEN']


def run():
    print(f'It\'s {datetime.now().isoformat()}')

    url = 'https://www.rainews.it/tgr/trento/notiziari'
    print(f'Opening {url}')

    text = requests.get(url).text
    payload = re.search(r'<rainews-player data=\'(.*?)\'></rainews-player>', text).group(1)
    payload = html.unescape(payload)
    data = json.loads(payload)

    title = data['title']
    content_url = data['content_url']

    print(f'Found "{title}"')
    print(f'Relinker: {content_url}')

    cap = cv2.VideoCapture(content_url)
    ratio = cap.get(cv2.CAP_PROP_SAR_NUM) / cap.get(cv2.CAP_PROP_SAR_DEN)
    timestamp = 0
    found = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (0, 0), fx=ratio, fy=1)
        frame = frame[495:545, 80:380]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        text = pytesseract.image_to_string(frame).strip()

        if editdistance.eval('EMILIO MOLINARI', text.upper()) <= 4:
            print(f'Found at {msec_to_time(timestamp)}')
            found.append(timestamp)
            timestamp += 40 * 1000
        else:
            timestamp += 2000
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp)

    cap.release()

    send_message(found, title)

    print(f'Done at {datetime.now().isoformat()}')

    gc.collect()


def send_message(found: list, title: str):
    msg = f'<b>{title}</b>\n'
    if len(found) == 0:
        msg += 'Emilio non ha montato servizi :('
    else:
        msg += f'Emilio ha montato {len(found)} servizi:\n'
        for timestamp in found:
            msg += f'- {msec_to_time(timestamp)}\n'

    resp = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', data={
        'chat_id': '-1001740623444',
        'text': msg,
        'parse_mode': 'HTML'
    })
    if resp.status_code != 200:
        print(f'Error sending message: {resp.text}')


def msec_to_time(msec):
    seconds = int(msec / 1000)
    return f'{seconds // 60:02}:{seconds % 60:02}'


if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(run, trigger=CronTrigger(hour='15', minute='20', timezone='Europe/Rome'))
    scheduler.add_job(run, trigger=CronTrigger(hour='21', minute='00', timezone='Europe/Rome'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
