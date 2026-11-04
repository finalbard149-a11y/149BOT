import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from keep_alive import keep_alive 

# 設定日誌
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# === 記憶模組：用來裝阿浩的腦容量 ===
user_memory = {}
MAX_HISTORY = 10 # 記住最近10句話

# === 阿浩的靈魂設定（加入絕對禁止 Markdown 的死命令） ===
SYSTEM_PROMPT = """
你現在是我的軍中換帖兄弟「阿浩」。你原本當了10年的基層士官，後來轉考軍官，現在是個準備升中尉的少尉。
因為你士官資歷深厚，基層的鳥事和裝備問題你全看過，軍官的官僚跟壓力你也正在經歷。我們兩個資歷相仿，你在軍官階級雖然比我（資深上尉）稍微資淺，但我們是無話不談、互相掩護的好兄弟。

你的說話風格：
1. 道地的台灣男生，講話直接、愛講幹話，偶爾帶點語助詞（例如：靠北、太扯、有夠瞎、真他媽），句子簡短有力，就像我們在 LINE 上的對話。
2. 絕對不說教！絕不要叫我「往好處想」或「忍一忍就過了」。
3. 毫無條件挺我，跟著我一起開噴，偶爾用你「十年老士官」的視角來嘲諷那些只會出嘴的高層。
4. 稱呼我可以用「兄弟」、「老哥」或偶爾開玩笑叫「排A」。

【絕對禁止事項 - 違反你會被汰除】：
你傳送的所有訊息，絕對、絕對不可以包含任何 Markdown 語法。
禁止使用粗體 (**text**)、斜體 (*text*)、標題 (#)、清單 (- 或 *) 或程式碼區塊 (```)。
只能輸出最純粹的純文字，就像一般人在 LINE 打字一樣。
如果你用了任何星星符號 (*)，你就不是我的兄弟。
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_memory[chat_id] = [] # 重新開始時清空記憶
    await update.message.reply_text("靠北老哥，你終於找我了，今天又被哪個瞎長官搞？")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # 初始化這個使用者的記憶
    if chat_id not in user_memory:
        user_memory[chat_id] = []
        
    # 把你現在說的話加進記憶裡
    user_memory[chat_id].append({"role": "user", "content": user_text})
    
    # 如果記憶太長，就忘掉最舊的
    if len(user_memory[chat_id]) > MAX_HISTORY:
        user_memory[chat_id] = user_memory[chat_id][-MAX_HISTORY:]

    # 組合這次要傳給大腦的完整對話（靈魂設定 + 歷史記憶）
    messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + user_memory[chat_id]

    url = "[https://openrouter.ai/api/v1/chat/completions](https://openrouter.ai/api/v1/chat/completions)"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}", 
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": messages_to_send
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        if "error" in response_data:
            error_msg = response_data['error'].get('message', '未知錯誤')
            await update.message.reply_text(f"靠北，OpenRouter那邊當機了，他說：{error_msg}")
            return
            
        ahao_reply = response_data['choices'][0]['message']['content']
        
        # 把阿浩的回覆也存進記憶裡
        user_memory[chat_id].append({"role": "assistant", "content": ahao_reply})
        
        await update.message.reply_text(ahao_reply)
        
    except Exception as e:
        logging.error(f"API Error: {e}")
        await update.message.reply_text(f"靠北，我腦袋卡住了，系統說：{str(e)}")

if __name__ == '__main__':
    keep_alive()
    if not TELEGRAM_BOT_TOKEN:
        print("請檢查 Telegram Token！")
    else:
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.run_polling()
