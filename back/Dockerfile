# Use python:3.11 exept arm64v8/python:3.11
FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install pip and application dependencies
RUN pip install --no-cache-dir --upgrade pip
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install python-dotenv

# Copy the application code
COPY ./app .
COPY ./start.sh .

# Expose the port for the web application
# EXPOSE 80
#EXPOSE 443

RUN chmod +x /app/start.sh
# Start the application using a shell script
CMD ["/app/start.sh"]    