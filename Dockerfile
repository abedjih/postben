FROM python:3.12-alpine

WORKDIR /app

COPY app.py .
COPY static/ static/

RUN mkdir -p data

EXPOSE 5000

CMD ["python3", "app.py"]
