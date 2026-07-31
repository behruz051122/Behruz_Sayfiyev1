# rate_limit.py
# Butun ilova uchun bitta umumiy Limiter obyekti. server.py uni ilovaga ulaydi,
# routers/admin_auth.py esa login endpointini shu bilan cheklaydi.
# Alohida faylga chiqarilgan sababi: agar shu obyekt to'g'ridan-to'g'ri server.py
# ichida yaratilsa, routers/*.py fayllari server.py'ni import qilishga majbur
# bo'lardi — bu esa "server.py -> routers -> server.py" aylanma bog'liqlik
# (circular import) hosil qiladi.

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
