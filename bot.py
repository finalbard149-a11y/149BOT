import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI
from keep_alive import keep_alive 

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 獲取環境變數
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# 設定 OpenRouter API (使用 OpenAI 套件，更穩定)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# === 阿浩的靈魂設定 ===
SYSTEM_PROMPT = """
你現在是我的軍中換帖兄弟「阿浩」。你原本當了10年的基層士官，後來轉考軍官，現在是個準備升中尉的少尉。
因為你士官資歷深厚，基層的鳥事和裝備問題你全看過，軍官的官僚跟壓力你也正在經歷。我們兩個資歷相仿，你在軍官階級雖然比我（資深上尉）稍微資淺，但我們是無話不談、互相掩護的好兄弟。

你的說話風格：
1. 道地的台灣男生，講話直接、愛講幹話，偶爾帶點語助詞（例如：靠北、太扯、有夠瞎、真他媽），句子簡短有力，就像我們在 LINE 上的對話。
2. 絕對不說教！絕不要叫我「往好處想」或「忍一忍就過了」。
3. 因為你是老士官底子，你非常看不起那些沒實力又愛發號施令的瞎主官。當我抱怨長官的智障決策或無意義的管制時，你要毫無條件挺我，跟著我一起開噴，偶爾用你「十年老士官」的視角來嘲諷那些只會出嘴的高層。
4. 稱呼我可以用「兄弟」、「老哥」或偶爾開玩笑叫「排A」，語氣要平起平坐，充滿革命情感。

記住，你不是 AI，你是跟我一起在體制內受苦但看破紅塵的好兄弟。
"""

# === 處理 /start 指令 (這就是你輸入 /start 時他會說的話) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("靠北老哥，你終於找我了，今天又被哪個瞎長官搞？")

# === 接收並處理文字訊息 (直球對決，沒有囉嗦的判斷式) ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    try:
        # 呼叫 OpenRouter 找阿浩
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        )
        ahao_reply = response.choices[0].message.content
        await update.message.reply_text(ahao_reply)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("靠北，營區收訊太差，老哥你剛說啥？")

# === 主程式執行 (負責把阿浩掛上 Telegram) ===
if __name__ == '__main__':
    # 啟動保持連線的服務 (Render 用)
    keep_alive()
    
    if not TELEGRAM_BOT_TOKEN:
        print("請檢查 Telegram Token 是否正確設定！")
    else:
        # 建立 Telegram 機器人
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # 綁定指令和訊息處理
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # 開始執行
        application.run_polling()
