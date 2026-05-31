FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p instance

EXPOSE 8080

CMD gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 60 --log-level info
