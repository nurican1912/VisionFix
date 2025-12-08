FROM python:3.9

WORKDIR /app

# 1. Linux için MSSQL Sürücülerini Kur (Microsoft Resmi Yöntemi)
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg2 unixodbc unixodbc-dev
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
RUN apt-get update
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17

# 2. Python Kütüphanelerini Kur
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 3. Kodu Kopyala
COPY . .

EXPOSE 5000
CMD ["python", "app.py"]