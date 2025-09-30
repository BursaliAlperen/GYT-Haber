const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const cheerio = require('cheerio');
const express = require('express');

// Express app oluştur (Render health check için)
const app = express();
const PORT = process.env.PORT || 3000;

// Basit health check endpoint
app.get('/', (req, res) => {
  res.json({ 
    status: 'OK', 
    message: 'GYT Haber Botu çalışıyor!',
    timestamp: new Date().toISOString()
  });
});

// Health check için /health endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    service: 'gyt-haber-bot',
    timestamp: new Date().toISOString()
  });
});

// Server'ı başlat
app.listen(PORT, () => {
  console.log(`🚀 Health check server ${PORT} portunda çalışıyor...`);
});

// Environment variables'dan bot token'ını al
const TOKEN = process.env.BOT_TOKEN;
if (!TOKEN) {
  console.error('❌ BOT_TOKEN environment variable bulunamadı!');
  process.exit(1);
}

const bot = new TelegramBot(TOKEN, { 
  polling: true,
  // Webhook için gerekli ayarlar
  webHook: false
});

// Kullanıcı veritabanı (basit bir object - production'da database kullanın)
const users = {};

// Haber kaynakları
const newsSources = [
    {
        name: 'Hürriyet',
        url: 'https://www.hurriyet.com.tr',
        selectors: {
            headlines: 'h3 a, .news-title, .title',
            images: 'img'
        }
    },
    {
        name: 'Milliyet',
        url: 'https://www.milliyet.com.tr',
        selectors: {
            headlines: '.news-title a, h3 a, .title',
            images: 'img'
        }
    },
    {
        name: 'NTV',
        url: 'https://www.ntv.com.tr',
        selectors: {
            headlines: '.news-title, h3, .title',
            images: 'img'
        }
    },
    {
        name: 'BBC Türkçe',
        url: 'https://www.bbc.com/turkce',
        selectors: {
            headlines: 'h3 a, .title, .news-title',
            images: 'img'
        }
    }
];

// Bot komutları
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const username = msg.from.first_name;
    
    // Kullanıcıyı kaydet
    users[chatId] = {
        username: username,
        chatId: chatId,
        subscribed: true,
        subscriptionType: 'hourly',
        lastSent: Date.now(),
        joinDate: new Date().toISOString()
    };

    const welcomeMessage = `
🤖 *GYT HABER BOT'una Hoş Geldiniz ${username}!* 🎉

📰 *Özellikler:*
• Güncel haberleri otomatik olarak alın
• Farklı zaman aralıklarında bildirimler
• Çeşitli haber kaynaklarından içerik
• Kişiselleştirilmiş haber akışı

⏰ *Zaman Seçenekleri:*
/yarimsaat - Yarım saatte bir haber
/saatlik - Saatte bir haber
/ikisaat - İki saatte bir haber
/durdur - Bildirimleri durdur

📊 *Diğer Komutlar:*
/simdi - Hemen haber al
/ayarlar - Ayarları görüntüle
/yardim - Yardım menüsü
/istatistik - Bot istatistikleri

_Gündemin nabzını buradan tutalım!_ 📈
    `;

    bot.sendMessage(chatId, welcomeMessage, { 
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: [[
                { text: '🚀 Hemen Haber Al', callback_data: 'send_now' }
            ]]
        }
    });

    console.log(`✅ Yeni kullanıcı: ${username} (${chatId})`);
});

// Haber çekme fonksiyonu
async function fetchNews() {
    try {
        const allNews = [];
        
        for (const source of newsSources) {
            try {
                const response = await axios.get(source.url, {
                    timeout: 15000,
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
                    }
                });
                
                const $ = cheerio.load(response.data);
                
                // Haber başlıklarını çek
                $(source.selectors.headlines).each((index, element) => {
                    if (index < 8) {
                        const title = $(element).text().trim().replace(/\s+/g, ' ');
                        if (title && title.length > 15 && title.length < 200) {
                            let url = $(element).attr('href');
                            if (url && !url.startsWith('http')) {
                                url = new URL(url, source.url).href;
                            }
                            
                            allNews.push({
                                title: title,
                                source: source.name,
                                url: url || source.url,
                                timestamp: new Date().toISOString()
                            });
                        }
                    }
                });
                
                // 1 saniye bekle (rate limiting)
                await new Promise(resolve => setTimeout(resolve, 1000));
                
            } catch (error) {
                console.log(`❌ ${source.name} haberleri çekilemedi:`, error.message);
            }
        }
        
        // Benzersiz haberleri seç (başlığa göre)
        const uniqueNews = allNews.filter((news, index, self) => 
            index === self.findIndex(n => n.title === news.title)
        );
        
        return uniqueNews.slice(0, 12);
    } catch (error) {
        console.log('❌ Haber çekme hatası:', error.message);
        return getFallbackNews();
    }
}

// Fallback haberler (API çalışmazsa)
function getFallbackNews() {
    const fallbackNews = [
        {
            title: "Türkiye'de Teknoloji Sektörü Rekor Büyüme Kaydetti",
            source: "GYT Haber",
            url: "https://www.gythaber.com",
            timestamp: new Date().toISOString()
        },
        {
            title: "Dolar ve Euro'da Tarihi Düşüş: Merkez Bankası Kararı Etkili Oldu",
            source: "GYT Ekonomi",
            url: "https://www.gythaber.com",
            timestamp: new Date().toISOString()
        },
        {
            title: "Süper Lig'de Tarihi Final: İki Dev Takım Şampiyonluk İçin Karşı Karşıya",
            source: "GYT Spor",
            url: "https://www.gythaber.com",
            timestamp: new Date().toISOString()
        },
        {
            title: "Bilim İnsanları Kansere Çare Buldu: Yeni Tedavi Yöntemi Başarıya Ulaştı",
            source: "GYT Sağlık",
            url: "https://www.gythaber.com",
            timestamp: new Date().toISOString()
        }
    ];
    
    return fallbackNews;
}

// Haber mesajı formatlama
function formatNewsMessage(news) {
    let message = `📰 *GYT HABER GÜNDEM* 📰\n\n`;
    message += `_${new Date().toLocaleString('tr-TR', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })}_\n\n`;
    
    // Haberleri karıştır
    const shuffledNews = news.sort(() => Math.random() - 0.5);
    
    shuffledNews.slice(0, 8).forEach((item, index) => {
        message += `*${index + 1}. ${item.title}*\n`;
        message += `📍 Kaynak: ${item.source}\n\n`;
    });
    
    message += `🔔 _Bir sonraki güncelleme yakında..._\n`;
    message += `📊 ${Object.keys(users).length} aktif kullanıcı`;
    
    return message;
}

// Zaman ayarları komutları
bot.onText(/\/yarimsaat/, (msg) => {
    const chatId = msg.chat.id;
    if (users[chatId]) {
        users[chatId].subscriptionType = 'half_hour';
        users[chatId].lastSent = Date.now();
        
        bot.sendMessage(chatId, '⏰ *Bildirimler yarım saatte bir gönderilecek!*\n\n_Gündemden anında haberdar olun!_ 📈', {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [[
                    { text: '🚀 Hemen Haber Al', callback_data: 'send_now' }
                ]]
            }
        });
        
        console.log(`⏰ ${users[chatId].username} yarım saatlik bildirime geçti`);
    }
});

bot.onText(/\/saatlik/, (msg) => {
    const chatId = msg.chat.id;
    if (users[chatId]) {
        users[chatId].subscriptionType = 'hourly';
        users[chatId].lastSent = Date.now();
        
        bot.sendMessage(chatId, '⏰ *Bildirimler saatte bir gönderilecek!*\n\n_Türkiye ve dünya gündemi sizlerle!_ 🌍', {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [[
                    { text: '🚀 Hemen Haber Al', callback_data: 'send_now' }
                ]]
            }
        });
        
        console.log(`⏰ ${users[chatId].username} saatlik bildirime geçti`);
    }
});

bot.onText(/\/ikisaat/, (msg) => {
    const chatId = msg.chat.id;
    if (users[chatId]) {
        users[chatId].subscriptionType = 'two_hours';
        users[chatId].lastSent = Date.now();
        
        bot.sendMessage(chatId, '⏰ *Bildirimler iki saatte bir gönderilecek!*\n\n_Son dakika gelişmeleri takip altında!_ 🔥', {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [[
                    { text: '🚀 Hemen Haber Al', callback_data: 'send_now' }
                ]]
            }
        });
        
        console.log(`⏰ ${users[chatId].username} iki saatlik bildirime geçti`);
    }
});

// Anlık haber komutu
bot.onText(/\/simdi/, async (msg) => {
    const chatId = msg.chat.id;
    
    const loadingMsg = await bot.sendMessage(chatId, '🔄 *Güncel haberler çekiliyor...*\n\n_Biraz bekleyin, gündem hazırlanıyor!_ 📡', {
        parse_mode: 'Markdown'
    });
    
    try {
        const news = await fetchNews();
        if (news.length > 0) {
            const message = formatNewsMessage(news);
            await bot.editMessageText(message, {
                chat_id: chatId,
                message_id: loadingMsg.message_id,
                parse_mode: 'Markdown',
                reply_markup: {
                    inline_keyboard: [[
                        { text: '🔄 Yenile', callback_data: 'send_now' }
                    ]]
                }
            });
            
            console.log(`📰 ${users[chatId]?.username || 'Kullanıcı'} anlık haber aldı`);
        } else {
            await bot.editMessageText('❌ *Şu anda haber çekilemiyor.*\n\n_Lütfen biraz sonra tekrar deneyin._ 🔄', {
                chat_id: chatId,
                message_id: loadingMsg.message_id,
                parse_mode: 'Markdown'
            });
        }
    } catch (error) {
        await bot.editMessageText('❌ *Haber çekilirken bir hata oluştu.*\n\n_Teknik ekibimiz sorunu çözüyor._ 🔧', {
            chat_id: chatId,
            message_id: loadingMsg.message_id,
            parse_mode: 'Markdown'
        });
    }
});

// Bildirimleri durdur
bot.onText(/\/durdur/, (msg) => {
    const chatId = msg.chat.id;
    if (users[chatId]) {
        users[chatId].subscribed = false;
        bot.sendMessage(chatId, '🔕 *Bildirimler durduruldu!*\n\n_Tekrar başlatmak için /start yazabilirsiniz._ 💫', {
            parse_mode: 'Markdown'
        });
        
        console.log(`🔕 ${users[chatId].username} bildirimleri durdurdu`);
    }
});

// İstatistik komutu
bot.onText(/\/istatistik/, (msg) => {
    const chatId = msg.chat.id;
    
    const totalUsers = Object.keys(users).length;
    const activeUsers = Object.values(users).filter(u => u.subscribed).length;
    const subscriptionStats = getSubscriptionStats();
    
    const statsMessage = `
📊 *GYT HABER BOT İSTATİSTİKLERİ*

👥 Toplam Kullanıcı: ${totalUsers}
✅ Aktif Kullanıcı: ${activeUsers}
📈 Aktivite Oranı: ${((activeUsers / totalUsers) * 100).toFixed(1)}%

⏰ *Bildirim Dağılımı:*
${subscriptionStats.half_hour} kullanıcı - Yarım Saat
${subscriptionStats.hourly} kullanıcı - 1 Saat  
${subscriptionStats.two_hours} kullanıcı - 2 Saat

🕒 Son Güncelleme: ${new Date().toLocaleString('tr-TR')}
    `;
    
    bot.sendMessage(chatId, statsMessage, { 
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: [[
                { text: '🔄 Yenile', callback_data: 'refresh_stats' }
            ]]
        }
    });
});

// Ayarlar komutu
bot.onText(/\/ayarlar/, (msg) => {
    const chatId = msg.chat.id;
    if (users[chatId]) {
        const user = users[chatId];
        const settings = `
⚙️ *Kullanıcı Ayarları*

👤 Kullanıcı: ${user.username}
📞 Chat ID: ${user.chatId}
🔔 Durum: ${user.subscribed ? '✅ Aktif' : '❌ Pasif'}
⏰ Bildirim: ${getSubscriptionText(user.subscriptionType)}
📅 Katılma: ${new Date(user.joinDate).toLocaleDateString('tr-TR')}

_Son güncelleme: ${new Date(user.lastSent).toLocaleString('tr-TR')}_
        `;
        
        bot.sendMessage(chatId, settings, {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [
                    [
                        { text: '⏰ Yarım Saat', callback_data: 'half_hour' },
                        { text: '⏰ 1 Saat', callback_data: 'hourly' },
                        { text: '⏰ 2 Saat', callback_data: 'two_hours' }
                    ],
                    [
                        { text: '🚀 Hemen Haber', callback_data: 'send_now' },
                        { text: '🔕 Durdur', callback_data: 'stop' },
                        { text: '📊 İstatistik', callback_data: 'stats' }
                    ]
                ]
            }
        });
    }
});

// Yardım komutu
bot.onText(/\/yardim/, (msg) => {
    const chatId = msg.chat.id;
    const helpMessage = `
🤖 *GYT HABER BOT YARDIM* 📚

*Komut Listesi:*

/start - Botu başlat ve kayıt ol
/yarimsaat - Yarım saatte bir haber
/saatlik - Saatte bir haber  
/ikisaat - İki saatte bir haber
/simdi - Hemen haber al
/durdur - Bildirimleri durdur
/ayarlar - Ayarları görüntüle
/istatistik - Bot istatistikleri
/yardim - Bu yardım mesajı

*Özellikler:*
• Otomatik haber güncellemeleri
• Çoklu haber kaynağı (Hürriyet, Milliyet, NTV, BBC)
• Kişiselleştirilmiş zaman aralıkları
• Gerçek zamanlı gündem takibi
• 7/24 kesintisiz hizmet

_Sorularınız için: @gytdestek_
    `;
    
    bot.sendMessage(chatId, helpMessage, { 
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: [[
                { text: '🚀 Hemen Deneyin', callback_data: 'send_now' }
            ]]
        }
    });
});

// Callback query handler
bot.on('callback_query', async (callbackQuery) => {
    const message = callbackQuery.message;
    const chatId = message.chat.id;
    const data = callbackQuery.data;

    if (users[chatId]) {
        switch (data) {
            case 'half_hour':
                users[chatId].subscriptionType = 'half_hour';
                users[chatId].lastSent = Date.now();
                bot.answerCallbackQuery(callbackQuery.id, { text: '⏰ Yarım saatte bir haber gönderilecek!' });
                break;
                
            case 'hourly':
                users[chatId].subscriptionType = 'hourly';
                users[chatId].lastSent = Date.now();
                bot.answerCallbackQuery(callbackQuery.id, { text: '⏰ Saatte bir haber gönderilecek!' });
                break;
                
            case 'two_hours':
                users[chatId].subscriptionType = 'two_hours';
                users[chatId].lastSent = Date.now();
                bot.answerCallbackQuery(callbackQuery.id, { text: '⏰ İki saatte bir haber gönderilecek!' });
                break;
                
            case 'send_now':
                bot.answerCallbackQuery(callbackQuery.id, { text: '🔄 Haberler çekiliyor...' });
                const news = await fetchNews();
                if (news.length > 0) {
                    const message = formatNewsMessage(news);
                    bot.sendMessage(chatId, message, { 
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[
                                { text: '🔄 Yenile', callback_data: 'send_now' }
                            ]]
                        }
                    });
                }
                break;
                
            case 'stop':
                users[chatId].subscribed = false;
                bot.answerCallbackQuery(callbackQuery.id, { text: '🔕 Bildirimler durduruldu!' });
                break;
                
            case 'stats':
                bot.answerCallbackQuery(callbackQuery.id, { text: '📊 İstatistikler hazırlanıyor...' });
                const totalUsers = Object.keys(users).length;
                const activeUsers = Object.values(users).filter(u => u.subscribed).length;
                
                const stats = `
📊 *Gerçek Zamanlı İstatistikler*

👥 Toplam Kullanıcı: ${totalUsers}
✅ Aktif Kullanıcı: ${activeUsers}
📈 Aktivite: ${((activeUsers / totalUsers) * 100).toFixed(1)}%

_Sistem sağlıklı çalışıyor!_ ✅
                `;
                
                bot.sendMessage(chatId, stats, { parse_mode: 'Markdown' });
                break;
                
            case 'refresh_stats':
                bot.answerCallbackQuery(callbackQuery.id, { text: '📊 İstatistikler yenileniyor...' });
                // İstatistik mesajını yenile
                break;
        }
    }
});

// Yardımcı fonksiyonlar
function getSubscriptionText(type) {
    const types = {
        'half_hour': '⏰ Yarım Saatte Bir',
        'hourly': '⏰ Saatte Bir',
        'two_hours': '⏰ İki Saatte Bir'
    };
    return types[type] || '⏰ Bilinmiyor';
}

function getIntervalTime(type) {
    const intervals = {
        'half_hour': 30 * 60 * 1000,
        'hourly': 60 * 60 * 1000,
        'two_hours': 2 * 60 * 60 * 1000
    };
    return intervals[type] || 60 * 60 * 1000;
}

function getSubscriptionStats() {
    const stats = {
        half_hour: 0,
        hourly: 0,
        two_hours: 0
    };
    
    Object.values(users).forEach(user => {
        if (user.subscribed && stats[user.subscriptionType] !== undefined) {
            stats[user.subscriptionType]++;
        }
    });
    
    return stats;
}

// Otomatik haber gönderme
setInterval(async () => {
    const now = Date.now();
    let sentCount = 0;
    let errorCount = 0;
    
    for (const chatId in users) {
        const user = users[chatId];
        
        if (user.subscribed) {
            const interval = getIntervalTime(user.subscriptionType);
            
            if (now - user.lastSent >= interval) {
                try {
                    const news = await fetchNews();
                    if (news.length > 0) {
                        const message = formatNewsMessage(news);
                        await bot.sendMessage(chatId, message, { 
                            parse_mode: 'Markdown',
                            reply_markup: {
                                inline_keyboard: [[
                                    { text: '🔄 Yenile', callback_data: 'send_now' }
                                ]]
                            }
                        });
                        user.lastSent = now;
                        sentCount++;
                        
                        // Rate limiting için bekle
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                } catch (error) {
                    console.log(`❌ Haber gönderilemedi ${chatId}:`, error.message);
                    errorCount++;
                }
            }
        }
    }
    
    if (sentCount > 0) {
        console.log(`✅ ${sentCount} kullanıcıya haber gönderildi (Hatalar: ${errorCount})`);
    }
}, 60000);

// Hata yönetimi
bot.on('polling_error', (error) => {
    console.log('❌ Polling error:', error.message);
});

bot.on('error', (error) => {
    console.log('❌ Bot error:', error.message);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('🛑 Bot kapatılıyor...');
    bot.stopPolling();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('🛑 Bot kapatılıyor...');
    bot.stopPolling();
    process.exit(0);
});

console.log('🤖 GYT HABER BOT Render üzerinde başlatıldı...');
console.log('📱 Bot aktif ve mesaj bekliyor...');
console.log('🌐 Health check endpoint: http://localhost:' + PORT);
console.log('🔑 Environment kontrol: ' + (TOKEN ? '✅ Token mevcut' : '❌ Token yok'));

// Başlangıç testi
async function initializeBot() {
    try {
        const news = await fetchNews();
        console.log(`✅ Bot başarıyla başlatıldı. ${news.length} haber çekildi.`);
        console.log(`📊 ${Object.keys(users).length} kullanıcı kayıtlı`);
    } catch (error) {
        console.log('❌ Bot başlatma hatası:', error.message);
    }
}

initializeBot();

module.exports = { bot, app };
