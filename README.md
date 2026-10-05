# ⭐ Telegram Stars Referral Bot

Foydalanuvchilar do‘stlarini taklif qilib **Stars** yig‘adigan Telegram bot.
Python 3.11+, **aiogram 3**, PostgreSQL (SQLAlchemy 2 async), Alembic, Redis, Docker.

## 1. Project haqida

- `/start` → ro‘yxatdan o‘tish → majburiy kanallarga obuna tekshiruvi → asosiy menyu
- Shaxsiy referral link, referral reward (`+5 ⭐` default), milestone bonuslar, kunlik bonus
- Profil, statistika, reyting (Top 10 + o‘z o‘rni)
- Withdrawal so‘rovlari (FSM) va admin tomonidan ko‘rib chiqish
- Admin panel: users, statistika, withdrawals, broadcast, kanallar, bonus/sozlamalar, reyting, banned users
- Anti-fraud: DB constraint'lar + service darajasidagi tekshiruvlar, atomik balans, idempotent reward

### Arxitektura

```text
handlers  →  services  →  repositories  →  models (PostgreSQL)
(Telegram)   (biznes)     (faqat SQL)
```

| Qatlam | Vazifa |
|---|---|
| `app/handlers` | Telegram update'lari, matnlar. DB logikasi yo‘q |
| `app/services` | Biznes qoidalar: `referral`, `withdrawal`, `balance`, `bonus`, `subscription`, `stars`, `broadcast` |
| `app/database/repositories` | SQL so‘rovlar (commit qilmaydi) |
| `app/middlewares` | DB session, user context/ban, obuna tekshiruvi, admin-only, rate limit (Redis) |

**Muhim dizayn qarorlari**

1. **Balans faqat `BalanceService.apply()` orqali** o‘zgaradi: `UPDATE ... WHERE balance + delta >= 0` (atomik) + `transactions` yozuvi. `user.balance += x` ishlatilmaydi.
2. **Withdrawal paytida balans darhol zaxiralanadi** (yechiladi). `Reject` → `refund` tranzaksiyasi bilan qaytariladi, `Approve` → `total_withdrawn` oshadi. Shu sababli parallel so‘rovlar orqali balansdan ortiq so‘rash mumkin emas.
3. **Double approve/reject yo‘q:** `UPDATE ... WHERE status='pending'` — faqat bitta chaqiruv o‘tadi.
4. **Referral reward obuna tasdiqlangandan keyin beriladi.** `/start` paytida faqat *pending* referral yoziladi; referred user barcha majburiy kanallarga obuna bo‘lib “✅ Tekshirish”dan o‘tgach reward beriladi (soxta akkauntlar bilan farm qilishni qiyinlashtiradi). Kanal yo‘q bo‘lsa reward darhol beriladi.
5. **Milestone bonuslari** (`user_milestones`, `UNIQUE(user_id, milestone)`) — har biri bir marta. Default **qo‘shimcha** bonuslar: `10→+5, 20→+10, 50→+25, 100→+50` ⭐ (admin panelda *Bonuses → Milestone bonuslari* orqali o‘zgartirasiz; `0` — o‘chirish). Referral menyusidagi jadval `N × reward` ni ko‘rsatadi.
6. Kunlik bonus: `UNIQUE(user_id, claim_date)`, sana `TIMEZONE` (default `Asia/Tashkent`) bo‘yicha.

## 2. Requirements

- Python 3.11+ (lokal ishga tushirish uchun)
- Docker + Docker Compose (tavsiya etiladi)
- PostgreSQL 14+ va Redis 6+ (Docker ishlatmasangiz)

## 3. `.env` sozlash

```bash
cp .env.example .env
```

| O‘zgaruvchi | Izoh |
|---|---|
| `BOT_TOKEN` | BotFather bergan token. **Hech qachon GitHub'ga yuklamang** |
| `BOT_USERNAME` | `@`siz username (referral linklar uchun) |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | `redis://host:6379/0` |
| `ADMIN_IDS` | Admin Telegram ID'lari, vergul bilan: `111,222` |
| `REFERRAL_REWARD` / `MIN_WITHDRAWAL` | Default qiymatlar (keyin admin paneldan o‘zgartiriladi) |
| `TIMEZONE`, `LOG_LEVEL`, `LOG_DIR` | Ixtiyoriy |

> Docker compose uchun `DATABASE_URL`/`REDIS_URL`dagi host `db` va `redis` bo‘ladi (`.env.example`dagidek).
> **Lokal** ishga tushirsangiz `localhost` yozing.

## 4. BotFather sozlamalari

1. `@BotFather` → `/newbot` → nom va username → **token**ni `.env`ga yozing.
2. Username'ni `BOT_USERNAME`ga yozing.
3. (Ixtiyoriy) `/setcommands` → `start - Botni ishga tushirish`.
4. Majburiy kanallar uchun **botni har bir kanalga administrator** qilib qo‘shing (aks holda `getChatMember` ishlamaydi).

## 5. PostgreSQL sozlash

Docker bilan avtomatik. Qo‘lda:

```sql
CREATE DATABASE referral_bot;
```

## 6. Redis sozlash

Docker bilan avtomatik. Redis FSM holatlari, rate limit va obuna cache’i uchun ishlatiladi.

## 7. Migration

```bash
alembic upgrade head
```

`DATABASE_URL` `.env`dan olinadi. Docker ishlatsangiz, `bot` konteyneri har startda migratsiyani **o‘zi** qo‘llaydi.
Yangi migration yaratish: `alembic revision --autogenerate -m "izoh"`.

## 8. Lokal ishga tushirish

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # va DATABASE_URL/REDIS_URL'da hostni localhost qiling
docker compose up -d db redis     # faqat DB va Redis
alembic upgrade head
python -m app.bot
```

Testlar (DB/Redis kerak emas, in-memory SQLite):

```bash
pytest
```

## 9. Docker bilan ishga tushirish

```bash
cp .env.example .env     # BOT_TOKEN, BOT_USERNAME, ADMIN_IDS ni to‘ldiring
docker compose up -d --build
docker compose logs -f bot
```

Kerak bo‘lsa migratsiyani qo‘lda: `docker compose exec bot alembic upgrade head`.
Loglar `./logs/` papkasida: `bot.log`, `errors.log` (traceback), `audit.log` (referral, withdrawal, admin harakatlari). Token loglarda `***` bilan yashiriladi.

## 10. Admin ID qo‘yish

1. Telegram ID'ngizni bilish: `@userinfobot`.
2. `.env`: `ADMIN_IDS=123456789,987654321`
3. Botni qayta ishga tushiring, botga `/start`, keyin `/admin`.

Admin paneldagi barcha xabar va callback’lar `AdminOnlyMiddleware` orqali himoyalangan (ruxsatsiz urinishlar `audit.log`ga yoziladi).

## 11. Majburiy kanal qo‘shish

1. Botni kanalga **administrator** qiling.
2. `/admin` → **📢 Channels** → **➕ Kanal qo‘shish**.
3. Public kanal: `@kanal_username` yuboring.
   Private kanal: birinchi qatorda ID (`-100...`), ikkinchi qatorda invite link (`https://t.me/+...`).
4. Kanalni o‘chirish: ro‘yxatdagi **➖** tugma.

Bot kanalda admin bo‘lmasa yoki kanal topilmasa, `getChatMember` xatosi `errors.log`ga yoziladi va shu kanal tekshiruvdan **o‘tkazib yuboriladi** (foydalanuvchilar qamalib qolmasligi uchun). Loglarni kuzatib turing.

## 12. ⚠️ Telegram Stars bilan bog‘liq cheklovlar

Telegram Bot API’da Stars bilan bog‘liq metodlar: `sendInvoice` / `createInvoiceLink` (valyuta `XTR`), `answerPreCheckoutQuery`, `refundStarPayment`, `getStarTransactions`, `getMyStarBalance`, shuningdek sovg‘alar (`getAvailableGifts`, `sendGift`, `convertGiftToStars`).

**Botdan foydalanuvchiga Stars’ni to‘g‘ridan-to‘g‘ri o‘tkazib beradigan (payout) metod yo‘q.** Shuning uchun bu loyihada:

- Bot **hisob-kitob** (balans, tarix, so‘rovlar) yuritadi — Stars ichki hisob birligi sifatida.
- **To‘lovni admin qo‘lda** bajaradi: so‘rovda ko‘rsatilgan foydalanuvchiga Stars’ni Telegram orqali yuboradi va **✅ Approve** bosadi (bot admin’ga yo‘riqnoma ko‘rsatadi). Yuborib bo‘lmasa **❌ Reject** — balans qaytariladi.
- Admin → Withdrawals bo‘limida botning Stars balansi (`getMyStarBalance`) ma’lumot uchun ko‘rsatiladi (agar API qaytarsa).
- Bot Stars qabul qilmaydi (invoice yo‘q), shuning uchun `refundStarPayment` ishlatilmaydi.

Telegram kelajakda payout imkonini qo‘shsa, integratsiyani **faqat** `app/services/stars_service.py` ga qo‘shing; `WithdrawalService.approve()` o‘zgarmaydi. Kod yozishdan oldin imkoniyatni rasmiy hujjatda tekshiring: https://core.telegram.org/bots/api

> Eslatma: Stars bilan rasmiy bo‘lmagan “pul yechish” va’dalari Telegram qoidalariga zid bo‘lishi mumkin. Botni ommaga chiqarishdan oldin Telegram Bot/Stars shartlarini va mahalliy qonunchilikni o‘zingiz tekshiring.

## 13. Production deployment

- `docker-compose.yml`dagi Postgres parolini o‘zgartiring (va `DATABASE_URL`ni moslang); portlar faqat `127.0.0.1`ga ochilgan.
- `.env`ni serverda saqlang, repoga qo‘ymang. `chmod 600 .env`.
- **Faqat bitta bot instansiyasi** (long polling) ishlasin — ikkita bir vaqtda ishlasa `TelegramConflictError` bo‘ladi.
- PostgreSQL uchun muntazam backup (`pg_dump`) sozlang; `pgdata` va `redisdata` volume’lari doimiy.
- `restart: unless-stopped` crash’dan keyin qayta ishga tushiradi; `docker compose logs -f bot` bilan kuzating.
- Katta trafik uchun webhook rejimiga o‘tish mumkin (hozir polling).
- Broadcast ~25 xabar/soniya tezlikda ketadi, `RetryAfter`ga rioya qiladi, botni bloklaganlar `is_active=false` bo‘ladi.

## Rate limit (Redis)

`/start` — 5 ta/60 s, callback — 20 ta/10 s, oddiy xabar — 10 ta/10 s (foydalanuvchi bo‘yicha). Kunlik bonus ham DB constraint bilan himoyalangan.

## Loyiha tuzilmasi

```text
app/
├── bot.py  config.py  texts.py  logging_config.py
├── handlers/        start, menu, referral, profile, withdraw, leaderboard, bonus, errors, admin/
├── keyboards/       user, referral, admin
├── middlewares/     db, user_context, subscription, admin_only, throttling
├── database/        models, database, repositories/
├── services/        referral, subscription, stars, withdrawal, bonus, balance, settings, stats, broadcast
├── states/          withdraw, admin
└── utils/           referral, validators, helpers
migrations/  tests/  Dockerfile  docker-compose.yml  alembic.ini
```
# referalstars
# referalstars
