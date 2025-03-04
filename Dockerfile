# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set work directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the code
COPY . /app/

# Download required NLTK data
RUN python -m nltk.downloader punkt punkt_tab

# Set Python to run in unbuffered mode to ensure logs are output immediately
ENV PYTHONUNBUFFERED=1

# Command to run the bot
CMD ["python", "-u", "bot.py"]