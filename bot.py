import logging
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import datetime
import random 
import os # Ortam değişkenlerini okumak için
# from dotenv import load_dotenv # Eğer yerel test için .env kullanacaksanız
# load_dotenv() 

# Loglamayı etkinleştirme
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Ayarlar ---
# BOT_TOKEN'ı doğrudan kod yerine, ortam değişkenlerinden alıyoruz!
# Render'da tanımlayacağınız Environment Variable adı 'BOT_TOKEN' olmalı.
BOT_TOKEN = os.environ.get("BOT_TOKEN") 

# Eğer token bulunamazsa botun başlamaması için kontrol ekleyelim
if not BOT_TOKEN:
    logger.error("BOT_TOKEN ortam değişkeni bulunamadı. Lütfen Render ayarlarınızı kontrol edin.")
    exit(1)

# Her saat başı rastgele seçilip gönderilecek haber başlıkları/mesajları (Aynı liste)
HABER_MESAJLARI = [
    "📰 **Gündemin Sıcağı Sıcağına!** \n\nGüncel haberleri sizin için derledik. Ayrıntılar için web sitemizi ziyaret edin.",
    "🚀 **Son Dakika Bülteni!** \n\nTeknoloji dünyasında çığır açan gelişme... Devamı için butona tıklayın.",
    "💰 **Ekonomi Raporu.** \n\nPiyasalarda hareketli bir gün. Yatırımcıların odak noktası neler? *Devamını Oku.*",
    "🌍 **Dünyadan Haberler.** \n\nUluslararası ilişkilerde kritik viraj. Analizler birazdan yayında!",
    "⏰ **Saatlik Hatırlatma:** \n\nGüncel haberleri okumayı unutmayın! {time} itibarıyla son gelişmeleri inceleyin.",
    "Sporun kalbi burada atıyor! ⚽ Basketbol ve futbol maç sonuçları, transferler ve yorumlar.",
]
# ----------------

# (gonder_otomatik_mesaj, start, ve stop fonksiyonları aynı kalacak)
# ... önceki koddan kopyalayıp yapıştırabilirsiniz ...

async def gonder_otomatik_mesaj(context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (Önceki kodunuzdaki gonder_otomatik_mesaj fonksiyonu) ...
    chat_id = context.job.data
    secilen_mesaj = random.choice(HABER_MESAJLARI)
    anlik_zaman = datetime.datetime.now().strftime("%H:%M")
    mesaj = secilen_mesaj.format(time=anlik_zaman)
    
    try:
        await context.bot.send_message(chat_id=chat_id, text=mesaj, parse_mode='Markdown')
        logger.info(f"Chat ID {chat_id} için haber mesajı gönderildi.")
    except Exception as e:
        logger.error(f"Chat ID {chat_id} için mesaj gönderilirken hata oluştu: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (Önceki kodunuzdaki start fonksiyonu) ...
    chat_id = update.message.chat_id
    
    await update.message.reply_text(
        "📰 **Hoş Geldiniz!** \n\nArtık her saat başı otomatik haber bülteninizi alacaksınız. \n\nÖzelliği durdurmak için `/stop` komutunu kullanın. \n\nİlk haber 10 saniye içinde geliyor!"
    )
    
    job_name = str(chat_id)
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
        logger.info(f"Chat ID {chat_id} için var olan job'lar kaldırıldı.")
        
    context.job_queue.run_repeating(
        gonder_otomatik_mesaj, 
        interval=3600, 
        first=10, 
        chat_id=chat_id, 
        data=chat_id, 
        name=job_name 
    )
    logger.info(f"Chat ID {chat_id} için saatlik haber job'ı başlatıldı.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (Önceki kodunuzdaki stop fonksiyonu) ...
    chat_id = update.message.chat_id
    job_name = str(chat_id)
    
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    
    if not current_jobs:
        await update.message.reply_text("Zaten aktif bir haber bülteni aboneliğiniz bulunmuyor.")
        return

    for job in current_jobs:
        job.schedule_removal()
    
    await update.message.reply_text("⛔ **Haber bülteni aboneliği durduruldu.** Tekrar başlatmak için `/start` yazabilirsiniz.")
    logger.info(f"Chat ID {chat_id} için haber job'ı durduruldu.")


def main() -> None:
    """Bot'u başlatır."""
    # BOT_TOKEN burada kullanılıyor, bu yüzden yukarıdaki kontrol kritik
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Komut işleyicileri ekleme
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    
    logger.info("Haber Botu başlatılıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
  
