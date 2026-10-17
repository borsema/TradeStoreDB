FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run.py .

ENV FLASK_ENV=production
ENV PORT=1000

EXPOSE 1000

CMD ["python", "run.py"]
