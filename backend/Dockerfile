# Backend image: Python + the API. Data and the model are built inside the image.
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
# Generate sample data and train the model at build time, so the API starts instantly.
RUN python -m app.data.generate && python -m app.predictor.train

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
