# Noon to'lov boti

Telegram orqali kelgan to'lov xabarlarini Notion "Noon" bazasiga avtomatik yozadi.

## Ishchi qanday yuboradi

3 qatorli xabar:

```
200
10:12
344
```

- 1-qator — **Summa**
- 2-qator — **To'lov vaqti**
- 3-qator — **№**

Bot avtomatik qo'shadi: **Sana** (bugungi kun), **Xabar vaqti** (hozirgi vaqt, Toshkent), **Status** = "Not started".

---

## 1-qadam: Notion Integration yaratish

1. https://www.notion.so/my-integrations manziliga kiring
2. **New integration** → nom bering (masalan "Noon Bot") → **Submit**
3. **Internal Integration Secret** ni nusxalab oling (`ntn_...` bilan boshlanadi) — bu `NOTION_TOKEN`
4. Noon bazasini Notionda oching → yuqoridagi **...** menyu → **Connections** → **Noon Bot** ni ulang

> ⚠️ Integratsiyani bazaga ulashni unutmang, aks holda bot yoza olmaydi.

## 2-qadam: Telegram bot yaratish

1. Telegramda **@BotFather** ga yozing → `/newbot`
2. Nom va username bering
3. Berilgan **token** ni saqlang — bu `TELEGRAM_TOKEN`

## 2b-qadam: Botni KANALGA qo'shish

Ishchilar kanalga post qilgani uchun:

1. Kanalingizni oching → **Manage Channel** → **Administrators** → **Add Admin**
2. Botingizni qidirib toping va **admin** qilib qo'shing
3. Botga hech bo'lmasa "post o'qish" ruxsatini bering (odatda admin bo'lsa yetarli)

> ⚠️ Kanalda bot **javob yoza olmaydi** (kanalga faqat adminlar post qiladi). Shuning uchun bot tasdiq va xato xabarlarini alohida **log guruhiga** yuboradi. Buning uchun:
>
> 1. Yangi Telegram **guruh** yarating (masalan "Noon Bot Log")
> 2. Botni o'sha guruhga qo'shing
> 3. Guruhda `/chatid` yuboring → ID ni oling (masalan `-1001234567890`)
> 4. Railway'da `LOG_CHAT_ID` ga shu ID ni qo'ying
>
> `LOG_CHAT_ID` ni qo'ymasangiz, bot jimgina ishlaydi (Notionga yozadi, lekin hech qayerga tasdiq yubormaydi). Xatolarni faqat Railway loglaridan ko'rasiz.

### Kanal ID'sini bilish

Ruxsatni cheklamoqchi bo'lsangiz (`ALLOWED_CHAT_IDS`), kanal ID'si kerak. Uni bilish uchun bot admin bo'lgach kanalga bitto oddiy post tashlang — Railway loglarida `Ruxsatsiz chat: -100...` yoki qo'shilgani ko'rinadi. Yoki kanalga `/chatid` post qiling.

## 3-qadam: GitHub'ga qo'yish

Bu papkadagi fayllarni yangi GitHub repozitoriyasiga yuklang.

## 4-qadam: Railway'da deploy

1. https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Repozitoriyangizni tanlang
3. **Variables** bo'limiga o'ting va quyidagilarni qo'shing:

| Nomi | Qiymati |
|------|---------|
| `TELEGRAM_TOKEN` | BotFather bergan token |
| `NOTION_TOKEN` | Notion integration secret (`ntn_...`) |
| `NOTION_DATA_SOURCE_ID` | `5b33d198-322c-40a3-9e4f-594dc88b3ccf` |
| `LOG_CHAT_ID` | (tavsiya) tasdiqlar yuboriladigan log guruhi ID'si |
| `ALLOWED_CHAT_IDS` | (ixtiyoriy) ruxsat etilgan chat ID'lar, vergul bilan |

4. Railway avtomatik deploy qiladi. **Deploy Logs** da `Bot ishga tushdi...` yozuvini ko'rsangiz — tayyor.

---

## Foydali buyruqlar

- `/start` — yo'riqnoma
- `/chatid` — shu chatning ID'sini ko'rsatadi (ruxsatni cheklash uchun kerak bo'lsa)

## ALLOWED_CHAT_IDS haqida

Agar botga faqat bitta guruhdan yozishga ruxsat bermoqchi bo'lsangiz:

1. Botni guruhga qo'shing
2. Guruhda `/chatid` yuboring → ID ni oling (masalan `-1001234567890`)
3. Railway Variables'da `ALLOWED_CHAT_IDS` ga shu ID ni qo'ying

Bo'sh qoldirsangiz — hamma chatdan yozish mumkin bo'ladi.
