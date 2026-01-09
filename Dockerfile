FROM python:3.10

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cache-dir --no-compile -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:init_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]