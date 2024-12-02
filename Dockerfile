FROM python:3.10.12

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    python3-tk \
    fonts-noto \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && echo "ja_JP.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && mkdir /app

# 必要なPythonパッケージのインストール
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt

# アプリケーションのコピー
COPY src/main.py /app/main.py
WORKDIR /app

# 環境変数の設定
ENV DISPLAY=:0
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

CMD ["python", "main.py"]