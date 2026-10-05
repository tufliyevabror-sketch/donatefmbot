"""Handler paketlari — faza 1: faqat helpers.

Keyingi fazalarda har bir bo'lim o'z Router() ini oladi:
  handlers/start.py      — /start, bosh menyu
  handlers/catalog.py    — o'yinlar katalogi
  handlers/payments.py   — balans/topup, chek qabul
  handlers/admin.py      — admin panel
  handlers/support.py    — yordam/FAQ/murojaat
va bot.py dagi yakka `router` o'rniga:
  from handlers import include_all
  include_all(dp)
"""
