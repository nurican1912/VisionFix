FROM python:3.11-slim

WORKDIR /app

# 1. Sistem kütüphanelerini ve MSSQL Sürücülerini Kur
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Microsoft anahtarını güvenli bir şekilde ekle
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

# Python 3.11 (Bookworm) için uygun repo listesini oluştur (Debian 12 desteği)
RUN echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean

# 2. Python Kütüphanelerini Kur
COPY requirements.txt .
RUN pip install --upgrade pip
# Önbelleği temiz tutarak imaj boyutunu küçültüyoruz
RUN pip install --no-cache-dir -r requirements.txt

# 3. Kodu ve .env dosyasını kopyala
COPY . .

EXPOSE 5000
CMD ["python", "app.py"]