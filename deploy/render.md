# نشر البوت على Render

Render مناسب للتجربة، لكن الخطة المجانية قد تدخل في وضع خمول بعد عدم وجود زيارات، وقد تفقد الملفات المحلية عند إعادة النشر. لذلك لا تعتمد على SQLite في Render؛ استخدم PostgreSQL خارجي.

الخطوات:
1. ارفع المشروع إلى GitHub.
2. في Render اختر New > Web Service.
3. اربط المستودع.
4. Build Command:
   pip install -r requirements.txt
5. Start Command:
   python -m app.main
6. أضف المتغيرات:
   BOT_TOKEN, ADMIN_IDS, DATABASE_URL, ENVIRONMENT=production, PORT=8080
7. افتح /health للتأكد من عمل الخدمة.
8. افتح تيلجرام وأرسل /start.
