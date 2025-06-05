# 1. Start from a lightweight Python base image
FROM python:3.10-slim

# 2. Prevent Python from writing .pyc files and enable stdout/stderr flushing
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy requirements.txt and install dependencies
#    (This allows Docker to cache pip install if requirements.txt doesn’t change.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into /app
COPY . .

# 6. Expose port 5000 so that 'docker run -p 5000:5000' maps correctly
EXPOSE 5000

# 7. Run the Flask development server on 0.0.0.0:5000
#    (Make sure app.py’s last lines use host='0.0.0.0', port=5000)
CMD ["python", "app.py"]
