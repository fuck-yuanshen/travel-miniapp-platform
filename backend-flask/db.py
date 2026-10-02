import os
import sqlite3
from hashlib import sha256
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import g

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "travel.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS merchants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    license_no TEXT,
    owner_user_id INTEGER NOT NULL UNIQUE,
    audit_status TEXT NOT NULL DEFAULT 'pending',
    rating REAL NOT NULL DEFAULT 5,
    created_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS banners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    image TEXT NOT NULL,
    link TEXT,
    sort INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    category_id INTEGER,
    status TEXT NOT NULL DEFAULT 'on_sale',
    base_price REAL NOT NULL,
    cover TEXT,
    detail TEXT,
    depart_city TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(merchant_id) REFERENCES merchants(id),
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS product_sku_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    sold INTEGER NOT NULL DEFAULT 0,
    UNIQUE(product_id, date),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    client_req_no TEXT,
    user_id INTEGER NOT NULL,
    merchant_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    pay_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    travel_date TEXT NOT NULL,
    qty INTEGER NOT NULL,
    remark TEXT,
    cancelled_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(merchant_id) REFERENCES merchants(id),
    UNIQUE(user_id, client_req_no)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    sku_date TEXT NOT NULL,
    unit_price REAL NOT NULL,
    qty INTEGER NOT NULL,
    title TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    pay_method TEXT NOT NULL,
    pay_status TEXT NOT NULL,
    mock_txn_no TEXT NOT NULL UNIQUE,
    paid_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    refund_no TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    reason TEXT,
    audit_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    content TEXT,
    images TEXT,
    reply TEXT,
    audit_status TEXT NOT NULL DEFAULT 'approved',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER,
    actor_role TEXT,
    action TEXT NOT NULL,
    target_id TEXT,
    trace_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    idem_key TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(scope, idem_key)
);

CREATE INDEX IF NOT EXISTS idx_products_category_status ON products(category_id, status);
CREATE INDEX IF NOT EXISTS idx_sku_product_date ON product_sku_calendar(product_id, date);
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_merchant_status ON orders(merchant_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
"""


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    migrate_db(conn)
    conn.commit()
    conn.close()
    seed_demo_data()


def _column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def migrate_db(conn):
    if not _column_exists(conn, "users", "username"):
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if not _column_exists(conn, "users", "password_hash"):
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

    conn.execute(
        """
        UPDATE users
        SET username = CASE
            WHEN username IS NULL OR username = '' THEN
                CASE
                    WHEN openid IS NULL OR openid = '' THEN 'user_' || id
                    ELSE REPLACE(openid, '-', '_')
                END
            ELSE username
        END
        """
    )
    conn.execute(
        """
        UPDATE users
        SET password_hash = COALESCE(NULLIF(password_hash, ''), ?)
        """,
        (sha256((os.getenv("TRAVEL_DEMO_PASSWORD") or "change-me-before-use").encode("utf-8")).hexdigest(),),
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")


def seed_demo_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    now = now_str()

    demo_password = os.getenv("TRAVEL_DEMO_PASSWORD") or "change-me-before-use"
    demo_users = [
        ("user-openid", "user01", demo_password, "演示用户", "13800000001", "user"),
        ("merchant-openid", "merchant01", demo_password, "演示商家账号", "13800000002", "merchant"),
        ("admin-openid", "admin01", demo_password, "平台管理员", "13800000003", "admin"),
    ]
    for openid, username, password, nickname, phone, role in demo_users:
        password_hash = sha256(password.encode("utf-8")).hexdigest()
        conn.execute(
            """
            INSERT INTO users(openid, username, password_hash, nickname, phone, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            ON CONFLICT(openid) DO UPDATE SET
                username = excluded.username,
                password_hash = excluded.password_hash,
                nickname = excluded.nickname,
                phone = excluded.phone,
                role = excluded.role,
                status = 'active'
            """,
            (openid, username, password_hash, nickname, phone, role, now),
        )

    merchant_user = conn.execute(
        "SELECT id FROM users WHERE openid = ?",
        ("merchant-openid",),
    ).fetchone()
    merchant_user_id = merchant_user["id"]
    conn.execute(
        """
        INSERT OR IGNORE INTO merchants(name, license_no, owner_user_id, audit_status, rating, created_at)
        VALUES (?, ?, ?, 'approved', 4.8, ?)
        """,
        ("山海旅业旗舰店", "LIC-DEMO-001", merchant_user_id, now),
    )

    categories = ["周边游", "自由行", "亲子游", "海岛度假"]
    for category in categories:
        conn.execute(
            """
            INSERT OR IGNORE INTO categories(name, status, created_at)
            VALUES (?, 'active', ?)
            """,
            (category, now),
        )

    if conn.execute("SELECT COUNT(1) AS c FROM banners").fetchone()["c"] == 0:
        banners = [
            (
                "春季海岛特惠",
                "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1400&q=80",
                "/pages/index/index",
                1,
                1,
                now,
            ),
            (
                "周末周边短途",
                "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1400&q=80",
                "/pages/index/index",
                2,
                1,
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO banners(title, image, link, sort, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            banners,
        )

    if conn.execute("SELECT COUNT(1) AS c FROM products").fetchone()["c"] == 0:
        merchant_id = conn.execute(
            "SELECT id FROM merchants WHERE owner_user_id = ?",
            (merchant_user_id,),
        ).fetchone()["id"]

        category_rows = conn.execute(
            "SELECT id, name FROM categories",
        ).fetchall()
        category_map = {row["name"]: row["id"] for row in category_rows}

        products = [
            (
                merchant_id,
                "厦门鼓浪屿 3 天 2 晚自由行",
                category_map["自由行"],
                "on_sale",
                1299,
                "https://images.unsplash.com/photo-1483683804023-6ccdb62f86ef?auto=format&fit=crop&w=1200&q=80",
                "含往返车船票与精选酒店，适合情侣与家庭轻松出游。",
                "广州",
                "海岛,轻度假,摄影",
                now,
                now,
            ),
            (
                merchant_id,
                "清远温泉山野周末 2 日游",
                category_map["周边游"],
                "on_sale",
                599,
                "https://images.unsplash.com/photo-1526779259212-939e64788e3c?auto=format&fit=crop&w=1200&q=80",
                "周末出行优选，含精品民宿、温泉门票和轻徒步线路。",
                "深圳",
                "温泉,周末,亲子",
                now,
                now,
            ),
            (
                merchant_id,
                "三亚亲子海滨度假 4 天 3 晚",
                category_map["亲子游"],
                "on_sale",
                2199,
                "https://images.unsplash.com/photo-1506956191951-7a88da4435e5?auto=format&fit=crop&w=1200&q=80",
                "亲子主题酒店 + 海洋馆套票，含接送机与旅行管家服务。",
                "北京",
                "亲子,海边,高端",
                now,
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO products(
                merchant_id, title, category_id, status, base_price, cover, detail, depart_city, tags, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            products,
        )

    if conn.execute("SELECT COUNT(1) AS c FROM product_sku_calendar").fetchone()["c"] == 0:
        product_rows = conn.execute("SELECT id, base_price FROM products").fetchall()
        calendar_rows = []
        for product in product_rows:
            for index in range(0, 30):
                travel_date = (date.today() + timedelta(days=index)).isoformat()
                price = round(float(product["base_price"]) + (index % 5) * 30, 2)
                stock = 20 + ((index * 3) % 10)
                calendar_rows.append((product["id"], travel_date, price, stock, 0))

        conn.executemany(
            """
            INSERT INTO product_sku_calendar(product_id, date, price, stock, sold)
            VALUES (?, ?, ?, ?, ?)
            """,
            calendar_rows,
        )

    conn.commit()
    conn.close()
