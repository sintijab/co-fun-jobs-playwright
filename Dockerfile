FROM --platform=linux/amd64 python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 80

CMD ["gunicorn", "-w", "2", "--timeout", "600", "--graceful-timeout", "120", "-b", "0.0.0.0:80", "app:app"]
