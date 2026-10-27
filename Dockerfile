FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/portfolio
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 portfolio
COPY --chown=portfolio:portfolio . .
RUN mkdir -p /srv/portfolio/instance && chown portfolio:portfolio /srv/portfolio/instance
USER portfolio
EXPOSE 8000
CMD ["bash", "scripts/start.sh"]
