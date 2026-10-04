FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY data_and_code_base ./data_and_code_base
COPY output ./output

RUN pip install --no-cache-dir .

ENV NAVIGATOR_DEMO_HOST=0.0.0.0
EXPOSE 8765

CMD ["python", "-m", "navigator", "demo"]
