# 1. Use a lightweight Python 3.10 base image
FROM python:3.10-slim

# 2. Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy and install dependencies first (caching layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code into the container
COPY . .

# 6. Expose port 5000 for Flask
EXPOSE 5000

# 7. Run the Flask app
CMD ["python", "app.py"]
