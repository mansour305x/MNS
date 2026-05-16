# Telegram Pro Bot — بوت تيلجرام احترافي كامل

بوت تيلجرام احترافي جاهز للتشغيل، مخصص كبنية قوية لأي مشروع عربي يحتاج إدارة مستخدمين، أزرار، لوحة إدارة داخل تيلجرام، رسائل جماعية، صلاحيات، حماية من السبام، سجلات أخطاء، ونسخ احتياطي.

## المزايا

- رسالة ترحيب احترافية.
- قائمة رئيسية Reply Keyboard.
- أزرار Inline للوحة الإدارة والإعدادات.
- أوامر: `/start`, `/help`, `/settings`, `/admin`, `/cancel`, `/role`.
- لوحة إدارة داخل تيلجرام.
- حفظ المستخدمين في قاعدة البيانات.
- أدوار: admin, moderator, user.
- حظر وفك حظر المستخدمين.
- إحصائيات عامة.
- إرسال جماعي نصي أو صورة أو ملف.
- حماية Rate Limit ضد السبام.
- سجلات أخطاء تقنية في قاعدة البيانات.
- إشعارات للمستخدمين.
- نسخ احتياطي JSON وCSV.
- Health server للاستضافة.
- تشغيل محلي SQLite ونشر PostgreSQL.
- Dockerfile وRender config.

## التقنية

- Python 3.12
- python-telegram-bot 22.7
- SQLAlchemy 2
- SQLite محلياً
- PostgreSQL للإنتاج
- FastAPI + Uvicorn لمسار الصحة `/health`

## إنشاء البوت

1. افتح تيلجرام وادخل على BotFather.
2. أنشئ بوتاً جديداً وخذ `BOT_TOKEN`.
3. احصل على Telegram ID الخاص بك وضعه في `ADMIN_IDS`.

## التشغيل المحلي

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# عدل BOT_TOKEN و ADMIN_IDS داخل .env
python -m app.main
```

ثم افتح البوت في تيلجرام وأرسل:

```text
/start
/admin
```

## متغيرات البيئة

راجع `.env.example`.

أهم المتغيرات:

- `BOT_TOKEN`: توكن البوت من BotFather.
- `ADMIN_IDS`: معرفات المديرين مفصولة بفاصلة.
- `DATABASE_URL`: رابط قاعدة البيانات.
- `PORT`: منفذ Health server.

## PostgreSQL للإنتاج

استخدم رابط PostgreSQL من Neon أو Supabase أو أي مزود PostgreSQL.

مثال:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
```

## النشر عبر Docker

```bash
docker build -t telegram-pro-bot .
docker run --env-file .env -p 8080:8080 telegram-pro-bot
```

## النشر على Koyeb

راجع `deploy/koyeb.md`.

## النشر على Render

راجع `deploy/render.md`. Render Free مناسب للتجربة وليس إنتاجاً مستقراً 24/7.

## الاختبارات

```bash
pytest -q
```

## لوحة الإدارة

الأمر:

```text
/admin
```

تشمل:

- الإحصائيات.
- المستخدمون.
- الإرسال الجماعي.
- الحظر وفك الحظر.
- إدارة الصلاحيات.
- تعديل رسالة الترحيب.
- وضع الصيانة.
- النسخ الاحتياطي.
- آخر الأخطاء.

## إدارة الصلاحيات

من لوحة الإدارة أو بالأمر:

```text
/role 123456789 moderator
/role 123456789 user
/role 123456789 admin
```

## ملاحظات أمنية

- لا تضع `BOT_TOKEN` داخل الكود.
- لا ترفع ملف `.env` إلى GitHub.
- استخدم PostgreSQL في الإنتاج، وليس SQLite على استضافة ذات ملفات مؤقتة.
- راقب سجلات الأخطاء والرسائل الجماعية.
- لا ترفع حدود الإرسال الجماعي عشوائياً حتى لا تتعرض لأخطاء Telegram rate limit.
