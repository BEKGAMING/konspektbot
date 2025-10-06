# UstozKonspektBot

## O‘rnatish va ishga tushirish

1. Python 3.10+ o‘rnating
2. Quyidagi kutubxonalarni o‘rnating:
   ```
   pip install aiogram==3.* openai python-docx
   ```
3. `config.py` faylida OpenAI API kalitini kiriting.
4. Botni ishga tushiring:
   ```
   python main.py
   ```

## Foydalanish

- /start — botni boshlash
- Fan/Sinf/Mavzu kiritib konspekt olish
- Chek (rasm) yuborib premium so‘rash
- Admin buyruqlari: /approve, /block, /users, /payments

## Eslatma

- Konspekt preview faqat 20% ko‘rsatiladi, to‘liq fayl uchun premium bo‘ling.
- To‘lov cheki adminga yuboriladi, tasdiqlangach premium ochiladi.
