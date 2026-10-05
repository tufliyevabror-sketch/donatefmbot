"""3 til (uz/ru/en) — bot va webapp uchun."""

I18N = {
    "uz": {
        # Asosiy
        "start": (
            "🎮 <b>Game Shop</b> botiga xush kelibsiz!\n\n"
            "Do'konimiz <b>Telegram Mini App</b>'da ishlaydi.\n"
            "🛍 <b>Do'kon</b> tugmasini bosib katalogni oching.\n\n"
            "Bo'limlar: 🔥 Free Fire • 🪂 PUBG • 🥷 Mobile Legends\n"
            "👾 Roblox • 🔫 Standoff 2 • ⭐️ Stars • 👑 TG Premium"
        ),
        "menu_text": "🏠 <b>Bosh sahifa</b>\n\nKerakli bo'limni tanlang 👇",
        "games_title": "🛒 <b>O'yinlar katalogi</b>\n\nTanlang 👇",
        "banned": "⛔️ Siz bloklangansiz. Admin bilan bog'laning.",

        # Balans
        "balance_title": "💰 <b>Sizning balansingiz</b>",
        "balance_label": "Balans",
        "total_topup_label": "Jami to'ldirilgan",
        "topup_hint": "Balansni to'ldirish uchun quyidan usulni tanlang 👇",
        "topup_menu": "🚀 <b>Hisobni to'ldirish</b>\n\nUsulni tanlang:",
        "pay_center": "💳 <b>TO'LOV MARKAZI ✨</b>",
        "pay_amount": "To'lov summasi",
        "copy_hint": "®️ Eslatma: raqamni ustiga bosib (copy) qilib oling",
        "receipt_required": "⌛ Shart: To'lov kvitansiyasini (chek) yuborish majburiy!",
        "send_receipt": "Summani kartaga o'tkazing va <b>chek/screenshot</b> ni shu yerga yuboring.",
        "after_approval": "Admin tasdiqlagach balansingizga qo'shiladi. ✅",
        "receipt_accepted": "Chek qabul qilindi!",
        "payment_id": "To'lov raqami",
        "wait_admin": "Admin tekshirib, tasdiqlashini kuting... ⏳",

        # To'lov usullari
        "topup_card": "💳 <b>Karta orqali to'lov</b>",
        "topup_stars": "⭐️ <b>Telegram Stars orqali to'ldirish</b>",
        "card_topup_intro": "Summani tanlang yoki o'zingiz yozing:",
        "choose_pay_method": "To'lov usulini tanlang 👇",

        # Buyurtma
        "order_info": "Buyurtma ma'lumotlari",
        "game_label": "O'yin",
        "package_label": "Paket",
        "price_label": "Narx",
        "game_id_label": "O'yin ID",
        "order_created": "✅ Buyurtma yaratildi! Raqam: <code>#{order_id}</code>\nAdmin tasdiqlashini kuting.",
        "order_waiting": "Iltimos, admin tomonidan bajarilishini kuting. ⏳",
        "too_low_balance": "❌ Hisobingizda mablag' yetarli emas!\n\n💰 <b>Balans</b> bo'limidan to'ldiring.",
        "balance_added": "<b>={balance}</b> hisobingizga qo'shildi.",

        # Tarix
        "history_title": "Tarix",
        "orders_label": "Buyurtmalar",
        "payments_label": "To'lovlar",
        "empty": "Hozircha yo'q.",

        # Sozlamalar
        "settings_title": "⚙️ <b>Sozlamalar</b>",
        "name_label": "Ism",
        "username_label": "Username",
        "language_label": "Til",
        "reg_date_label": "Ro'yxatdan o'tgan",
        "need_help": "Yordam kerak bo'lsa, admin bilan bog'laning.",

        # Admin
        "admin_menu": "👑 <b>Admin panel</b>\n\nBo'limni tanlang:",
        "admin_stats": "Statistika",
        "users_label": "Foydalanuvchilar",
        "revenue_label": "Daromad",
        "topups_label": "To'ldirilgan",
        "today_orders": "Bugungi buyurtmalar",
        "month_users": "Oylik foydalanuvchilar",
        "month_new_users": "Yangi foydalanuvchilar",
        "month_revenue": "Oylik daromad",
        "month_topups": "Oylik to'ldirishlar",
        "order_label": "Buyurtma",
        "payment_label": "To'lov",
        "user_profile": "Foydalanuvchi profili",
        "admin_settings": "Sozlamalar",

        # Referral
        "referral_title": "🤝 <b>Do'stlarni taklif qilish</b>",
        "referral_hint": "Tavsiya qilingan hisobdan pul qo'shilganda {percent}% keshbek olasiz.",
        "your_link": "Sizning havolangiz",
        "stats": "Statistika",

        # Promo
        "promo_invalid": "❌ Promokod ishlamaydi.",
        "promo_expired": "❌ Promokod muddati tugagan.",
        "promo_limit": "❌ Promokod limiti tugagan.",
        "promo_used": "❌ Siz bu promokodni allaqachon ishlatgansiz.",
        "promo_ok": "🎉 Promokod qabul qilindi!",
        "enter_promo": "Promokod kiriting:",

        # Umumiy tugmalar
        "cancel": "❌ Bekor qilindi.",
        "back": "🔙 Orqaga",
        "home": "🏠 Bosh sahifa",
        "done": "✅ Bajarildi",
        "refused": "❌ Rad etildi",
        "phone_ok": "✅ Telefon saqlandi.",
        "no_photo": "⚠️ Iltimos, rasm yuboring.",
        "no_admin": "❌ Sizda admin huquqi yo'q.",
        "send_photo_hint": "Chek/screenshot yuboring:",

        # O'yin ichida
        "choose_package": "👇 Paketni tanlang:",

        # Buyurtma holati bildirishnomalari
        "order_queued": (
            "⏳ <b>Buyurtma qabul qilindi.</b>\n\n"
            "🧾 Buyurtma: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "🆔 O'yin ID: <code>{player}</code>\n"
            "💰 Narx: <b>{price} so'm</b>\n\n"
            "Bajarilishini kuting — holatni <code>/track {id}</code> bilan kuzatasiz."
        ),
        "order_payment_required": (
            "💳 <b>Buyurtma uchun to'lov kutilmoqda.</b>\n\n"
            "🧾 Buyurtma: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "💰 Summa: <b>{price} so'm</b>\n\n"
            "To'lov tasdiqlangach buyurtma ishga tushadi."
        ),
        "order_done": (
            "✅ <b>Buyurtmangiz bajarildi!</b>\n\n"
            "🎮 {game}\n"
            "📦 {package}\n"
            "🆔 O'yin ID: <code>{player}</code>\n"
            "💰 Narx: <b>{price} so'm</b>"
        ),
        "order_done_footer": "🧾 Buyurtma: <code>{id}</code> — rahmat! 🎉",
        "order_reason_admin": "Admin bekor qildi",

        # PRO obuna
        "pro_title": "💎 PRO obuna",
        "pro_price": "💰 Oylik narx: <b>{price} so'm</b>\n🏷 Chegirma: <b>{percent}%</b> (−{saved} so'm)",
        "pro_price_now": "🏷 Hozirgi narx: <b>{price} so'm</b> — 30 kun",
        "pro_perks": (
            "💎 <b>PRO afzalliklari:</b>\n\n"
            "• Keshbek: <b>{base}% → {full}%</b> (har bir to'lovda)\n"
            "• Profilda 💎 PRO nishoni\n"
            "• Yangi paket va aksiyalarga erta kirish"
        ),
        "pro_active": "✅ <b>PRO obuna faol.</b>\n📅 Muddat: <b>{date}</b> gacha",
        "pro_inactive": "❌ <b>PRO obuna yo'q.</b>\n\nQuyidagi tugma orqali 30 kunga yoqishingiz mumkin.",
        "pro_buy_ok": (
            "✅ <b>PRO obuna yoqildi!</b>\n\n"
            "📅 Muddat: <b>{date}</b> gacha\n"
            "💳 Yechildi: <b>{price} so'm</b>\n"
            "💎 Keshbek foizingiz endi <b>{full}%</b>."
        ),
        "pro_no_balance": (
            "❌ <b>Balans yetarli emas.</b>\n\n"
            "Kerakli: <b>{price} so'm</b>\n"
            "Sizning balansingiz: <b>{balance} so'm</b>"
        ),
        "pro_disabled": "🔒 PRO obuna hozircha o'chirilgan. Tez orada qaytadi.",
        "pro_expired": (
            "⌛️ <b>PRO obunangiz tugadi.</b>\n\n"
            "📅 Muddat: <b>{date}</b>\n"
            "Keshbek foizingiz {base}% ga qaytdi.\n\n"
            "Davom ettirish uchun: /pro"
        ),
        "order_fail_hint": "ℹ️ Sabab: {detail}",
        "order_auto_fail": (
            "⏳ <b>Buyurtmangiz avtomatik yuborilmadi.</b>\n\n"
            "🧾 Buyurtma: <code>{id}</code>\n"
            "📦 {package}\n"
            "ℹ️ Sabab: <code>{detail}</code>\n\n"
            "Admin tekshirmoqda. 🙏"
        ),
        "order_reason_delivery": "Yetkazib berishda xatolik",
        "order_rejected": (
            "↩️ <b>Buyurtma bekor qilindi.</b>\n\n"
            "🧾 Buyurtma: <code>{id}</code>\n"
            "📦 {package}\n"
            "💰 <b>{price} so'm</b> balansingizga qaytarildi.\n\n"
            "Sabab: {detail}"
        ),
        "order_reminder": (
            "⏳ <b>Buyurtmangiz hali bajarilmagan.</b>\n\n"
            "🧾 Buyurtma: <code>{id}</code>\n"
            "🎮 {game} — {package}\n\n"
            "Holatni <code>/track {id}</code> bilan tekshiring.\n"
            "⚠️ Kutish vaqti: {minutes} daqiqa."
        ),

        # Broadcast
        "broadcast_start": "📢 <b>Xabar yuborish</b>\n\nMatnni yuboring (HTML ruxsat etiladi).",
        "broadcast_preview": "✅ Tayyor. <b>{count}</b> ta foydalanuvchiga yuborilsin?",

        # Yangi qo'shilgan
        "admin_search_prompt": "🔎 <b>Qidiruv</b>\n\nID, username yoki ism yozing (masalan: 123456789 yoki @username):",
        "phone": "Telefon",
        "keshbek_label": "Referral keshbek",
        "status_label": "Holat",
        "banned_label": "Bloklangan",
        "active": "Faol",
        "contact_admin": "Murojaat uchun",
        "delivery_title": "Avto-delivery",
        "pending_orders": "Kutilayotgan buyurtmalar",
        "delivery_hint": "Provider sozlash: <code>/set delivery_api_url &lt;url&gt;</code> <code>/set delivery_provider custom</code>",

        # Paket va o'yin
    },
    "ru": {
        # Asosiy
        "start": (
            "🎮 Добро пожаловать в <b>Game Shop</b>!\n\n"
            "Магазин работает в <b>Telegram Mini App</b>.\n"
            "🛍 Нажмите кнопку <b>Магазин</b>, чтобы открыть каталог.\n\n"
            "Категории: 🔥 Free Fire • 🪂 PUBG • 🥷 Mobile Legends\n"
            "👾 Roblox • 🔫 Standoff 2 • ⭐️ Stars • 👑 TG Premium"
        ),
        "menu_text": "<b>🏠 Главная</b>\n\nВыберите раздел 👇",
        "games_title": "<b>🛒 Каталог игр</b>\n\nВыберите 👇",
        "banned": "⛔️ Вы заблокированы. Обратитесь к администратору.",

        # Balans
        "balance_title": "<b>💰 Ваш баланс</b>",
        "balance_label": "Баланс",
        "total_topup_label": "Всего пополнено",
        "topup_hint": "Выберите способ пополнения ниже 👇",
        "topup_menu": "🚀 <b>Пополнение счёта</b>\n\nВыберите способ:",
        "pay_center": "💳 <b>ЦЕНТР ОПЛАТЫ ✨</b>",
        "pay_amount": "Сумма оплаты",
        "copy_hint": "®️ Нажмите на номер, чтобы скопировать",
        "receipt_required": "⌛ Условие: отправка чека обязательна!",
        "send_receipt": "Переведите сумму на карту и отправьте <b>чек/скриншот</b> сюда.",
        "after_approval": "После подтверждения админом средства зачислятся. ✅",
        "receipt_accepted": "Чек принят!",
        "payment_id": "Номер платежа",
        "wait_admin": "Ожидайте проверки администратором... ⏳",

        # To'lov usullari
        "topup_card": "💳 <b>Оплата картой</b>",
        "topup_stars": "⭐️ <b>Пополнение через Telegram Stars</b>",
        "card_topup_intro": "Выберите сумму или введите свою:",
        "choose_pay_method": "Выберите способ оплаты 👇",

        # Buyurtma
        "order_info": "Информация о заказе",
        "game_label": "Игра",
        "package_label": "Пакет",
        "price_label": "Цена",
        "game_id_label": "ID игры",
        "order_created": "✅ Заказ создан! Номер: <code>#{order_id}</code>\nОжидайте подтверждения администратора.",
        "order_waiting": "Пожалуйста, дождитесь выполнения администратором. ⏳",
        "too_low_balance": "❌ Недостаточно средств!\n\n💰 Пополните в разделе <b>Баланс</b>.",
        "balance_added": "<b>={balance}</b> зачислено на счёт.",

        # Tarix
        "history_title": "История",
        "orders_label": "Заказы",
        "payments_label": "Платежи",
        "empty": "Пока пусто.",

        # Sozlamalar
        "settings_title": "⚙️ <b>Настройки</b>",
        "name_label": "Имя",
        "username_label": "Username",
        "language_label": "Язык",
        "reg_date_label": "Дата регистрации",
        "need_help": "Нужна помощь? Обратитесь к администратору.",

        # Admin
        "admin_menu": "👑 <b>Админ-панель</b>\n\nВыберите раздел:",
        "admin_stats": "Статистика",
        "users_label": "Пользователи",
        "revenue_label": "Выручка",
        "topups_label": "Пополнения",
        "today_orders": "Заказы за сегодня",
        "month_users": "Пользователи за месяц",
        "month_new_users": "Новые пользователи",
        "month_revenue": "Выручка за месяц",
        "month_topups": "Пополнения за месяц",
        "order_label": "Заказ",
        "payment_label": "Платёж",
        "user_profile": "Профиль пользователя",
        "admin_settings": "Настройки",

        # Referral
        "referral_title": "🤝 <b>Пригласить друзей</b>",
        "referral_hint": "Когда друг пополнит счёт, вы получите кешбек {percent}%.",
        "your_link": "Ваша ссылка",
        "stats": "Статистика",

        # Promo
        "promo_invalid": "❌ Промокод недействителен.",
        "promo_expired": "❌ Срок промокода истёк.",
        "promo_limit": "❌ Лимит промокода исчерпан.",
        "promo_used": "❌ Вы уже использовали этот промокод.",
        "promo_ok": "🎉 Промокод принят!",
        "enter_promo": "Введите промокод:",

        # Umumiy tugmalar
        "cancel": "❌ Отменено.",
        "back": "🔙 Назад",
        "home": "🏠 Главная",
        "done": "✅ Готово",
        "refused": "❌ Отклонено",
        "phone_ok": "✅ Телефон сохранён.",
        "no_photo": "⚠️ Пожалуйста, отправьте фото.",
        "no_admin": "❌ У вас нет прав администратора.",
        "send_photo_hint": "Отправьте чек/скриншот:",

        # O'yin ichida
        "choose_package": "👇 Выберите пакет:",

        # Уведомления о статусе заказа
        "order_queued": (
            "⏳ <b>Зазак принят.</b>\n\n"
            "🧾 Заказ: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "🆔 ID игрока: <code>{player}</code>\n"
            "💰 Цена: <b>{price} сум</b>\n\n"
            "Ожидайте выполнения — статус: <code>/track {id}</code>."
        ),
        "order_payment_required": (
            "💳 <b>Ожидается оплата за заказ.</b>\n\n"
            "🧾 Заказ: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "💰 Сумма: <b>{price} сум</b>\n\n"
            "Заказ начнётся после подтверждения оплаты."
        ),
        "order_done": (
            "✅ <b>Ваш заказ выполнен!</b>\n\n"
            "🎮 {game}\n"
            "📦 {package}\n"
            "🆔 ID игрока: <code>{player}</code>\n"
            "💰 Цена: <b>{price} сум</b>"
        ),
        "order_done_footer": "🧾 Заказ: <code>{id}</code> — спасибо! 🎉",
        "order_reason_admin": "Отменено администратором",

        # PRO подписка
        "pro_title": "💎 PRO подписка",
        "pro_price": "💰 Цена в месяц: <b>{price} сум</b>\n🏷 Скидка: <b>{percent}%</b> (−{saved} сум)",
        "pro_price_now": "🏷 Текущая цена: <b>{price} сум</b> — 30 дней",
        "pro_perks": (
            "💎 <b>Преимущества PRO:</b>\n\n"
            "• Кешбэк: <b>{base}% → {full}%</b> (с каждого платежа)\n"
            "• Значок 💎 PRO в профиле\n"
            "• Ранний доступ к новым пакетам и акциям"
        ),
        "pro_active": "✅ <b>PRO подписка активна.</b>\n📅 До: <b>{date}</b>",
        "pro_inactive": "❌ <b>PRO подписки нет.</b>\n\nМожно активировать на 30 дней кнопкой ниже.",
        "pro_buy_ok": (
            "✅ <b>PRO подписка активирована!</b>\n\n"
            "📅 Действует до: <b>{date}</b>\n"
            "💳 Списано: <b>{price} сум</b>\n"
            "💎 Ваш кешбэк теперь <b>{full}%</b>."
        ),
        "pro_no_balance": (
            "❌ <b>Недостаточно средств.</b>\n\n"
            "Нужно: <b>{price} сум</b>\n"
            "Ваш баланс: <b>{balance} сум</b>"
        ),
        "pro_disabled": "🔒 Пока подписка отключена. Скоро вернёмся.",
        "pro_expired": (
            "⌛️ <b>Ваша PRO подписка закончилась.</b>\n\n"
            "📅 Действовала до: <b>{date}</b>\n"
            "Ваш кешбэк вернулся к {base}%.\n\n"
            "Продлить: /pro"
        ),
        "order_fail_hint": "ℹ️ Причина: {detail}",
        "order_auto_fail": (
            "⏳ <b>Заказ не был отправлен автоматически.</b>\n\n"
            "🧾 Заказ: <code>{id}</code>\n"
            "📦 {package}\n"
            "ℹ️ Причина: <code>{detail}</code>\n\n"
            "Администратор проверяет. 🙏"
        ),
        "order_reason_delivery": "Ошибка доставки",
        "order_rejected": (
            "↩️ <b>Заказ отменён.</b>\n\n"
            "🧾 Заказ: <code>{id}</code>\n"
            "📦 {package}\n"
            "💰 <b>{price} сум</b> возвращено на баланс.\n\n"
            "Причина: {detail}"
        ),
        "order_reminder": (
            "⏳ <b>Ваш заказ ещё не выполнен.</b>\n\n"
            "🧾 Заказ: <code>{id}</code>\n"
            "🎮 {game} — {package}\n\n"
            "Проверьте статус: <code>/track {id}</code>.\n"
            "⚠️ Время ожидания: {minutes} мин."
        ),

        # Broadcast
        "broadcast_start": "📢 <b>Рассылка</b>\n\nОтправьте текст (HTML разрешён).",
        "broadcast_preview": "✅ Готово. Отправить <b>{count}</b> пользователям?",

        # Yangi qo'shilgan
        "admin_search_prompt": "🔎 <b>Поиск</b>\n\nВведите ID, username или имя (например: 123456789 или @username):",
        "phone": "Телефон",
        "keshbek_label": "Реферальный кешбек",
        "status_label": "Статус",
        "banned_label": "Заблокирован",
        "active": "Активен",
        "contact_admin": "Для связи",
        "delivery_title": "Авто-доставка",
        "pending_orders": "Ожидающие заказы",
        "delivery_hint": "Настройка: <code>/set delivery_api_url &lt;url&gt;</code> <code>/set delivery_provider custom</code>",
    },
    "en": {
        # Asosiy
        "start": (
            "🎮 Welcome to <b>Game Shop</b>!\n\n"
            "Our shop runs as a <b>Telegram Mini App</b>.\n"
            "🛍 Tap the <b>Shop</b> button to open the catalogue.\n\n"
            "Categories: 🔥 Free Fire • 🪂 PUBG • 🥷 Mobile Legends\n"
            "👾 Roblox • 🔫 Standoff 2 • ⭐️ Stars • 👑 TG Premium"
        ),
        "menu_text": "<b>🏠 Home</b>\n\nChoose a section 👇",
        "games_title": "<b>🛒 Games catalog</b>\n\nSelect 👇",
        "banned": "⛔️ You are banned. Contact admin.",

        # Balance
        "balance_title": "<b>💰 Your Balance</b>",
        "balance_label": "Balance",
        "total_topup_label": "Total topped up",
        "topup_hint": "Choose a top-up method below 👇",
        "topup_menu": "🚀 <b>Top Up</b>\n\nSelect method:",
        "pay_center": "💳 <b>PAYMENT CENTER ✨</b>",
        "pay_amount": "Payment amount",
        "copy_hint": "®️ Tap number to copy",
        "receipt_required": "⌛ Required: send receipt (screenshot)!", 
        "send_receipt": "Transfer to card and send <b>receipt/screenshot</b> here.",
        "after_approval": "After admin approval, funds will be added. ✅",
        "receipt_accepted": "Receipt accepted!",
        "payment_id": "Payment ID",
        "wait_admin": "Waiting for admin verification... ⏳",

        # Payment methods
        "topup_card": "💳 <b>Card Payment</b>",
        "topup_stars": "⭐️ <b>Top Up via Telegram Stars</b>",
        "card_topup_intro": "Select amount or enter custom:",
        "choose_pay_method": "Choose payment method 👇",

        # Order
        "order_info": "Order details",
        "game_label": "Game",
        "package_label": "Package",
        "price_label": "Price",
        "game_id_label": "Game ID",
        "order_created": "✅ Order created! ID: <code>#{order_id}</code>\nWaiting for admin confirmation.",
        "order_waiting": "Please wait for admin confirmation. ⏳",
        "too_low_balance": "❌ Insufficient balance!\n\n💰 Top up in <b>Balance</b> section.",
        "balance_added": "<b>={balance}</b> added to your balance.",

        # History
        "history_title": "History",
        "orders_label": "Orders",
        "payments_label": "Payments",
        "empty": "Empty.",

        # Settings
        "settings_title": "⚙️ <b>Settings</b>",
        "name_label": "Name",
        "username_label": "Username",
        "language_label": "Language",
        "reg_date_label": "Registered",
        "need_help": "Need help? Contact admin.",

        # Admin
        "admin_menu": "👑 <b>Admin Panel</b>\n\nSelect section:",
        "admin_stats": "Statistics",
        "users_label": "Users",
        "revenue_label": "Revenue",
        "topups_label": "Top-ups",
        "today_orders": "Today's orders",
        "month_users": "Monthly users",
        "month_new_users": "New users",
        "month_revenue": "Monthly revenue",
        "month_topups": "Monthly top-ups",
        "order_label": "Order",
        "payment_label": "Payment",
        "user_profile": "User Profile",
        "admin_settings": "Settings",

        # Referral
        "referral_title": "🤝 <b>Invite Friends</b>",
        "referral_hint": "Get {percent}% cashback when friend tops up.",
        "your_link": "Your link",
        "stats": "Stats",

        # Promo
        "promo_invalid": "❌ Invalid promo code.",
        "promo_expired": "❌ Promo code expired.",
        "promo_limit": "❌ Promo code limit reached.",
        "promo_used": "❌ You already used this promo code.",
        "promo_ok": "🎉 Promo code accepted!",
        "enter_promo": "Enter promo code:",

        # Common buttons
        "cancel": "❌ Cancelled.",
        "back": "🔙 Back",
        "home": "🏠 Home",
        "done": "✅ Done",
        "refused": "❌ Refused",
        "phone_ok": "✅ Phone saved.",
        "no_photo": "⚠️ Please send a photo.",
        "no_admin": "❌ No admin rights.",
        "send_photo_hint": "Send receipt/screenshot:",

        # Game
        "choose_package": "👇 Choose a package:",

        # Order status notifications
        "order_queued": (
            "⏳ <b>Your order has been accepted.</b>\n\n"
            "🧾 Order: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "🆔 Player ID: <code>{player}</code>\n"
            "💰 Price: <b>{price} UZS</b>\n\n"
            "Please wait — track it with <code>/track {id}</code>."
        ),
        "order_payment_required": (
            "💳 <b>Payment is required for this order.</b>\n\n"
            "🧾 Order: <code>{id}</code>\n"
            "🎮 {game} — {package}\n"
            "💰 Amount: <b>{price} UZS</b>\n\n"
            "The order starts once the payment is confirmed."
        ),
        "order_done": (
            "✅ <b>Your order is complete!</b>\n\n"
            "🎮 {game}\n"
            "📦 {package}\n"
            "🆔 Player ID: <code>{player}</code>\n"
            "💰 Price: <b>{price} UZS</b>"
        ),
        "order_done_footer": "🧾 Order: <code>{id}</code> — thank you! 🎉",
        "order_reason_admin": "Cancelled by an admin",

        # PRO subscription
        "pro_title": "💎 PRO subscription",
        "pro_price": "💰 Monthly price: <b>{price} UZS</b>\n🏷 Discount: <b>{percent}%</b> (−{saved} UZS)",
        "pro_price_now": "🏷 Current price: <b>{price} UZS</b> — 30 days",
        "pro_perks": (
            "💎 <b>PRO perks:</b>\n\n"
            "• Cashback: <b>{base}% → {full}%</b> (on every payment)\n"
            "• 💎 PRO badge on your profile\n"
            "• Early access to new packages and promos"
        ),
        "pro_active": "✅ <b>PRO subscription is active.</b>\n📅 Until: <b>{date}</b>",
        "pro_inactive": "❌ <b>No PRO subscription.</b>\n\nYou can activate it for 30 days with the button below.",
        "pro_buy_ok": (
            "✅ <b>PRO subscription activated!</b>\n\n"
            "📅 Valid until: <b>{date}</b>\n"
            "💳 Charged: <b>{price} UZS</b>\n"
            "💎 Your cashback is now <b>{full}%</b>."
        ),
        "pro_no_balance": (
            "❌ <b>Insufficient balance.</b>\n\n"
            "Required: <b>{price} UZS</b>\n"
            "Your balance: <b>{balance} UZS</b>"
        ),
        "pro_disabled": "🔒 PRO subscription is temporarily off. Back soon.",
        "pro_expired": (
            "⌛️ <b>Your PRO subscription has ended.</b>\n\n"
            "📅 It was valid until: <b>{date}</b>\n"
            "Your cashback is back to {base}%.\n\n"
            "Renew: /pro"
        ),
        "order_fail_hint": "ℹ️ Reason: {detail}",
        "order_auto_fail": (
            "⏳ <b>Your order could not be delivered automatically.</b>\n\n"
            "🧾 Order: <code>{id}</code>\n"
            "📦 {package}\n"
            "ℹ️ Reason: <code>{detail}</code>\n\n"
            "An admin is checking it. 🙏"
        ),
        "order_reason_delivery": "Delivery failed",
        "order_rejected": (
            "↩️ <b>Your order was cancelled.</b>\n\n"
            "🧾 Order: <code>{id}</code>\n"
            "📦 {package}\n"
            "💰 <b>{price} UZS</b> was returned to your balance.\n\n"
            "Reason: {detail}"
        ),
        "order_reminder": (
            "⏳ <b>Your order is still pending.</b>\n\n"
            "🧾 Order: <code>{id}</code>\n"
            "🎮 {game} — {package}\n\n"
            "Check the status: <code>/track {id}</code>.\n"
            "⚠️ Waiting: {minutes} minutes."
        ),

        # Broadcast
        "broadcast_start": "📢 <b>Broadcast</b>\n\nSend message (HTML allowed).",
        "broadcast_preview": "✅ Ready. Send to <b>{count}</b> users?",

        # Yangi qo'shilgan
        "admin_search_prompt": "🔎 <b>Search</b>\n\nEnter ID, username or name (e.g.: 123456789 or @username):",
        "phone": "Phone",
        "keshbek_label": "Referral cashback",
        "status_label": "Status",
        "banned_label": "Banned",
        "active": "Active",
        "contact_admin": "Contact",
        "delivery_title": "Auto-delivery",
        "pending_orders": "Pending orders",
        "delivery_hint": "Setup: <code>/set delivery_api_url &lt;url&gt;</code> <code>/set delivery_provider custom</code>",
    },
}


def t(lang, key, **kw):
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    text = I18N.get(lang, I18N["uz"]).get(key, I18N["uz"].get(key, key))
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    return text


# ==================== WEBAPP (frontend) i18n ====================
WEBAPP_I18N = {
    "uz": {
        "home": "Bosh sahifa", "history": "Tarix", "settings": "Sozlamalar",
        "balance": "Balans", "topup": "Hisobni to'ldirish",
        "pay_method": "To'lov usulini tanlang", "buy": "Sotib olish",
        "verify": "Tekshirish", "verifying": "Tekshirilmoqda...",
        "enter_id": "O'yin ID kiriting", "products": "MAHSULOTNI TANLANG",
        "cat_all": "Hammasi", "promo": "Chegirma kodlar",
        "promo_placeholder": "Promokod", "apply": "Qo'llash",
        "invite": "Do'stlarni taklif qilish", "invite_link": "Taklif havolasi",
        "copy": "Nusxalash", "copied": "Nusxalandi ✅",
        "orders": "Buyurtmalar", "finance": "Moliya",
        "save": "Saqlash", "phone": "Telefon raqami", "lang": "Til",
        "keshbek": "KESHBEK", "invited": "Taklif qilingan", "reward": "Bonus",
        "pay_amount": "To'lov", "pay": "To'lash", "close": "Tushunarli",
        "notifications": "Bildirishnomalar", "cart": "Savat", "theme": "Mavzu",
        "favorites": "Sevimlilar", "leaderboard": "Reyting", "empty": "Bo'sh",
        "receipt": "Chek", "reorder": "Qayta buyurtma", "rate": "Baholash",
        # --- index.html statik ---
        "bal_label": "Balansingiz", "topup_go": "To'ldirish",
        "referral_short": "Taklif", "promo_short": "Promo",
        "games": "O'YINLAR",
        "fav_empty_t": "Sevimlilar yo'q",
        "fav_empty_d": "O'yin kartochkasiga bosib ⭐️ belgini qo'shing — keyin shu yerda tez topasiz.",
        "view_games": "O'yinlarni ko'rish",
        "prod_empty_t": "Mahsulot yo'q",
        "prod_empty_d": "Bu kategoriyada hozircha mahsulot mavjud emas.",
        "add_cart": "Savatga", "amount": "Summa",
        "amount_ph": "Summani kiriting (so'm)",
        "guide": "Qo'llanma",
        "guide_body": "1. Usulni tanlang<br>2. Summani kiriting<br>3. To'lang va balansingiz avtomatik yoki admin tasdiqlashidan so'ng to'ladi",
        "refresh": "Yangilash", "services": "XIZMATLAR",
        "rating_count": "{0} ta baholash",
        "rating_hint": "Buyurtmangiz bajarilgach ⭐️ bilan baholang — bu xizmatni yaxshilashga yordam beradi.",
        "nav_admin": "Admin",
        "pay_with_bal": "Balans bilan", "pay_uzqr": "UzQR Tezkor", "pay_by_card": "Karta orqali",
        "ref_inst1": "Do'st taklif qilgan foydalanuvchi hisob to'ldirganda siz",
        "ref_inst2": "keshbek olasiz.",
        "ref_bonus": "Olingan bonus",
        "share": "Ulashish", "view_lb": "Reyting jadvalini ko'rish",
        "promo_inst1": "Promokodni kiriting — balansingizga bonus qo'shiladi.",
        "promo_inst2": "Kodlar: /promo KOD (botda) yoki bu yerga yozing.",
        "mark_read": "O'qilgan qilish", "clear_cart": "Tozalash",
        "lb_title": "Referral reytingi", "print": "PDF / Chop etish",
        "cancel": "Bekor qilish", "confirm": "Tasdiqlash",
        "admin_panel": "Admin panel", "tab_dash": "Boshqaruv",
        "tab_payments": "To'lovlar", "tab_users": "Foydalanuvchilar",
        "tab_promos": "Promokodlar", "tab_audit": "Audit",
        "pay_window": "To'lov oynasi", "favorite": "Sevimli",
        "user_label": "Foydalanuvchi", "banned_label": "Bloklangan",
        # --- app.js toasts/holatlar ---
        "err_network": "Server bilan bog'lanib bo'lmadi",
        "game_not_found": "O'yin topilmadi",
        "id_ok": "ID qabul qilindi ✅", "id_enter": "ID kiriting",
        "select_product": "Mahsulot tanlang",
        "err_generic": "Xatolik yuz berdi",
        "no_balance": "Balans yetarli emas. Balansni to'ldiring!",
        "send_receipt": "Chek/screenshot rasmni botga yuboring",
        "admin_not_found": "Admin topilmadi — bot orqali murojaat qiling",
        "wait_admin": "Admin tasdiqlashini kuting ✅",
        "cart_cleared": "Savat tozalandi",
        "enter_id_first": "Avval o'yin ID kiriting",
        "enter_amount": "Summa kiriting",
        "min_sum": "Minimal summa: {0} so'm",
        "min_amt": "Minimal: {0} so'm", "max_amt": "Maksimal: {0} so'm",
        "refreshed": "⟳ Yangilandi",
        "reorder_bad": "Bu buyurtmani qayta buyurtma qilib bo'lmaydi",
        "reorder_ok": "✅ Qayta buyurtma qabul qilindi!",
        "enter_number": "Raqam kiriting", "saved_ok": "Saqlandi ✅",
        "support_not_found": "Support topilmadi",
        "loading": "Yuklanmoqda...", "enter_promo": "Promokod kiriting",
        "all_read_ok": "O'qilgan qilindi ✅",
        "wrong_amount": "Noto'g'ri summa", "enter_code": "KOD kiriting",
        "fav_added": "⭐️ Sevimlilarga qo'shildi",
        "fav_removed": "☆ Olib tashlandi",
        "cart_removed": "🛒 Savatdan olib tashlandi",
        "cart_added": "🛒 Savatga qo'shildi",
        "promo_bad": "Promokod ishlamadi",
        "no_notifications": "Bildirishnomalar yo'q",
        "no_orders": "Buyurtmalar yo'q", "no_payments": "To'lovlar yo'q",
        "no_orders_yet": "Hozircha birorta buyurtmangiz yo'q.",
        "no_finance": "Hozircha moliya tarixi bo'sh.",
        "no_filter_rows": "Bu filtr bo'yicha yozuv yo'q.",
        "no_games": "O'yinlar yo'q", "no_promo": "Promokod yo'q",
        "no_rating": "Hali reyting yo'q",
        "no_waiting_pay": "Kutilayotgan to'lov yo'q.",
        "no_audit": "Audit yozuvlari yo'q",
        "catalog_empty": "Katalog hozircha bo'sh.",
        "no_admin_rights": "Admin huquqi yo'q",
        "err_load": "Yuklab bo'lmadi.", "try_again": "Qayta urinish",
        "code_example": "KOD (masalan: YANGI25)",
        "can_continue": "Davom etish mumkin.",
        "wrong_verify": "❌ Tekshirilmadi. ID'ni qayta kiriting.",
        "id_found_ok": "✅ {0} topildi. To'g'ri o'yinchi!",
        "pay_timer_expired": "⏰ Vaqt tugadi — chekni hali ham yuborishingiz mumkin",
        "new_msgs_here": "Yangi xabarlar shu yerda paydo bo'ladi.",
        "open_in_tg": "Mini App'ni to'g'ridan-to'g'ri Telegram'da oching.",
        "only_admins": "Bu bo'lim faqat adminlar uchun.",
        "try_other_req": "Boshqa so'rov bilan urinib ko'ring.",
        "admin_actions_here": "Admin amallari shu yerda ko'rinadi.",
        "create_promo_first": "Yuqoridan yangi promokod yarating.",
        "cart_empty": "Savat bo'sh",
        # --- statuslar ---
        "st_pending": "Kutilmoqda", "st_ok": "Muvaffaqiyatli",
        "st_rejected": "Rad etilgan", "st_cancelled": "Bekor qilingan",
        "st_refunded": "Qaytarildi", "st_waitpay": "To'lov kutilmoqda",
        "st_paid": "To'landi",
        # --- tasdiq dialoglari ---
        "cf_order_reject": "Buyurtma #{0} rad etilsinmi?",
        "cf_pay_reject": "To'lov #{0} rad etilsinmi?",
        "cf_promo_del": "Promokod {0} o'chirilsinmi?",
        "cf_ban": "Foydalanuvchini ban qilsinmi?",
        "cf_unban": "Ban olib tashlansinmi?",
        "cf_refund": "Mijozga {0} so'm qaytariladi.",
        "refund_note": "Mijozga rad etilgani haqida xabar boradi.",
        # --- admin tugmalar ---
        "adm_bal_plus": "➕ Balans qo'shish",
        "adm_bal_minus": "➖ Balans kamaytirish",
        "adm_ban": "⛔️ Ban", "adm_unban": " Ban olib tashlash",
        "adm_reject": "❌ Rad", "adm_receipt": "🧾 Chek",
        "kod_enter": "KOD kiriting", "phone_enter": "Raqam kiriting",
        "support": "Qo'llab-quvvatlash",
        "invite_link_bot": 'Taklif havolasi (bot)',
        "lb_row": 'Reyting jadvali',
        "sum_suffix": "so'm",
        "baholang": 'Baholang:',
        "link_prefix": 'Havola: ',
        "not_found": 'Topilmadi',
        "back": 'Qaytish',
        "cart_empty_text": "O'yin tanlang va mahsulotni savatga qo'shing.",
        "be_first": "Birinchi bo'ling — do'stlarni taklif qiling!",
        "open_in_tg_title": 'Telegram orqali oching',
        "banned_text": 'Siz bloklangansiz.',
        "batch_result": '✅ {0} bajarildi, ❌ {1} xatolik',
        "batch_ok": '✅ {0} buyurtma qabul qilindi!',
        "total_label": 'JAMI',
        "date_label": 'Sana',
        "game_label": "O'yin",
        "pkg_label": 'Paket',
        "player_lbl": "O'yinchi ID",
        "player_name": "O'yinchi",
        "holat": 'Holat',
        "receipt_foot": "Bu chek faqat ma'lumot uchun.",
        "print_receipt": '🖨 PDF saqlash / chop etish',
        "step_created": 'Yaratildi',
        "step_paid": "To'lov",
        "step_delivered": 'Yetkazildi',
        "light_mode": '☀️ Light rejim',
        "dark_mode": '🌙 Dark rejim',
        "sum_prompt": "Summani so'mda kiriting:",
        "pay_with_balance_btn": "💠 Balans bilan to'lash ({0} so'm)",
        "stars_rate": "1 ⭐️ = 270 so'm",
        "saved_ids_title": 'SAQLANGAN IDLAR',
        "in_cart": '🛒 savatda',
        "close_btn": 'Yopish',
        "card_word": 'Karta',
        "contact_ask": 'Murojaat',
        "number_word": 'Raqam',
        "phone_word": 'Telefon',
        "email_word": 'Email',
        "owner_word": 'Egasi',
        "pay_no": "To'lov raqami",
        "order_no": 'Buyurtma',
        "pay_hint": "Ushbu sahifa <b>yopilguncha</b> pulni o'tkazing. So'ng chekni botga yuboring yoki quyida yuklang.",
        "view_receipt": "Chek ko'rish / PDF",
        "send_receipt_bot": 'Chekni yuborish (bot)',
        "ask_admin": 'Adminga murojaat qilish',
        "exit": 'Chiqish',
        "pay_transfer": "<b>{0}</b> o'tkazishingiz kerak.",
        "pay_after_tx": "Trаnsaksiya qilganingizdan so'ng admin tasdiqlaydi va buyurtmangiz bajariladi.",
        "stars_req": 'To\'lov so\'rovi chatga yuborildi.<br>Chatga o\'tib "To\'lash" tugmasini bosing.<br><br><b>Summa: {0}</b>',
        "no_data": "Ma'lumot yo'q",
        "week_revenue": '📈 7 kunlik tushum',
        "week_topups": "💳 7 kunlik to'ldirishlar",
        "stat_total_users": 'Jami foydalanuvchilar',
        "stat_mau": 'Oylik faol (MAU)',
        "stat_new_users": 'Yangi (bu oy)',
        "stat_done": 'Bajarilgan',
        "stat_revenue": 'Jami tushum',
        "stat_month_rev": 'Oylik tushum',
        "stat_topupped": "To'ldirilgan",
        "stat_month_topups": "Oylik to'ldirishlar",
        "stat_pending": 'Kutilayotgan',
        "stat_waitpay": "To'lov kutish",
        "today_title": '📈 Bugun',
        "today_done_orders": 'Bajarilgan buyurtmalar:',
        "autodel_title": '🚚 Avto-delivery',
        "interval": 'Interval',
        "settings_title": '⚙️ Sozlamalar',
        "active_card": 'Faol karta',
        "cashback": 'Keshbek',
        "referral_word": 'Referral',
        "min_max_topup": 'Min/Max topup',
        "fl_pending": '⏳ Kutilayotgan',
        "fl_done": '✅ Bajarilgan',
        "fl_rejected": '❌ Rad etilgan',
        "fl_all": '📋 Hammasi',
        "btn_done": '✅ Bajarildi',
        "btn_refund": '↩️ Qaytarish',
        "client_word": 'Mijoz',
        "confirm_pay": '✅ Tasdiqlash',
        "search_ph": 'ID / username / ism qidiruv',
        "search_btn": 'Qidirish',
        "total_topped_up": "Jami to'ldirgan",
        "btn_add_bal": '➕ Balans',
        "btn_deduct": '➖ Kamaytirish',
        "btn_unban": '✅ Unban',
        "new_promo_title": '🎁 Yangi promokod',
        "create_btn": 'Yaratish',
        "delete_btn": "O'chirish",
        "uses_label": 'Ishlatilgan',
        "refund_word": 'Qaytarish',
        "st_done": 'Bajarildi',
        "st_reject_short": '❌ Bekor',
        "method_card": 'Karta',
        "method_refund": 'Qaytarish',
        "clear_cart2": 'Savatni tozalash',
        "st_confirmed": 'Tasdiqlandi',
        "stars_req2": 'To\'lov so\'rovi chatga yuborildi.<br>Telegram chatga o\'tib "To\'lash" tugmasini bosing.<br><br><b>To\'lab bo\'lgach buyurtma avtomatik bajariladi.</b>',
        "provider": 'Provider',
        "tab_games": "O'yinlar",
        "tab_broadcast": 'Xabar yuborish',
        "tab_settings": 'Sozlamalar',
        "add_game_btn": "Yangi o'yin",
        "edit_word": 'Tahrirlash',
        "game_id_ph": "O'yin ID (freefire)",
        "game_name_ph": "O'yin nomi",
        "game_emoji_ph": 'Emoji (🔥)',
        "game_desc_ph": 'Tavsif',
        "pkg_title": 'Paketlar',
        "pkg_add_btn": "Paket qo'shish",
        "pkg_id_ph": 'Paket ID (ff-100)',
        "pkg_name_ph": 'Nomi (100 Diamonds)',
        "pkg_amt_ph": 'Miqdor',
        "pkg_price_ph": "Narx (so'm)",
        "pkg_cat_ph": 'Kategoriya',
        "game_saved": "O'yin saqlandi",
        "game_deleted": "O'yin o'chirildi",
        "cf_game_del": "O'yinni o'chirish: {0}?",
        "enter_game_name": "O'yin nomini kiriting",
        "set_star_rate": '1000 Stars narxi',
        "set_min_topup": "Min to'ldirish",
        "set_max_topup": "Max to'ldirish",
        "set_pay_window": "To'lov oynasi (sek)",
        "set_card_active": 'Faol karta',
        "set_support_user": 'Support username',
        "set_sup_phone": 'Support telefon',
        "set_sup_email": 'Support email',
        "set_admin_contact": 'Murojaat uchun',
        "set_referral": 'Referal %',
        "settings_saved": 'Sozlamalar saqlandi',
        "maintenance_lbl": 'Texnik ishlar rejimi',
        "maintenance_hint": "Yoqilganda foydalanuvchilar to'lay olmaydi (adminlar mumkin)",
        "f_auto_delivery": "Avtomatik yetkazish",
        "f_ocr": "Chekni rasm orqali tekshirish (OCR)",
        "f_nickname": "ID kiritilganda o'yinchi nomini ko'rsatish",
        "f_id_validation": "ID formatini tekshirish (xato ID bloklanadi)",
        "f_chek_reminder": "Chek yubormasa eslatish",
        "toggle_on": 'Yoqilgan',
        "toggle_off": "O'chiq",
        "admins_title": 'Adminlar',
        "admin_id_ph": 'User ID (123456789)',
        "admin_add_btn": "Qo'shish",
        "admin_added": "Admin qo'shildi",
        "admin_removed": "Admin o'chirildi",
        "cf_admin_del": "Admindan o'chirish: {0}?",
        "admin_self_err": "O'zingizni o'chira olmaysiz",
        "admin_exists": 'Bu user allaqachon admin',
        "admin_no_user": 'Bunday user topilmadi',
        "added_by_lbl": "Qo'shgan",
        "you_label": 'Siz',
        "bc_title": 'Xabar yuborish',
        "bc_text_ph": 'Xabar matni...',
        "bc_scope_all": 'Barchaga',
        "bc_scope_user": 'Bitta userga',
        "bc_user_ph": 'User ID',
        "bc_send": 'Yuborish',
        "bc_sent_all": 'Barchaga yuborildi: {0} ta',
        "bc_sent_user": 'Userga yuborildi',
        "bc_empty": 'Xabar matnini kiriting',
        "bc_need_user": 'User ID kiriting',
        "bc_tg_note": 'Bitta user: notification + Telegram xabar',
        "export_csv": '⬇️ CSV',
        "export_failed": 'Export xatosi',
        "ref_top_title": 'Eng faol refererlar',
        "ref_invites": 'Takliflar',
        "ref_earned": 'Daromad',
        "maintenance_msg": "Texnik ishlar tufayli to'lovlar vaqtincha mavjud emas",
        "maintenance_banner": '🔧 Texnik ishlar davom etmoqda...',
        "games_edit_title": "O'yinni tahrirlash",
    },
    "ru": {
        "home": "Главная", "history": "История", "settings": "Настройки",
        "balance": "Баланс", "topup": "Пополнить счёт",
        "pay_method": "Выберите способ оплаты", "buy": "Купить",
        "verify": "Проверить", "verifying": "Проверка...",
        "enter_id": "Введите ID игры", "products": "ВЫБЕРИТЕ ТОВАР",
        "cat_all": "Все", "promo": "Промокоды",
        "promo_placeholder": "Промокод", "apply": "Применить",
        "invite": "Пригласить друзей", "invite_link": "Ссылка приглашения",
        "copy": "Копировать", "copied": "Скопировано ✅",
        "orders": "Заказы", "finance": "Финансы",
        "save": "Сохранить", "phone": "Телефон", "lang": "Язык",
        "keshbek": "КЕШБЕК", "invited": "Приглашено", "reward": "Бонус",
        "pay_amount": "Оплата", "pay": "Оплатить", "close": "Понятно",
        "notifications": "Уведомления", "cart": "Корзина", "theme": "Тема",
        "favorites": "Избранное", "leaderboard": "Рейтинг", "empty": "Пусто",
        "receipt": "Чек", "reorder": "Повторить заказ", "rate": "Оценить",
        "bal_label": "Ваш баланс", "topup_go": "Пополнить",
        "referral_short": "Приглашение", "promo_short": "Промо",
        "games": "ИГРЫ",
        "fav_empty_t": "Нет избранного",
        "fav_empty_d": "Нажмите ⭐️ на карточке игры — она появится здесь.",
        "view_games": "Смотреть игры",
        "prod_empty_t": "Товаров нет",
        "prod_empty_d": "В этой категории пока нет товаров.",
        "add_cart": "В корзину", "amount": "Сумма",
        "amount_ph": "Введите сумму (сум)",
        "guide": "Инструкция",
        "guide_body": "1. Выберите способ<br>2. Введите сумму<br>3. Оплатите — баланс пополнится автоматически или после подтверждения админа",
        "refresh": "Обновить", "services": "СЕРВИСЫ",
        "rating_count": "оценок: {0}",
        "rating_hint": "Оцените заказ ⭐️ после выполнения — это поможет улучшить сервис.",
        "nav_admin": "Админ",
        "pay_with_bal": "С баланса", "pay_uzqr": "UzQR Экспресс", "pay_by_card": "Картой",
        "ref_inst1": "Вы получите",
        "ref_inst2": "кешбэка, когда приглашённый пополнит счёт.",
        "ref_bonus": "Полученный бонус",
        "share": "Поделиться", "view_lb": "Смотреть рейтинг",
        "promo_inst1": "Введите промокод — бонус добавится на баланс.",
        "promo_inst2": "Коды: /promo КОД (в боте) или введите здесь.",
        "mark_read": "Прочитать все", "clear_cart": "Очистить",
        "lb_title": "Реферальный рейтинг", "print": "PDF / Печать",
        "cancel": "Отмена", "confirm": "Подтвердить",
        "admin_panel": "Админ-панель", "tab_dash": "Панель",
        "tab_payments": "Платежи", "tab_users": "Пользователи",
        "tab_promos": "Промокоды", "tab_audit": "Аудит",
        "pay_window": "Окно оплаты", "favorite": "Избранное",
        "user_label": "Пользователь", "banned_label": "Заблокирован",
        "err_network": "Не удалось связаться с сервером",
        "game_not_found": "Игра не найдена",
        "id_ok": "ID принят ✅", "id_enter": "Введите ID",
        "select_product": "Выберите товар",
        "err_generic": "Произошла ошибка",
        "no_balance": "Недостаточно баланса. Пополните счёт!",
        "send_receipt": "Отправьте чек/скриншот в бот",
        "admin_not_found": "Админ не найден — обратитесь через бота",
        "wait_admin": "Ожидайте подтверждения админа ✅",
        "cart_cleared": "Корзина очищена",
        "enter_id_first": "Сначала введите ID игры",
        "enter_amount": "Введите сумму",
        "min_sum": "Минимальная сумма: {0} сум",
        "min_amt": "Минимум: {0}", "max_amt": "Максимум: {0}",
        "refreshed": "⟳ Обновлено",
        "reorder_bad": "Этот заказ нельзя повторить",
        "reorder_ok": "✅ Повторный заказ принят!",
        "enter_number": "Введите номер", "saved_ok": "Сохранено ✅",
        "support_not_found": "Поддержка не найдена",
        "loading": "Загрузка...", "enter_promo": "Введите промокод",
        "all_read_ok": "Отмечено прочитанным ✅",
        "wrong_amount": "Неверная сумма", "enter_code": "Введите КОД",
        "fav_added": "⭐️ Добавлено в избранное",
        "fav_removed": "☆ Удалено",
        "cart_removed": "🛒 Удалено из корзины",
        "cart_added": "🛒 Добавлено в корзину",
        "promo_bad": "Промокод не работает",
        "no_notifications": "Нет уведомлений",
        "no_orders": "Нет заказов", "no_payments": "Нет платежей",
        "no_orders_yet": "У вас пока нет заказов.",
        "no_finance": "Финансовая история пуста.",
        "no_filter_rows": "Нет записей по этому фильтру.",
        "no_games": "Нет игр", "no_promo": "Нет промокодов",
        "no_rating": "Рейтинга пока нет",
        "no_waiting_pay": "Нет ожидающих платежей.",
        "no_audit": "Нет записей аудита",
        "catalog_empty": "Каталог пока пуст.",
        "no_admin_rights": "Нет прав админа",
        "err_load": "Не удалось загрузить.", "try_again": "Повторить",
        "code_example": "КОД (например: NEW25)",
        "can_continue": "Можно продолжить.",
        "wrong_verify": "❌ Не проверено. Введите ID заново.",
        "id_found_ok": "✅ {0} найден. Верный игрок!",
        "pay_timer_expired": "⏰ Время вышло — чек всё ещё можно отправить",
        "new_msgs_here": "Новые сообщения появятся здесь.",
        "open_in_tg": "Откройте Mini App прямо в Telegram.",
        "only_admins": "Этот раздел только для админов.",
        "try_other_req": "Попробуйте другой запрос.",
        "admin_actions_here": "Действия админа появятся здесь.",
        "create_promo_first": "Создайте новый промокод выше.",
        "cart_empty": "Корзина пуста",
        "st_pending": "Ожидает", "st_ok": "Успешно",
        "st_rejected": "Отклонён", "st_cancelled": "Отменён",
        "st_refunded": "Возврат", "st_waitpay": "Ожидает оплаты",
        "st_paid": "Оплачено",
        "cf_order_reject": "Отклонить заказ #{0}?",
        "cf_pay_reject": "Отклонить платёж #{0}?",
        "cf_promo_del": "Удалить промокод {0}?",
        "cf_ban": "Забанить пользователя?",
        "cf_unban": "Снять бан?",
        "cf_refund": "Клиенту будет возвращено {0} сум.",
        "refund_note": "Клиент получит уведомление об отклонении.",
        "adm_bal_plus": "➕ Пополнить баланс",
        "adm_bal_minus": "➖ Списать баланс",
        "adm_ban": "⛔️ Бан", "adm_unban": " Снять бан",
        "adm_reject": "❌ Отклонить", "adm_receipt": "🧾 Чек",
        "kod_enter": "Введите КОД", "phone_enter": "Введите номер",
        "support": 'Поддержка',
        "invite_link_bot": 'Ссылка приглашения (бот)',
        "lb_row": 'Таблица рейтинга',
        "sum_suffix": 'сум',
        "baholang": 'Оцените:',
        "link_prefix": 'Ссылка: ',
        "not_found": 'Не найдено',
        "back": 'Назад',
        "cart_empty_text": 'Выберите игру и добавьте товар в корзину.',
        "be_first": 'Будьте первыми — приглашайте друзей!',
        "open_in_tg_title": 'Откройте в Telegram',
        "banned_text": 'Вы заблокированы.',
        "batch_result": '✅ {0} выполнено, ❌ {1} ошибок',
        "batch_ok": '✅ {0} заказов принято!',
        "total_label": 'ИТОГО',
        "date_label": 'Дата',
        "game_label": 'Игра',
        "pkg_label": 'Пакет',
        "player_lbl": 'ID игрока',
        "player_name": 'Игрок',
        "holat": 'Статус',
        "receipt_foot": 'Этот чек только для информации.',
        "print_receipt": '🖨 Сохранить PDF / печать',
        "step_created": 'Создан',
        "step_paid": 'Оплата',
        "step_delivered": 'Доставлен',
        "light_mode": '☀️ Светлая тема',
        "dark_mode": '🌙 Тёмная тема',
        "sum_prompt": 'Введите сумму в сум:',
        "pay_with_balance_btn": '💠 Оплатить с баланса ({0} сум)',
        "stars_rate": '1 ⭐️ = 270 сум',
        "saved_ids_title": 'СОХРАНЁННЫЕ ID',
        "in_cart": '🛒 в корзине',
        "close_btn": 'Закрыть',
        "card_word": 'Карта',
        "contact_ask": 'Обращение',
        "number_word": 'Номер',
        "phone_word": 'Телефон',
        "email_word": 'Email',
        "owner_word": 'Владелец',
        "pay_no": 'Номер платежа',
        "order_no": 'Заказ',
        "pay_hint": 'Переведите деньги, пока страница <b>не закрыта</b>. Затем отправьте чек в бот или загрузите здесь.',
        "view_receipt": 'Чек / PDF',
        "send_receipt_bot": 'Отправить чек (бот)',
        "ask_admin": 'Связаться с админом',
        "exit": 'Выйти',
        "pay_transfer": 'Вам нужно перевести <b>{0}</b>.',
        "pay_after_tx": 'После транзакции админ подтвердит и заказ будет выполнен.',
        "stars_req": 'Запрос на оплату отправлен в чат.<br>Перейдите в чат и нажмите "Оплатить".<br><br><b>Сумма: {0}</b>',
        "no_data": 'Нет данных',
        "week_revenue": '📈 Выручка за 7 дней',
        "week_topups": '💳 Пополнений за 7 дней',
        "stat_total_users": 'Всего пользователей',
        "stat_mau": 'Активные за месяц (MAU)',
        "stat_new_users": 'Новые (этот месяц)',
        "stat_done": 'Выполнено',
        "stat_revenue": 'Общая выручка',
        "stat_month_rev": 'Выручка за месяц',
        "stat_topupped": 'Пополнено',
        "stat_month_topups": 'Пополнений за месяц',
        "stat_pending": 'Ожидают',
        "stat_waitpay": 'Ожидают оплаты',
        "today_title": '📈 Сегодня',
        "today_done_orders": 'Выполненные заказы:',
        "autodel_title": '🚚 Авто-доставка',
        "interval": 'Интервал',
        "settings_title": '⚙️ Настройки',
        "active_card": 'Активная карта',
        "cashback": 'Кешбэк',
        "referral_word": 'Реферал',
        "min_max_topup": 'Мин/Макс пополнение',
        "fl_pending": '⏳ Ожидают',
        "fl_done": '✅ Выполненные',
        "fl_rejected": '❌ Отклонённые',
        "fl_all": '📋 Все',
        "btn_done": '✅ Выполнено',
        "btn_refund": '↩️ Возврат',
        "client_word": 'Клиент',
        "confirm_pay": '✅ Подтвердить',
        "search_ph": 'ID / username / имя',
        "search_btn": 'Поиск',
        "total_topped_up": 'Всего пополнил',
        "btn_add_bal": '➕ Баланс',
        "btn_deduct": '➖ Списать',
        "btn_unban": '✅ Разбан',
        "new_promo_title": '🎁 Новый промокод',
        "create_btn": 'Создать',
        "delete_btn": 'Удалить',
        "uses_label": 'Использовано',
        "refund_word": 'Возврат',
        "st_done": 'Выполнен',
        "st_reject_short": '❌ Отклонён',
        "method_card": 'Карта',
        "method_refund": 'Возврат',
        "clear_cart2": 'Очистить корзину',
        "st_confirmed": 'Подтверждён',
        "stars_req2": 'Запрос на оплату отправлен в чат.<br>Перейдите в Telegram-чат и нажмите "Оплатить".<br><br><b>После оплаты заказ выполнится автоматически.</b>',
        "provider": 'Провайдер',
        "tab_games": 'Игры',
        "tab_broadcast": 'Рассылка',
        "tab_settings": 'Настройки',
        "add_game_btn": 'Новая игра',
        "edit_word": 'Редактировать',
        "game_id_ph": 'ID игры (freefire)',
        "game_name_ph": 'Название игры',
        "game_emoji_ph": 'Эмодзи (🔥)',
        "game_desc_ph": 'Описание',
        "pkg_title": 'Пакеты',
        "pkg_add_btn": 'Добавить пакет',
        "pkg_id_ph": 'ID пакета (ff-100)',
        "pkg_name_ph": 'Название (100 Diamonds)',
        "pkg_amt_ph": 'Количество',
        "pkg_price_ph": 'Цена (сум)',
        "pkg_cat_ph": 'Категория',
        "game_saved": 'Игра сохранена',
        "game_deleted": 'Игра удалена',
        "cf_game_del": 'Удалить игру: {0}?',
        "enter_game_name": 'Введите название игры',
        "set_star_rate": 'Цена 1000 Stars',
        "set_min_topup": 'Мин. пополнение',
        "set_max_topup": 'Макс. пополнение',
        "set_pay_window": 'Окно оплаты (сек)',
        "set_card_active": 'Активная карта',
        "set_support_user": 'Username поддержки',
        "set_sup_phone": 'Телефон поддержки',
        "set_sup_email": 'Email поддержки',
        "set_admin_contact": 'Для связи',
        "set_referral": 'Реферал %',
        "settings_saved": 'Настройки сохранены',
        "maintenance_lbl": 'Режим техработ',
        "maintenance_hint": 'Включено: пользователи не могут платить (админы могут)',
        "f_auto_delivery": 'Автоматическая доставка',
        "f_ocr": 'Проверка чека по фото (OCR)',
        "f_nickname": 'Показывать ник игрока по ID',
        "f_id_validation": 'Проверка формата ID',
        "f_chek_reminder": 'Напоминать, если чек не отправлен',
        "toggle_on": 'Вкл',
        "toggle_off": 'Выкл',
        "admins_title": 'Админы',
        "admin_id_ph": 'User ID (123456789)',
        "admin_add_btn": 'Добавить',
        "admin_added": 'Админ добавлен',
        "admin_removed": 'Админ удалён',
        "cf_admin_del": 'Убрать из админов: {0}?',
        "admin_self_err": 'Нельзя убрать себя',
        "admin_exists": 'Этот user уже админ',
        "admin_no_user": 'Пользователь не найден',
        "added_by_lbl": 'Добавил',
        "you_label": 'Вы',
        "bc_title": 'Отправка сообщения',
        "bc_text_ph": 'Текст сообщения...',
        "bc_scope_all": 'Всем',
        "bc_scope_user": "Одному user'у",
        "bc_user_ph": 'User ID',
        "bc_send": 'Отправить',
        "bc_sent_all": 'Отправлено всем: {0}',
        "bc_sent_user": 'Отправлено пользователю',
        "bc_empty": 'Введите текст сообщения',
        "bc_need_user": 'Введите User ID',
        "bc_tg_note": "Одному user'у: notification + Telegram",
        "export_csv": '⬇️ CSV',
        "export_failed": 'Ошибка экспорта',
        "ref_top_title": 'Активные рефереры',
        "ref_invites": 'Приглашения',
        "ref_earned": 'Заработано',
        "maintenance_msg": 'Платежи временно недоступны из-за техработ',
        "maintenance_banner": '🔧 Идут техработы...',
        "games_edit_title": 'Редактирование игры',
    },
    "en": {
        "home": "Home", "history": "History", "settings": "Settings",
        "balance": "Balance", "topup": "Top up",
        "pay_method": "Choose payment method", "buy": "Buy",
        "verify": "Verify", "verifying": "Verifying...",
        "enter_id": "Enter game ID", "products": "CHOOSE A PRODUCT",
        "cat_all": "All", "promo": "Promo codes",
        "promo_placeholder": "Promo code", "apply": "Apply",
        "invite": "Invite friends", "invite_link": "Invite link",
        "copy": "Copy", "copied": "Copied ✅",
        "orders": "Orders", "finance": "Finance",
        "save": "Save", "phone": "Phone number", "lang": "Language",
        "keshbek": "CASHBACK", "invited": "Invited", "reward": "Reward",
        "pay_amount": "Payment", "pay": "Pay", "close": "Got it",
        "notifications": "Notifications", "cart": "Cart", "theme": "Theme",
        "favorites": "Favorites", "leaderboard": "Leaderboard", "empty": "Empty",
        "receipt": "Receipt", "reorder": "Reorder", "rate": "Rate",
        "bal_label": "Your balance", "topup_go": "Top up",
        "referral_short": "Invite", "promo_short": "Promo",
        "games": "GAMES",
        "fav_empty_t": "No favorites",
        "fav_empty_d": "Tap ⭐️ on a game card — it will appear here.",
        "view_games": "Browse games",
        "prod_empty_t": "No products",
        "prod_empty_d": "No products in this category yet.",
        "add_cart": "Add to cart", "amount": "Amount",
        "amount_ph": "Enter amount (UZS)",
        "guide": "Guide",
        "guide_body": "1. Choose a method<br>2. Enter the amount<br>3. Pay — balance updates automatically or after admin approval",
        "refresh": "Refresh", "services": "SERVICES",
        "rating_count": "{0} ratings",
        "rating_hint": "Rate your order ⭐️ after completion — it helps improve the service.",
        "nav_admin": "Admin",
        "pay_with_bal": "From balance", "pay_uzqr": "UzQR Express", "pay_by_card": "By card",
        "ref_inst1": "You get",
        "ref_inst2": "cashback when an invited user tops up.",
        "ref_bonus": "Bonus received",
        "share": "Share", "view_lb": "View leaderboard",
        "promo_inst1": "Enter a promo code — bonus will be added to your balance.",
        "promo_inst2": "Codes: /promo CODE (in bot) or type here.",
        "mark_read": "Mark all read", "clear_cart": "Clear",
        "lb_title": "Referral leaderboard", "print": "PDF / Print",
        "cancel": "Cancel", "confirm": "Confirm",
        "admin_panel": "Admin panel", "tab_dash": "Dashboard",
        "tab_payments": "Payments", "tab_users": "Users",
        "tab_promos": "Promo codes", "tab_audit": "Audit",
        "pay_window": "Payment window", "favorite": "Favorite",
        "user_label": "User", "banned_label": "Blocked",
        "err_network": "Could not connect to server",
        "game_not_found": "Game not found",
        "id_ok": "ID accepted ✅", "id_enter": "Enter ID",
        "select_product": "Select a product",
        "err_generic": "Something went wrong",
        "no_balance": "Insufficient balance. Top up your account!",
        "send_receipt": "Send receipt/screenshot to the bot",
        "admin_not_found": "Admin not found — contact via bot",
        "wait_admin": "Wait for admin approval ✅",
        "cart_cleared": "Cart cleared",
        "enter_id_first": "Enter game ID first",
        "enter_amount": "Enter amount",
        "min_sum": "Minimum amount: {0} UZS",
        "min_amt": "Min: {0}", "max_amt": "Max: {0}",
        "refreshed": "⟳ Updated",
        "reorder_bad": "This order cannot be reordered",
        "reorder_ok": "✅ Reorder accepted!",
        "enter_number": "Enter number", "saved_ok": "Saved ✅",
        "support_not_found": "Support not found",
        "loading": "Loading...", "enter_promo": "Enter promo code",
        "all_read_ok": "Marked as read ✅",
        "wrong_amount": "Invalid amount", "enter_code": "Enter CODE",
        "fav_added": "⭐️ Added to favorites",
        "fav_removed": "☆ Removed",
        "cart_removed": "🛒 Removed from cart",
        "cart_added": "🛒 Added to cart",
        "promo_bad": "Promo code doesn't work",
        "no_notifications": "No notifications",
        "no_orders": "No orders", "no_payments": "No payments",
        "no_orders_yet": "You have no orders yet.",
        "no_finance": "No finance history yet.",
        "no_filter_rows": "No records for this filter.",
        "no_games": "No games", "no_promo": "No promo codes",
        "no_rating": "No ratings yet",
        "no_waiting_pay": "No pending payments.",
        "no_audit": "No audit records",
        "catalog_empty": "Catalog is empty.",
        "no_admin_rights": "No admin rights",
        "err_load": "Failed to load.", "try_again": "Try again",
        "code_example": "CODE (e.g. NEW25)",
        "can_continue": "You can continue.",
        "wrong_verify": "❌ Verification failed. Re-enter the ID.",
        "id_found_ok": "✅ {0} found. Correct player!",
        "pay_timer_expired": "⏰ Time is up — you can still send the receipt",
        "new_msgs_here": "New messages will appear here.",
        "open_in_tg": "Open the Mini App directly in Telegram.",
        "only_admins": "This section is for admins only.",
        "try_other_req": "Try another request.",
        "admin_actions_here": "Admin actions will appear here.",
        "create_promo_first": "Create a new promo code above.",
        "cart_empty": "Cart is empty",
        "st_pending": "Pending", "st_ok": "Successful",
        "st_rejected": "Rejected", "st_cancelled": "Cancelled",
        "st_refunded": "Refunded", "st_waitpay": "Awaiting payment",
        "st_paid": "Paid",
        "cf_order_reject": "Reject order #{0}?",
        "cf_pay_reject": "Reject payment #{0}?",
        "cf_promo_del": "Delete promo code {0}?",
        "cf_ban": "Ban this user?",
        "cf_unban": "Unban this user?",
        "cf_refund": "Client will be refunded {0} UZS.",
        "refund_note": "Client will be notified about the rejection.",
        "adm_bal_plus": "➕ Add balance",
        "adm_bal_minus": "➖ Deduct balance",
        "adm_ban": "⛔️ Ban", "adm_unban": " Unban",
        "adm_reject": "❌ Reject", "adm_receipt": "🧾 Receipt",
        "kod_enter": "Enter CODE", "phone_enter": "Enter number",
        "support": 'Support',
        "invite_link_bot": 'Invite link (bot)',
        "lb_row": 'Leaderboard',
        "sum_suffix": 'UZS',
        "baholang": 'Rate:',
        "link_prefix": 'Link: ',
        "not_found": 'Not found',
        "back": 'Back',
        "cart_empty_text": 'Pick a game and add a product to the cart.',
        "be_first": 'Be the first — invite your friends!',
        "open_in_tg_title": 'Open in Telegram',
        "banned_text": 'You are blocked.',
        "batch_result": '✅ {0} done, ❌ {1} failed',
        "batch_ok": '✅ {0} orders accepted!',
        "total_label": 'TOTAL',
        "date_label": 'Date',
        "game_label": 'Game',
        "pkg_label": 'Package',
        "player_lbl": 'Player ID',
        "player_name": 'Player',
        "holat": 'Status',
        "receipt_foot": 'This receipt is for information only.',
        "print_receipt": '🖨 Save PDF / print',
        "step_created": 'Created',
        "step_paid": 'Payment',
        "step_delivered": 'Delivered',
        "light_mode": '☀️ Light mode',
        "dark_mode": '🌙 Dark mode',
        "sum_prompt": 'Enter the amount in UZS:',
        "pay_with_balance_btn": '💠 Pay from balance ({0} UZS)',
        "stars_rate": '1 ⭐️ = 270 UZS',
        "saved_ids_title": 'SAVED IDS',
        "in_cart": '🛒 in cart',
        "close_btn": 'Close',
        "card_word": 'Card',
        "contact_ask": 'Contact',
        "number_word": 'Number',
        "phone_word": 'Phone',
        "email_word": 'Email',
        "owner_word": 'Owner',
        "pay_no": 'Payment #',
        "order_no": 'Order',
        "pay_hint": 'Transfer the money while this page is <b>open</b>. Then send the receipt to the bot or upload it here.',
        "view_receipt": 'Receipt / PDF',
        "send_receipt_bot": 'Send receipt (bot)',
        "ask_admin": 'Contact admin',
        "exit": 'Exit',
        "pay_transfer": 'You need to transfer <b>{0}</b>.',
        "pay_after_tx": 'After the transaction, the admin will confirm and the order will be fulfilled.',
        "stars_req": 'Payment request sent to the chat.<br>Go to the chat and tap "Pay".<br><br><b>Amount: {0}</b>',
        "no_data": 'No data',
        "week_revenue": '📈 7-day revenue',
        "week_topups": '💳 7-day top-ups',
        "stat_total_users": 'Total users',
        "stat_mau": 'Monthly active (MAU)',
        "stat_new_users": 'New (this month)',
        "stat_done": 'Completed',
        "stat_revenue": 'Total revenue',
        "stat_month_rev": 'Monthly revenue',
        "stat_topupped": 'Topped up',
        "stat_month_topups": 'Monthly top-ups',
        "stat_pending": 'Pending',
        "stat_waitpay": 'Awaiting payment',
        "today_title": '📈 Today',
        "today_done_orders": 'Completed orders:',
        "autodel_title": '🚚 Auto-delivery',
        "interval": 'Interval',
        "settings_title": '⚙️ Settings',
        "active_card": 'Active card',
        "cashback": 'Cashback',
        "referral_word": 'Referral',
        "min_max_topup": 'Min/Max top-up',
        "fl_pending": '⏳ Pending',
        "fl_done": '✅ Completed',
        "fl_rejected": '❌ Rejected',
        "fl_all": '📋 All',
        "btn_done": '✅ Complete',
        "btn_refund": '↩️ Refund',
        "client_word": 'Client',
        "confirm_pay": '✅ Confirm',
        "search_ph": 'ID / username / name',
        "search_btn": 'Search',
        "total_topped_up": 'Total topped up',
        "btn_add_bal": '➕ Balance',
        "btn_deduct": '➖ Deduct',
        "btn_unban": '✅ Unban',
        "new_promo_title": '🎁 New promo code',
        "create_btn": 'Create',
        "delete_btn": 'Delete',
        "uses_label": 'Used',
        "refund_word": 'Refund',
        "st_done": 'Completed',
        "st_reject_short": '❌ Rejected',
        "method_card": 'Card',
        "method_refund": 'Refund',
        "clear_cart2": 'Clear cart',
        "st_confirmed": 'Confirmed',
        "stars_req2": 'Payment request sent to the chat.<br>Open the Telegram chat and tap "Pay".<br><br><b>After payment the order is fulfilled automatically.</b>',
        "provider": 'Provider',
        "tab_games": 'Games',
        "tab_broadcast": 'Broadcast',
        "tab_settings": 'Settings',
        "add_game_btn": 'New game',
        "edit_word": 'Edit',
        "game_id_ph": 'Game ID (freefire)',
        "game_name_ph": 'Game name',
        "game_emoji_ph": 'Emoji (🔥)',
        "game_desc_ph": 'Description',
        "pkg_title": 'Packages',
        "pkg_add_btn": 'Add package',
        "pkg_id_ph": 'Package ID (ff-100)',
        "pkg_name_ph": 'Name (100 Diamonds)',
        "pkg_amt_ph": 'Amount',
        "pkg_price_ph": 'Price (UZS)',
        "pkg_cat_ph": 'Category',
        "game_saved": 'Game saved',
        "game_deleted": 'Game deleted',
        "cf_game_del": 'Delete game: {0}?',
        "enter_game_name": 'Enter game name',
        "set_star_rate": '1000 Stars rate',
        "set_min_topup": 'Min top-up',
        "set_max_topup": 'Max top-up',
        "set_pay_window": 'Pay window (sec)',
        "set_card_active": 'Active card',
        "set_support_user": 'Support username',
        "set_sup_phone": 'Support phone',
        "set_sup_email": 'Support email',
        "set_admin_contact": 'Contact for appeals',
        "set_referral": 'Referral %',
        "settings_saved": 'Settings saved',
        "maintenance_lbl": 'Maintenance mode',
        "maintenance_hint": 'On: users cannot pay (admins can)',
        "f_auto_delivery": 'Auto delivery',
        "f_ocr": 'Check receipt photo (OCR)',
        "f_nickname": 'Show player nickname by ID',
        "f_id_validation": 'Validate ID format',
        "f_chek_reminder": 'Remind if receipt not sent',
        "toggle_on": 'On',
        "toggle_off": 'Off',
        "admins_title": 'Admins',
        "admin_id_ph": 'User ID (123456789)',
        "admin_add_btn": 'Add',
        "admin_added": 'Admin added',
        "admin_removed": 'Admin removed',
        "cf_admin_del": 'Remove admin: {0}?',
        "admin_self_err": 'You cannot remove yourself',
        "admin_exists": 'Already an admin',
        "admin_no_user": 'User not found',
        "added_by_lbl": 'Added by',
        "you_label": 'You',
        "bc_title": 'Send message',
        "bc_text_ph": 'Message text...',
        "bc_scope_all": 'To everyone',
        "bc_scope_user": 'To one user',
        "bc_user_ph": 'User ID',
        "bc_send": 'Send',
        "bc_sent_all": 'Sent to everyone: {0}',
        "bc_sent_user": 'Sent to user',
        "bc_empty": 'Enter message text',
        "bc_need_user": 'Enter user ID',
        "bc_tg_note": 'Single user: notification + Telegram',
        "export_csv": '⬇️ CSV',
        "export_failed": 'Export error',
        "ref_top_title": 'Top referrers',
        "ref_invites": 'Invites',
        "ref_earned": 'Earned',
        "maintenance_msg": 'Payments temporarily unavailable (maintenance)',
        "maintenance_banner": '🔧 Maintenance in progress...',
        "games_edit_title": 'Edit game',
    },
}


def wt(lang, key, **kw):
    if lang not in ("uz", "ru", "en"):
        lang = "uz"
    text = WEBAPP_I18N.get(lang, WEBAPP_I18N["uz"]).get(key, WEBAPP_I18N["uz"].get(key, key))
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    return text