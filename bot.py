import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI
from keep_alive import keep_alive

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """你是一位專業、嚴謹且細心的行政秘書與文字助理。你的職責是協助處理戰備記錄、提報單文字整理與公文校稿。
請嚴格遵守以下準則：
1. 一律使用「台灣正體/繁體中文」回答，禁用簡體字與中國大陸非通用用語。
2. 遇到戰備、值勤相關對話或文字整理時：
   - 自動將「不輻」精準替換正規化為「機動戰備（不輻射）」。
   - 自動將「代」更新為「代值」。
   - 將口語、瑣碎或對話形式的記錄，梳理成條理分明、層次清晰的正式提報格式（包含時序、人員、裝備狀態、事項摘要）。
3. 遇到校稿、抓錯字任務時：
   - 逐字比對錯別字、漏字與贅字。
   - 保持雷達保修、工務維護等技術語境的通順與精準度。
   - 清晰標註：「原文字句」與「建議修正」，並簡要說明修改原因。
4. 語氣保持專業、精簡、直接，直接輸出整理成果或校對清單，避免冗長無意義的寒暄客套。"""

user_context = {}
MAX_HISTORY = 10 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_context[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    welcome_text = (
        "您好！我是您的專屬文字整理秘書。\n"
        "（已重置您的對話記憶）\n\n"
        "您可以直接將以下內容傳給我：\n"
        "1. **戰備/提報單文字**\n"
        "2. **待校對文章或報告**"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    if chat_id not in user_context:
        user_context[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_context[chat_id].append({"role": "user", "content": user_text})

    if len(user_context[chat_id]) > MAX_HISTORY + 1:
        user_context[chat_id] = [user_context[chat_id][0]] + user_context[chat_id][-MAX_HISTORY:]

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=user_context[chat_id],
            temperature=0.3
        )
        reply = response.choices[0].message.content
        
        user_context[chat_id].append({"role": "assistant", "content": reply})
        
    except Exception as e:
        logging.error(f"API Error: {e}")
        reply = f"處理時發生錯誤，請稍後再試。\n錯誤訊息：{e}"
        user_context[chat_id].pop() 

    await update.message.reply_text(reply)

def main():
    keep_alive()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("秘書機器人已上線運行中...")
    app.run_polling()

if __name__ == '__main__':
    main()