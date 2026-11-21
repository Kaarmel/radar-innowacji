FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY radar radar
COPY konfiguracja konfiguracja
# Baza (dane/radar.sqlite) i klucze (.env) montowane z zewnątrz:
#   docker run -p 8090:8090 -v "$PWD/dane:/app/dane" --env-file .env radar-innowacji
# Pusta baza: python -m radar.cli pobierz interreg|mapadotacji|radon|radon_patenty
VOLUME /app/dane
EXPOSE 8090
CMD ["uvicorn", "radar.app:app", "--host", "0.0.0.0", "--port", "8090", "--proxy-headers"]
