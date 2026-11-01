import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from openai import OpenAI
from keep_alive import keep_alive
import docx
from pypdf import PdfReader

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
        "（已具備文件讀取能力）\n\n"
        "您可以直接傳送以下內容給我：\n"
        "1. **純文字**：戰備紀錄、對話排版。\n"
        "2. **文件檔案 (.txt, .docx, .pdf)**：為您讀取內容並校稿抓錯。"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def process_with_ai(chat_id, user_text, update):
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    await process_with_ai(chat_id, user_text, update)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    doc = update.message.document
    file_name = doc.file_name
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # 限制只處理特定副檔名
    if not (file_name.endswith('.txt') or file_name.endswith('.docx') or file_name.endswith('.pdf')):
        await update.message.reply_text("目前秘書只支援讀取 .txt, .docx, 與 .pdf 格式的文件喔！")
        return

    # 下載檔案到暫存區
    file = await context.bot.get_file(doc.file_id)
    file_path = f"/tmp/{doc.file_id}_{file_name}"
    await file.download_to_drive(file_path)
    
    await update.message.reply_text(f"正在努力閱讀「{file_name}」...")
    
    extracted_text = ""
    try:
        if file_name.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()
        elif file_name.endswith('.docx'):
            doc_obj = docx.Document(file_path)
            extracted_text = "\n".join([p.text for p in doc_obj.paragraphs])
        elif file_name.endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text()
    except Exception as e:
        await update.message.reply_text(f"抱歉，讀取文件時發生錯誤：{e}")
        return
    finally:
        # 讀取完畢後刪除暫存檔，避免佔用伺服器空間
        if os.path.exists(file_path):
            os.remove(file_path)
            
    if not extracted_text.strip():
        await update.message.reply_text("這份文件中沒有找到可以讀取的純文字。")
        return

    # 將提取出來的文字組裝成指令丟給 AI
    ai_prompt = f"這是我上傳的文件「{file_name}」，請將以下內容記住。回覆我『文件已讀取完畢，隨時等候您的指示』即可，請絕對不要主動進行排版、摘要或修改。內容如下：\n\n{extracted_text}"
    await process_with_ai(chat_id, ai_prompt, update)

def main():
    keep_alive()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    logging.info("多模態秘書機器人已上線運行中...")
    app.run_polling()

if __name__ == '__main__':
    main()
