# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /ragaiapi

# Set the logs directory
RUN mkdir -p /ragaiapi/logs

# Set the output directory for processed files
RUN mkdir -p /ragaiapi/processed_files

# Copy the current app directory contents into the container at /app
COPY ./app /ragaiapi/app
COPY ./requirements.txt /ragaiapi/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade -r /ragaiapi/requirements.txt

# Make port 10103 available to the world outside this container
EXPOSE 10103

# add PYTHONPATH to solve absolute import error for docker
#ENV PYTHONPATH "${PYTHONPATH}:/ragaiapi/app"
ENV PYTHONPATH "${PYTHONPATH}:/ragaiapi"

###############################
# Creates a non-root user with an explicit UID and adds permission to access the /ragaiapi folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /ragaiapi
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
#CMD ["gunicorn", "--bind", "0.0.0.0:10103", "-k", "uvicorn.workers.UvicornWorker", "app.main:app"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10103"]
