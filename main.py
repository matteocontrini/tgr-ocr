import html
import json
import os
import re
import time
from datetime import datetime

import cv2
import editdistance
import pytesseract
import requests
import schedule

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
        if ret:
            frame = cv2.resize(frame, (0, 0), fx=ratio, fy=1)
            frame = frame[495:545, 80:380]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            text = pytesseract.image_to_string(frame).strip()
            # print(text)

            if editdistance.eval('EMILIO MOLINARI', text.upper()) <= 4:
                print(f'Found at {msec_to_time(timestamp)}')
                found.append(timestamp)
                timestamp += 40 * 1000
            else:
                timestamp += 2000
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp)
        else:
            cap.release()
            break

    send_message(found, title)

    print(f'Done at {datetime.now().isoformat()}')


def send_message(found: list, title: str):
    msg = f'<b>{title}</b>\n'
    if len(found) == 0:
        msg += 'Emilio non ha montato servizi :('
    else:
        msg += f'Emilio ha montato {len(found)} servizi:\n'
        for timestamp in found:
            msg += f'- {msec_to_time(timestamp)}\n'

    print(msg)
    resp = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', data={
        'chat_id': '-1001740623444',
        'text': msg,
        'parse_mode': 'HTML'
    })
    if resp.status_code != 200:
        print(f'Error sending message: {resp.text}')


def msec_to_time(msec):
    sec = msec / 1000
    min = sec / 60
    sec = sec % 60
    hour = min / 60
    min = min % 60
    return f'{hour:02.0f}:{min:02.0f}:{sec:02.0f}'


if __name__ == '__main__':
    schedule.every().day.at('15:30', 'Europe/Rome').do(run)
    schedule.every().day.at('21:00', 'Europe/Rome').do(run)

    while 1:
        schedule.run_pending()
        time.sleep(60)
