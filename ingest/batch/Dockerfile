FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir dbt-duckdb==1.8.0
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
RUN mkdir -p /app/data
CMD ["python", "main.py"]
