FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Pythonのパッケージをインストール
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Playwrightのブラウザをインストール（Python版イメージでは既に入っている場合が多いですが、念のため）
RUN playwright install chromium

# ソースコードをコピー
COPY . .

# 実行コマンド（デフォルトは待機）
CMD ["tail", "-f", "/dev/null"]
