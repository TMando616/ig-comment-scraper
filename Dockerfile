FROM mcr.microsoft.com/playwright:v1.42.0-jammy

# Pythonのパッケージをインストール
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightのブラウザをインストール（公式イメージに含まれているが、念のため）
RUN playwright install chromium

# ソースコードをコピー
COPY . .

# 実行コマンド（デフォルトは待機）
CMD ["tail", "-f", "/dev/null"]
