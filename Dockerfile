FROM python:3.10-bullseye

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y tesseract-ocr libgl1

RUN pip install pipenv

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pipenv install --deploy --ignore-pipfile

COPY . .

CMD ["pipenv", "run", "python", "main.py"]
