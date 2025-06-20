from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, PicklePersistence
from telegram.error import NetworkError, TelegramError, BadRequest
from stock_fetcher import get_volatility
from stock_fetcher import get_cheap_stocks
import time
import logging
from stock_fetcher import generate_detailed_analysis
import asyncio

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = '7364319210:AAHEbp4XC2ddKlLsab__d3eMJbu6DyUMFDU'

async def _send_continuous_typing(chat):
    """Background task to keep showing typing indicator"""
    while True:
        try:
            await chat.send_action(action='typing')
            await asyncio.sleep(4)  # Refresh typing indicator every 4 seconds
        except Exception as e:
            logger.error(f"Typing indicator error: {e}")
            break

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "📈 <b>Stock Analysis Bot</b> 📉\n\n"
            "Available commands:\n"
            "/stocks - Get top stock picks\n"
            "/help - Show this message",
            parse_mode='HTML'
        )
    except TelegramError as e:
        logger.error(f"Start command error: {e}")

async def stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    max_retries = 3
    retry_delay = 2
    
    try:
        msg = await update.message.reply_text("🔍 Scanning for stocks under ₹100...")
        
        for attempt in range(max_retries):
            try:
                stocks_data = get_cheap_stocks()
                
                # Validate results before sending
                if not stocks_data:
                    await msg.edit_text(
                        "⚠️ No qualifying stocks found today.\n\n"
                        "Possible reasons:\n"
                        "- Market conditions too strict\n"
                        "- Temporary data issues\n"
                        "Try again later or adjust filters."
                    )
                    return
                
                # First message - Stock list
                response = ["<b>💰 Top Stocks Under ₹100</b> 🚀\n\n"]
                for stock in stocks_data:
                    response.append(
                        f"🏢 <b>{stock.get('name', 'N/A')}</b> ({stock.get('symbol', '?')})\n"
                        f"• Price: ₹{stock.get('price', 0):.2f} | PE: {stock.get('pe', 'N/A')}\n"
                        f"• Volatility: {stock.get('volatility', 0)}% | Mcap: {stock.get('mcap', 'N/A')}\n"
                        f"──────────────────"
                    )
                
                await msg.edit_text(
                    text="\n".join(response)[:4096],
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                
                # Second message - Detailed analysis
                analysis_header = await update.message.reply_text(
                    "📊 <b>Detailed Analysis:</b>",
                    parse_mode='HTML'
                )
                
                for stock in stocks_data:
                    try:
                        analysis = generate_detailed_analysis(stock)
                        await update.message.reply_text(
                            analysis,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )
                        time.sleep(1)  # Prevent rate limiting
                    except Exception as e:
                        logger.error(f"Analysis failed for {stock.get('symbol')}: {e}")
                        continue
                
                break  # Success, exit retry loop
                    
            except NetworkError as e:
                if attempt == max_retries - 1:
                    await msg.edit_text("🔴 Network Error\nPlease try again later")
                time.sleep(retry_delay * (attempt + 1))
                
    except Exception as e:
        logger.error(f"Error in /stocks: {str(e)}")
        await update.message.reply_text("⚠️ System busy. Try /stocks again later.")

def main():
    # Option 1: Without persistence
    app = Application.builder() \
        .token(BOT_TOKEN) \
        .build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stocks", stocks))
    app.add_handler(CommandHandler("help", start))
    
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()