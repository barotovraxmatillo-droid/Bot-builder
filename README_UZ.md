# Telegram shablon bot yaratuvchi (MVP)

Bu loyiha SafoBuilder uslubidagi boshlang‘ich prototip. Foydalanuvchi Kino, SMM yoki Do‘kon shablonini tanlaydi, o‘z bot tokenini yuboradi va bot shu Python jarayonida ishga tushadi.

## Muhim cheklovlar
- Bu loyiha tayyor MVP; to‘liq SafoBuilder kloni emas.
- Kino katalogi, mahsulotlar va xizmat narxlari demo matnlar. Ularni keyin ma’lumotlar bazasi/admin panel bilan kengaytirish kerak.
- Bot tokenlari `bots.db` ichida saqlanadi. Faqat o‘zingiz boshqaradigan botlar uchun foydalaning va server fayllariga kirishni himoyalang.
- Hostingning bepul rejasi uxlab qolishi yoki cheklanishi mumkin; 24/7 kafolatlanmaydi.
- Ko‘p botlarni ishga tushirish server xotirasi va so‘rov limitlariga bog‘liq.
- Token noto‘g‘ri yoki bekor qilingan bo‘lsa, bot ishga tushmaydi.

## 1. Asosiy bot tokenini olish
Telegramda `@BotFather` ni oching, `/newbot` yuboring va yangi builder bot tokenini oling.

## 2. Telefon orqali ishga tushirish (Termux)
```bash
pkg update
pkg install python
pip install -r requirements.txt
export BUILDER_TOKEN="BU_YERGA_ASOSIY_BOT_TOKENI"
export ADMIN_ID="TELEGRAM_USER_ID"
python main.py
```
`ADMIN_ID` ixtiyoriy, lekin `/admin` statistikasi uchun o‘zingizning Telegram numeric ID raqamingizni yozing.

## 3. Render kabi worker hosting
1. GitHub’da yangi repository yarating va shu fayllarni yuklang.
2. Hostingda repository’ni ulang.
3. Environment Variables bo‘limida `BUILDER_TOKEN` va `ADMIN_ID` ni kiriting.
4. Deploy qiling.
5. Loglarda xato yo‘qligini tekshiring.

Bepul hosting rejasi o‘zgarishi mumkin; bepul 24/7 ishlash kafolatlanmaydi.

## Shablonlarni kengaytirish
- Kino botga faqat tarqatishga huquqingiz bo‘lgan filmlar/video fayllarini qo‘shing.
- SMM buyurtmalari bot egasiga xabar bo‘lib keladi.
- Do‘kon bot hozircha demo menyu; to‘lovlarni ulashdan oldin buyurtma, xavfsizlik va qaytarish qoidalarini qo‘shing.
