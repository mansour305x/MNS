# نشر البوت على Koyeb عبر Docker

1. ارفع المشروع إلى GitHub.
2. ادخل إلى Koyeb وأنشئ App جديدة من GitHub.
3. اختر Dockerfile الموجود في جذر المشروع.
4. اختر Instance من نوع `free` إن كان متاحاً في حسابك.
5. أضف متغيرات البيئة:
   - BOT_TOKEN
   - ADMIN_IDS
   - DATABASE_URL
   - ENVIRONMENT=production
   - LOG_LEVEL=INFO
   - PORT=8080
6. اجعل Health check على المسار `/health`.
7. Deploy.
8. بعد التشغيل، افتح البوت في تيلجرام وأرسل /start.

مهم: استخدم PostgreSQL خارجي مثل Neon Free بدلاً من SQLite للإنتاج؛ لأن ملفات الحاوية قد لا تكون خياراً موثوقاً للحفظ الدائم عند إعادة النشر.
