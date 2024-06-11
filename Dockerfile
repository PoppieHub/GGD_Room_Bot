FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Run the bot implementation
CMD ["python", "main.py"]