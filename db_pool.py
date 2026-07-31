# db_pool.py
# SQLite ulanishlar puli.
#
# NEGA KERAK:
# Avvalgi versiyada database.py'dagi HAR BIR funksiya o'zining SQLite ulanishini
# ochib, ishini tugatgach yopardi (`sqlite3.connect()` -> ... -> `conn.close()`).
# Bitta sahifa yuklanganda o'nlab bunday funksiya chaqirilishi mumkin — demak
# o'nlab marta fayl ochib-yopiladi. Bu kam sonli foydalanuvchida sezilmaydi,
# lekin foydalanuvchilar ko'paygach sezilarli sekinlashuvga va vaqti-vaqti bilan
# "database is locked" xatoliklariga olib keladi.
#
# Yechim: server ishga tushganda oldindan bir nechta (POOL_SIZE) ulanish ochib
# qo'yamiz va ularni navbat (Queue) orqali qayta-qayta beramiz/qaytarib olamiz.
# Bundan tashqari WAL rejimi yoqilgan — bu bir vaqtning o'zida o'qish va yozish
# amallari bir-biriga xalaqit bermasligini ta'minlaydi.

import contextlib
import queue
import sqlite3
import threading

from config import DB_PATH

POOL_SIZE = 8

_pool: "queue.Queue[sqlite3.Connection]" = queue.Queue(maxsize=POOL_SIZE)
_pool_lock = threading.Lock()
_pool_initialized = False


def _create_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")   # bir vaqtda o'qish + yozishga ruxsat beradi
    conn.execute("PRAGMA busy_timeout = 5000")  # baza band bo'lsa xato bermay, 5s kutadi
    return conn


def init_pool() -> None:
    """Server ishga tushganda (database.init_db() ichida) bir marta chaqiriladi."""
    global _pool_initialized
    with _pool_lock:
        if _pool_initialized:
            return
        for _ in range(POOL_SIZE):
            _pool.put(_create_connection())
        _pool_initialized = True


@contextlib.contextmanager
def get_connection():
    """
    Puldan bitta tayyor ulanish oladi, foydalanib bo'lgach avtomatik puliga
    qaytaradi (xatolik yuz bersa ham qaytaradi — 'finally' orqali).

    Ishlatilishi:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ...")
            conn.commit()
    """
    if not _pool_initialized:
        init_pool()
    conn = _pool.get()
    try:
        yield conn
    finally:
        _pool.put(conn)
