FROM python:3.9

WORKDIR /app

COPY . ./

RUN pip3 --no-cache-dir install -r requirements.txt

CMD [ "python", "-u", "main.py" ]