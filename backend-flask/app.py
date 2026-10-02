import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from auth import create_token, require_auth
from db import close_db, get_db, init_db, now_str
from errors import ApiError
from security import hash_password, verify_password
from state_machine import ORDER_STATUS_LABELS, PAY_SUCCESS_STATES, ensure_transition

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
ALLOWED_UPLOAD_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY", "travel-miniapp-demo-secret")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
    app.config["JSON_AS_ASCII"] = False
    app.json.ensure_ascii = False

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    CORS(app, supports_credentials=True)
    init_db()

    app.teardown_appcontext(close_db)

    @app.before_request
    def setup_trace():
        trace_id = request.headers.get("X-Trace-Id", "").strip()
        g.trace_id = trace_id if trace_id else uuid.uuid4().hex

    @app.after_request
    def inject_trace_header(response):
        response.headers["X-Trace-Id"] = g.get("trace_id", "")
        return response

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return (
            jsonify(
                {
                    "code": err.code,
                    "message": err.message,
                    "data": None,
                    "traceId": g.get("trace_id"),
                }
            ),
            err.status,
        )

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_err):
        return (
            jsonify(
                {
                    "code": 40099,
                    "message": "上传文件过大（最大 5MB）",
                    "data": None,
                    "traceId": g.get("trace_id"),
                }
            ),
            413,
        )

    @app.errorhandler(404)
    def handle_not_found(_err):
        return (
            jsonify(
                {
                    "code": 40400,
                    "message": "接口不存在",
                    "data": None,
                    "traceId": g.get("trace_id"),
                }
            ),
            404,
        )

    @app.errorhandler(Exception)
    def handle_unknown(err):
        return (
            jsonify(
                {
                    "code": 50000,
                    "message": f"服务异常: {str(err)}",
                    "data": None,
                    "traceId": g.get("trace_id"),
                }
            ),
            500,
        )

    @app.get("/api/health")
    def health():
        return ok(
            {
                "service": "travel-miniapp-flask",
                "time": now_str(),
                "doc": "P0 链路: 登录-商品-下单-模拟支付-订单流转",
            }
        )

    @app.post("/api/auth/login")
    def auth_login():
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        role = (payload.get("role") or "").strip()

        if not username:
            raise ApiError("账号不能为空", code=40001, status=400)
        if not password:
            raise ApiError("密码不能为空", code=40002, status=400)

        conn = get_db()
        user_row = conn.execute(
            """
            SELECT id, openid, username, password_hash, nickname, phone, role, status, created_at
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        if user_row is None:
            raise ApiError("账号或密码错误", code=40111, status=401)
        if not verify_password(password, user_row["password_hash"]):
            raise ApiError("账号或密码错误", code=40111, status=401)
        if user_row["status"] != "active":
            raise ApiError("账号不可用", code=40112, status=401)
        if role and role != user_row["role"]:
            raise ApiError(
                f"该账号角色为 {user_row['role']}，请使用对应角色登录",
                code=40003,
                status=400,
            )

        # 支持首次登录时改密，便于课程演示
        new_password = payload.get("newPassword")
        if isinstance(new_password, str) and new_password.strip():
            if len(new_password.strip()) < 6:
                raise ApiError("新密码长度至少 6 位", code=40004, status=400)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password.strip()), user_row["id"]),
            )
            conn.commit()
            user_row = conn.execute(
                """
                SELECT id, openid, username, password_hash, nickname, phone, role, status, created_at
                FROM users
                WHERE id = ?
                """,
                (user_row["id"],),
            ).fetchone()

        user = dict(user_row)
        merchant_info = None
        if user["role"] == "merchant":
            merchant_row = conn.execute(
                """
                SELECT id, name, audit_status
                FROM merchants
                WHERE owner_user_id = ?
                """,
                (user["id"],),
            ).fetchone()
            if merchant_row:
                merchant_info = dict(merchant_row)

        token = create_token({"uid": user["id"], "role": user["role"], "ts": now_str()})
        return ok(
            {
                "token": token,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "openid": user["openid"],
                    "nickname": user["nickname"],
                    "phone": user["phone"],
                    "role": user["role"],
                },
                "merchant": merchant_info,
            }
        )

    @app.get("/api/banners")
    def banner_list():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT id, title, image, link, sort, updated_at
            FROM banners
            WHERE enabled = 1
            ORDER BY sort ASC, id DESC
            """
        ).fetchall()
        return ok([dict(row) for row in rows])

    @app.get("/api/categories")
    def category_list():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT id, name, status
            FROM categories
            WHERE status = 'active'
            ORDER BY id ASC
            """
        ).fetchall()
        return ok([dict(row) for row in rows])

    @app.get("/uploads/<path:filename>")
    def upload_file_serve(filename):
        safe_name = secure_filename(filename)
        if not safe_name:
            raise ApiError("文件不存在", code=40491, status=404)
        return send_from_directory(UPLOAD_DIR, safe_name)

    @app.post("/api/upload/image")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def upload_image():
        upload_file = request.files.get("file")
        if upload_file is None:
            raise ApiError("缺少上传文件", code=40096, status=400)
        original_name = secure_filename(upload_file.filename or "")
        if not original_name:
            raise ApiError("文件名无效", code=40097, status=400)
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise ApiError("仅支持 jpg/jpeg/png/webp", code=40098, status=400)

        stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:10]}.{ext}"
        stored_path = os.path.join(UPLOAD_DIR, stored_name)
        upload_file.save(stored_path)
        return ok(
            {
                "url": f"{request.host_url.rstrip('/')}/uploads/{stored_name}",
                "filename": stored_name,
            }
        )

    @app.get("/api/products")
    def product_list():
        keyword = (request.args.get("keyword") or "").strip()
        category_id = request.args.get("categoryId")
        min_price = request.args.get("minPrice")
        max_price = request.args.get("maxPrice")
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=10, minimum=1, maximum=50)

        conditions = ["p.status = 'on_sale'"]
        params = []

        if keyword:
            conditions.append("(p.title LIKE ? OR p.detail LIKE ? OR p.tags LIKE ?)")
            keyword_like = f"%{keyword}%"
            params.extend([keyword_like, keyword_like, keyword_like])

        if category_id:
            conditions.append("p.category_id = ?")
            params.append(int(category_id))

        if min_price:
            conditions.append("COALESCE(ps.min_price, p.base_price) >= ?")
            params.append(float(min_price))

        if max_price:
            conditions.append("COALESCE(ps.min_price, p.base_price) <= ?")
            params.append(float(max_price))

        base_from_sql = """
        FROM products p
        LEFT JOIN (
            SELECT product_id, MIN(price) AS min_price, SUM(stock) AS total_stock
            FROM product_sku_calendar
            GROUP BY product_id
        ) ps ON ps.product_id = p.id
        LEFT JOIN categories c ON c.id = p.category_id
        """
        where_sql = " WHERE " + " AND ".join(conditions)

        conn = get_db()
        total_row = conn.execute(
            "SELECT COUNT(1) AS c " + base_from_sql + where_sql,
            tuple(params),
        ).fetchone()
        total = total_row["c"] if total_row else 0

        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.title,
                p.cover,
                p.base_price,
                p.depart_city,
                p.tags,
                p.merchant_id,
                COALESCE(ps.min_price, p.base_price) AS min_price,
                COALESCE(ps.total_stock, 0) AS total_stock,
                c.name AS category_name
            """
            + base_from_sql
            + where_sql
            + " ORDER BY p.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()

        items = []
        for row in rows:
            product = dict(row)
            product["min_price"] = float(product["min_price"])
            product["base_price"] = float(product["base_price"])
            product["tags"] = (product["tags"] or "").split(",") if product.get("tags") else []
            items.append(product)

        return ok(
            {
                "items": items,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                },
            }
        )

    @app.get("/api/products/<int:product_id>")
    def product_detail(product_id):
        days = to_int(request.args.get("days"), default=30, minimum=1, maximum=90)
        conn = get_db()

        product_row = conn.execute(
            """
            SELECT
                p.id,
                p.title,
                p.cover,
                p.detail,
                p.status,
                p.base_price,
                p.depart_city,
                p.tags,
                p.merchant_id,
                m.name AS merchant_name,
                c.name AS category_name
            FROM products p
            JOIN merchants m ON m.id = p.merchant_id
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.id = ?
            """,
            (product_id,),
        ).fetchone()
        if product_row is None:
            raise ApiError("商品不存在", code=40401, status=404)

        sku_rows = conn.execute(
            """
            SELECT date, price, stock, sold
            FROM product_sku_calendar
            WHERE product_id = ?
            ORDER BY date ASC
            LIMIT ?
            """,
            (product_id, days),
        ).fetchall()

        review_rows = conn.execute(
            """
            SELECT
                r.id,
                r.score,
                r.content,
                r.images,
                r.reply,
                r.created_at,
                u.nickname AS user_nickname
            FROM reviews r
            LEFT JOIN users u ON u.id = r.user_id
            WHERE r.product_id = ? AND r.audit_status = 'approved'
            ORDER BY r.id DESC
            LIMIT 20
            """,
            (product_id,),
        ).fetchall()

        product = dict(product_row)
        product["base_price"] = float(product["base_price"])
        product["tags"] = (product["tags"] or "").split(",") if product.get("tags") else []

        sku_calendar = []
        for row in sku_rows:
            sku = dict(row)
            sku["price"] = float(sku["price"])
            sku_calendar.append(sku)

        reviews = []
        for row in review_rows:
            review = dict(row)
            review["content"] = sanitize_text(review.get("content"))
            review["reply"] = sanitize_text(review.get("reply"))
            review["images"] = parse_json_array(review.get("images"))
            reviews.append(review)

        return ok(
            {
                "product": product,
                "skuCalendar": sku_calendar,
                "reviews": reviews,
            }
        )

    @app.post("/api/orders")
    @require_auth(roles={"user", "admin"})
    def create_order():
        data = request.get_json(silent=True) or {}
        product_id = data.get("productId")
        travel_date = (data.get("travelDate") or "").strip()
        qty = to_int(data.get("qty"), default=1, minimum=1, maximum=9)
        contact_name = (data.get("contactName") or "").strip()
        contact_phone = (data.get("contactPhone") or "").strip()
        remark = (data.get("remark") or "").strip() or None
        client_req_no = (data.get("clientReqNo") or "").strip() or None

        if not product_id:
            raise ApiError("productId 不能为空", code=40011, status=400)
        if not travel_date:
            travel_date = datetime.now().strftime("%Y-%m-%d")
        if not contact_name or not contact_phone:
            raise ApiError("联系人姓名与手机号不能为空", code=40013, status=400)

        actor = g.current_user
        payload = None
        with immediate_transaction() as conn:
            if client_req_no:
                existing_row = conn.execute(
                    """
                    SELECT *
                    FROM orders
                    WHERE user_id = ? AND client_req_no = ?
                    """,
                    (actor["id"], client_req_no),
                ).fetchone()
                if existing_row is not None:
                    payload = {
                        "order": get_order_payload(conn, existing_row),
                        "idempotent": True,
                    }

            if payload is None:
                product_row = conn.execute(
                    """
                    SELECT id, merchant_id, title, status, base_price, tags, category_id
                    FROM products
                    WHERE id = ?
                    """,
                    (product_id,),
                ).fetchone()
                if product_row is None or product_row["status"] != "on_sale":
                    raise ApiError("商品不可下单", code=40014, status=400)

                tags = [tag.strip() for tag in (product_row["tags"] or "").split(",") if tag.strip()]
                is_normal_product = product_row["category_id"] is None or "普通商品" in tags
                if is_normal_product:
                    existing_sku = conn.execute(
                        """
                        SELECT id
                        FROM product_sku_calendar
                        WHERE product_id = ? AND date = ?
                        """,
                        (product_id, travel_date),
                    ).fetchone()
                    if existing_sku is None:
                        conn.execute(
                            """
                            INSERT INTO product_sku_calendar(product_id, date, price, stock, sold)
                            VALUES (?, ?, ?, 999999, 0)
                            """,
                            (product_id, travel_date, float(product_row["base_price"])),
                        )

                stock_updated = conn.execute(
                    """
                    UPDATE product_sku_calendar
                    SET stock = stock - ?, sold = sold + ?
                    WHERE product_id = ? AND date = ? AND stock >= ?
                    """,
                    (qty, qty, product_id, travel_date, qty),
                ).rowcount
                if stock_updated != 1:
                    raise ApiError("库存不足，请选择其他日期", code=40015, status=400)

                sku_row = conn.execute(
                    """
                    SELECT price, stock, sold
                    FROM product_sku_calendar
                    WHERE product_id = ? AND date = ?
                    """,
                    (product_id, travel_date),
                ).fetchone()
                if sku_row is None:
                    raise ApiError("商品日期库存不存在", code=40016, status=400)

                order_no = generate_order_no(conn)
                amount = round(float(sku_row["price"]) * qty, 2)
                created_at = now_str()
                conn.execute(
                    """
                    INSERT INTO orders(
                        order_no, client_req_no, user_id, merchant_id, amount, pay_amount,
                        status, contact_name, contact_phone, travel_date, qty, remark,
                        cancelled_reason, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 'pending_payment', ?, ?, ?, ?, ?, NULL, ?, ?)
                    """,
                    (
                        order_no,
                        client_req_no,
                        actor["id"],
                        product_row["merchant_id"],
                        amount,
                        contact_name,
                        contact_phone,
                        travel_date,
                        qty,
                        remark,
                        created_at,
                        created_at,
                    ),
                )
                order_id = conn.execute(
                    "SELECT id FROM orders WHERE order_no = ?",
                    (order_no,),
                ).fetchone()["id"]
                conn.execute(
                    """
                    INSERT INTO order_items(order_id, product_id, sku_date, unit_price, qty, title)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, product_id, travel_date, float(sku_row["price"]), qty, product_row["title"]),
                )
                insert_operation_log(
                    conn,
                    actor_id=actor["id"],
                    actor_role=actor["role"],
                    action="order.create",
                    target_id=order_no,
                    detail=json.dumps(
                        {"productId": product_id, "travelDate": travel_date, "qty": qty},
                        ensure_ascii=False,
                    ),
                )
                created_row = conn.execute(
                    "SELECT * FROM orders WHERE id = ?",
                    (order_id,),
                ).fetchone()
                payload = {"order": get_order_payload(conn, created_row), "idempotent": False}

        return ok(payload)

    @app.get("/api/orders")
    @require_auth(roles={"user", "merchant", "admin"}, merchant_approved=True)
    def order_list():
        user = g.current_user
        status = (request.args.get("status") or "").strip()
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=10, minimum=1, maximum=50)

        conditions = []
        params = []
        if user["role"] == "user":
            conditions.append("o.user_id = ?")
            params.append(user["id"])
        elif user["role"] == "merchant":
            conditions.append("o.merchant_id = ?")
            params.append(user["merchant_id"])

        if status:
            conditions.append("o.status = ?")
            params.append(status)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""
        conn = get_db()
        total_row = conn.execute(
            "SELECT COUNT(1) AS c FROM orders o" + where_sql,
            tuple(params),
        ).fetchone()
        total = total_row["c"] if total_row else 0

        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT
                o.*,
                oi.title AS product_title,
                oi.unit_price AS unit_price,
                oi.qty AS item_qty
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            """
            + where_sql
            + " ORDER BY o.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()

        items = []
        for row in rows:
            record = dict(row)
            items.append(
                {
                    "orderNo": record["order_no"],
                    "status": record["status"],
                    "statusLabel": ORDER_STATUS_LABELS.get(record["status"], record["status"]),
                    "amount": float(record["amount"]),
                    "payAmount": float(record["pay_amount"]),
                    "travelDate": record["travel_date"],
                    "createdAt": record["created_at"],
                    "productTitle": record.get("product_title"),
                    "itemQty": record.get("item_qty"),
                    "unitPrice": float(record["unit_price"]) if record.get("unit_price") else None,
                }
            )

        return ok(
            {
                "items": items,
                "pagination": {"page": page, "pageSize": page_size, "total": total},
            }
        )

    @app.get("/api/orders/<order_no>")
    @require_auth(roles={"user", "merchant", "admin"}, merchant_approved=True)
    def order_detail(order_no):
        conn = get_db()
        order_row = get_order_by_no(conn, order_no)
        ensure_order_access(g.current_user, order_row)
        return ok({"order": get_order_payload(conn, order_row)})

    @app.post("/api/orders/<order_no>/cancel")
    @require_auth(roles={"user", "admin"})
    def cancel_order(order_no):
        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "").strip() or "用户主动取消"
        user = g.current_user

        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(user, order_row)

            if order_row["status"] != "pending_payment":
                raise ApiError("当前状态不可取消", code=40021, status=400)

            conn.execute(
                """
                UPDATE orders
                SET status = 'cancelled', cancelled_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (reason, now_str(), order_row["id"]),
            )
            item_rows = conn.execute(
                """
                SELECT product_id, sku_date, qty
                FROM order_items
                WHERE order_id = ?
                """,
                (order_row["id"],),
            ).fetchall()
            for item in item_rows:
                conn.execute(
                    """
                    UPDATE product_sku_calendar
                    SET stock = stock + ?,
                        sold = CASE WHEN sold >= ? THEN sold - ? ELSE 0 END
                    WHERE product_id = ? AND date = ?
                    """,
                    (item["qty"], item["qty"], item["qty"], item["product_id"], item["sku_date"]),
                )

            insert_operation_log(
                conn,
                actor_id=user["id"],
                actor_role=user["role"],
                action="order.cancel",
                target_id=order_no,
                detail=json.dumps({"reason": reason}, ensure_ascii=False),
            )
            updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_row["id"],)).fetchone()

        return ok({"order": get_order_payload(get_db(), updated)})

    @app.post("/api/pay/mock-success")
    @require_auth(roles={"user", "admin"})
    def pay_mock_success():
        user = g.current_user
        data = request.get_json(silent=True) or {}
        order_no = (data.get("orderNo") or "").strip()
        idem_key = (request.headers.get("Idempotency-Key") or data.get("idemKey") or "").strip()
        if not order_no:
            raise ApiError("orderNo 不能为空", code=40031, status=400)

        scope = f"pay.mockSuccess:{user['id']}"
        if idem_key:
            cached_payload = get_idempotent_response(scope, idem_key)
            if cached_payload is not None:
                return ok(cached_payload, message="ok(idempotent)")

        payload = None
        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(user, order_row)
            if order_row["status"] in PAY_SUCCESS_STATES:
                payload = {
                    "orderNo": order_no,
                    "status": order_row["status"],
                    "statusLabel": ORDER_STATUS_LABELS.get(order_row["status"], order_row["status"]),
                    "paidAt": now_str(),
                    "idempotent": True,
                }
            else:
                if order_row["status"] != "pending_payment":
                    raise ApiError("订单状态不允许支付", code=40032, status=400)

                paid_at = now_str()
                conn.execute(
                    """
                    UPDATE orders
                    SET status = 'to_travel', pay_amount = amount, updated_at = ?
                    WHERE id = ?
                    """,
                    (paid_at, order_row["id"]),
                )
                payment_row = conn.execute(
                    """
                    SELECT id
                    FROM payments
                    WHERE order_id = ?
                    """,
                    (order_row["id"],),
                ).fetchone()
                if payment_row is None:
                    conn.execute(
                        """
                        INSERT INTO payments(order_id, pay_method, pay_status, mock_txn_no, paid_at, created_at)
                        VALUES (?, 'mock', 'success', ?, ?, ?)
                        """,
                        (order_row["id"], f"MOCK-{uuid.uuid4().hex[:16].upper()}", paid_at, paid_at),
                    )

                insert_operation_log(
                    conn,
                    actor_id=user["id"],
                    actor_role=user["role"],
                    action="pay.mockSuccess",
                    target_id=order_no,
                    detail=json.dumps({"paidAt": paid_at}, ensure_ascii=False),
                )

                payload = {
                    "orderNo": order_no,
                    "status": "to_travel",
                    "statusLabel": ORDER_STATUS_LABELS["to_travel"],
                    "paidAt": paid_at,
                    "idempotent": False,
                }

            if idem_key:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO idempotency_records(scope, idem_key, response, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (scope, idem_key, json.dumps(payload, ensure_ascii=False), now_str()),
                )

        return ok(payload)

    @app.get("/api/pay/query")
    @require_auth(roles={"user", "merchant", "admin"}, merchant_approved=True)
    def pay_query():
        order_no = (request.args.get("orderNo") or "").strip()
        if not order_no:
            raise ApiError("orderNo 不能为空", code=40033, status=400)

        conn = get_db()
        order_row = get_order_by_no(conn, order_no)
        ensure_order_access(g.current_user, order_row)
        payment_row = conn.execute(
            """
            SELECT pay_method, pay_status, mock_txn_no, paid_at
            FROM payments
            WHERE order_id = ?
            """,
            (order_row["id"],),
        ).fetchone()

        return ok(
            {
                "orderNo": order_no,
                "orderStatus": order_row["status"],
                "orderStatusLabel": ORDER_STATUS_LABELS.get(order_row["status"], order_row["status"]),
                "payInfo": dict(payment_row) if payment_row else None,
            }
        )

    @app.post("/api/orders/<order_no>/status")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def update_order_status(order_no):
        user = g.current_user
        data = request.get_json(silent=True) or {}
        target_status = (data.get("targetStatus") or "").strip()
        reason = (data.get("reason") or "").strip() or None
        if not target_status:
            raise ApiError("targetStatus 不能为空", code=40041, status=400)

        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(user, order_row)
            ensure_transition(order_row["status"], target_status)

            if target_status == "refunded":
                rollback_order_stock(conn, order_row["id"])

            conn.execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_status, now_str(), order_row["id"]),
            )
            insert_operation_log(
                conn,
                actor_id=user["id"],
                actor_role=user["role"],
                action="order.updateStatus",
                target_id=order_no,
                detail=json.dumps({"from": order_row["status"], "to": target_status, "reason": reason}, ensure_ascii=False),
            )
            updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_row["id"],)).fetchone()

        return ok({"order": get_order_payload(get_db(), updated)})

    @app.post("/api/orders/<order_no>/confirm")
    @require_auth(roles={"user", "admin"})
    def confirm_order_completed(order_no):
        user = g.current_user

        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(user, order_row)
            if order_row["status"] != "to_travel":
                raise ApiError("当前订单不是待出行状态，无法确认完成", code=40053, status=400)
            ensure_transition(order_row["status"], "completed")

            conn.execute(
                """
                UPDATE orders
                SET status = 'completed', updated_at = ?
                WHERE id = ?
                """,
                (now_str(), order_row["id"]),
            )
            insert_operation_log(
                conn,
                actor_id=user["id"],
                actor_role=user["role"],
                action="order.confirm",
                target_id=order_no,
                detail=json.dumps({"from": order_row["status"], "to": "completed"}, ensure_ascii=False),
            )
            updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_row["id"],)).fetchone()

        return ok({"order": get_order_payload(get_db(), updated)})

    @app.post("/api/refunds/apply")
    @require_auth(roles={"user", "admin"})
    def refund_apply():
        data = request.get_json(silent=True) or {}
        order_no = (data.get("orderNo") or "").strip()
        reason = (data.get("reason") or "").strip() or "行程调整"
        if not order_no:
            raise ApiError("orderNo 不能为空", code=40051, status=400)

        actor = g.current_user
        result = None
        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(actor, order_row)
            if order_row["status"] not in {"to_travel", "after_sale"}:
                raise ApiError("当前订单状态不可申请退款", code=40052, status=400)

            pending_refund = conn.execute(
                """
                SELECT refund_no, status
                FROM refunds
                WHERE order_id = ? AND status = 'pending'
                """,
                (order_row["id"],),
            ).fetchone()
            if pending_refund:
                result = {
                    "refundNo": pending_refund["refund_no"],
                    "status": pending_refund["status"],
                    "idempotent": True,
                }
            else:
                refund_no = generate_refund_no(conn)
                ts = now_str()
                conn.execute(
                    """
                    INSERT INTO refunds(order_id, refund_no, status, reason, audit_by, created_at, updated_at)
                    VALUES (?, ?, 'pending', ?, NULL, ?, ?)
                    """,
                    (order_row["id"], refund_no, reason, ts, ts),
                )
                conn.execute(
                    """
                    UPDATE orders
                    SET status = 'refunding', updated_at = ?
                    WHERE id = ?
                    """,
                    (ts, order_row["id"]),
                )
                insert_operation_log(
                    conn,
                    actor_id=actor["id"],
                    actor_role=actor["role"],
                    action="refund.apply",
                    target_id=refund_no,
                    detail=json.dumps({"orderNo": order_no, "reason": reason}, ensure_ascii=False),
                )
                result = {"refundNo": refund_no, "status": "pending", "idempotent": False}

        return ok(result)

    @app.post("/api/refunds/<refund_no>/audit")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def refund_audit(refund_no):
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        approved = bool(data.get("approved"))
        reason = (data.get("reason") or "").strip() or None
        with immediate_transaction() as conn:
            refund_row = conn.execute(
                """
                SELECT id, order_id, refund_no, status, reason, audit_by
                FROM refunds
                WHERE refund_no = ?
                """,
                (refund_no,),
            ).fetchone()
            if refund_row is None:
                raise ApiError("退款单不存在", code=40421, status=404)
            if refund_row["status"] != "pending":
                raise ApiError("退款单已处理", code=40061, status=400)

            order_row = conn.execute("SELECT * FROM orders WHERE id = ?", (refund_row["order_id"],)).fetchone()
            ensure_order_access(actor, order_row)

            now = now_str()
            if approved:
                rollback_order_stock(conn, order_row["id"])
                conn.execute(
                    "UPDATE refunds SET status = 'approved', audit_by = ?, updated_at = ? WHERE id = ?",
                    (actor["id"], now, refund_row["id"]),
                )
                conn.execute(
                    "UPDATE orders SET status = 'refunded', updated_at = ? WHERE id = ?",
                    (now, order_row["id"]),
                )
                outcome = "approved"
            else:
                conn.execute(
                    "UPDATE refunds SET status = 'rejected', audit_by = ?, updated_at = ? WHERE id = ?",
                    (actor["id"], now, refund_row["id"]),
                )
                conn.execute(
                    "UPDATE orders SET status = 'to_travel', updated_at = ? WHERE id = ?",
                    (now, order_row["id"]),
                )
                outcome = "rejected"

            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="refund.audit",
                target_id=refund_no,
                detail=json.dumps({"result": outcome, "reason": reason}, ensure_ascii=False),
            )

        return ok({"refundNo": refund_no, "result": outcome})

    @app.post("/api/reviews")
    @require_auth(roles={"user", "admin"})
    def review_create():
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        order_no = (data.get("orderNo") or "").strip()
        score = to_int(data.get("score"), default=5, minimum=1, maximum=5)
        content = (data.get("content") or "").strip() or None
        images = data.get("images") or []
        if not isinstance(images, list):
            raise ApiError("images must be an array", code=40075, status=400)
        if not order_no:
            raise ApiError("orderNo 不能为空", code=40071, status=400)

        with immediate_transaction() as conn:
            order_row = get_order_by_no(conn, order_no)
            ensure_order_access(actor, order_row)
            if order_row["status"] != "completed":
                raise ApiError("仅已完成订单允许评价", code=40072, status=400)
            existing = conn.execute(
                "SELECT id FROM reviews WHERE order_id = ?",
                (order_row["id"],),
            ).fetchone()
            if existing:
                raise ApiError("该订单已评价", code=40073, status=400)
            item_row = conn.execute(
                """
                SELECT product_id
                FROM order_items
                WHERE order_id = ?
                LIMIT 1
                """,
                (order_row["id"],),
            ).fetchone()
            ts = now_str()
            conn.execute(
                """
                INSERT INTO reviews(order_id, user_id, product_id, score, content, images, reply, audit_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, NULL, 'approved', ?, ?)
                """,
                (order_row["id"], actor["id"], item_row["product_id"], score, content, json.dumps(images, ensure_ascii=False), ts, ts),
            )
            review_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="review.create",
                target_id=order_no,
                detail=json.dumps({"score": score}, ensure_ascii=False),
            )

        return ok({"orderNo": order_no, "score": score, "reviewId": review_id})

    @app.post("/api/reviews/<int:review_id>/reply")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def review_reply(review_id):
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        reply = (data.get("reply") or "").strip()
        if not reply:
            raise ApiError("reply 不能为空", code=40074, status=400)

        with immediate_transaction() as conn:
            review_row = conn.execute(
                """
                SELECT r.id, r.order_id, r.reply, o.merchant_id
                FROM reviews r
                JOIN orders o ON o.id = r.order_id
                WHERE r.id = ?
                """,
                (review_id,),
            ).fetchone()
            if review_row is None:
                raise ApiError("评价不存在", code=40431, status=404)
            if actor["role"] == "merchant" and actor["merchant_id"] != review_row["merchant_id"]:
                raise ApiError("无权限回复该评价", code=40304, status=403)
            conn.execute(
                "UPDATE reviews SET reply = ?, updated_at = ? WHERE id = ?",
                (reply, now_str(), review_id),
            )
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="review.reply",
                target_id=str(review_id),
                detail=json.dumps({"reply": reply}, ensure_ascii=False),
            )

        return ok({"reviewId": review_id, "reply": reply})

    @app.get("/api/merchant/reviews")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_review_list():
        actor = g.current_user
        product_id = to_int(request.args.get("productId"), default=0, minimum=0, maximum=999999)
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=10, minimum=1, maximum=50)

        if actor["role"] == "merchant":
            merchant_id = actor["merchant_id"]
        else:
            merchant_id = to_int(request.args.get("merchantId"), default=0, minimum=0, maximum=999999)
            if merchant_id <= 0:
                raise ApiError("merchantId is required", code=40079, status=400)

        conditions = ["o.merchant_id = ?"]
        params = [merchant_id]
        if product_id > 0:
            conditions.append("r.product_id = ?")
            params.append(product_id)
        where_sql = " WHERE " + " AND ".join(conditions)

        conn = get_db()
        total_row = conn.execute(
            """
            SELECT COUNT(1) AS c
            FROM reviews r
            JOIN orders o ON o.id = r.order_id
            """
            + where_sql,
            tuple(params),
        ).fetchone()
        total = int(total_row["c"] or 0) if total_row else 0

        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT
                r.id,
                r.order_id,
                r.product_id,
                r.score,
                r.content,
                r.images,
                r.reply,
                r.audit_status,
                r.created_at,
                r.updated_at,
                o.order_no,
                p.title AS product_title,
                u.nickname AS user_nickname
            FROM reviews r
            JOIN orders o ON o.id = r.order_id
            LEFT JOIN products p ON p.id = r.product_id
            LEFT JOIN users u ON u.id = r.user_id
            """
            + where_sql
            + " ORDER BY r.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()

        items = []
        for row in rows:
            item = dict(row)
            item["content"] = sanitize_text(item.get("content"))
            item["reply"] = sanitize_text(item.get("reply"))
            item["images"] = parse_json_array(item.get("images"))
            items.append(item)

        return ok(
            {
                "items": items,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                },
            }
        )

    @app.get("/api/merchant/products")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_product_list():
        actor = g.current_user
        merchant_id = actor["merchant_id"] if actor["role"] == "merchant" else request.args.get("merchantId")
        if not merchant_id:
            raise ApiError("merchantId is required", code=40081, status=400)
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.merchant_id,
                p.title,
                p.category_id,
                p.status,
                p.base_price,
                p.cover,
                p.detail,
                p.depart_city,
                p.tags,
                p.created_at,
                p.updated_at,
                c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.merchant_id = ?
            ORDER BY p.id DESC
            """,
            (int(merchant_id),),
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["tags"] = (item["tags"] or "").split(",") if item.get("tags") else []
            item["base_price"] = float(item["base_price"])
            items.append(item)
        return ok(items)

    @app.post("/api/merchant/products")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_product_create():
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        merchant_id = actor["merchant_id"] if actor["role"] == "merchant" else data.get("merchantId")
        if not merchant_id:
            raise ApiError("merchantId 不能为空", code=40082, status=400)
        title = (data.get("title") or "").strip()
        base_price = float(data.get("basePrice") or 0)
        if not title or base_price <= 0:
            raise ApiError("title 与 basePrice 必填且有效", code=40083, status=400)
        category_id = data.get("categoryId")
        cover = (data.get("cover") or "").strip() or None
        detail = (data.get("detail") or "").strip() or None
        depart_city = (data.get("departCity") or "").strip() or None
        tags = data.get("tags") or []
        status = (data.get("status") or "on_sale").strip()
        if status not in {"on_sale", "off_sale"}:
            raise ApiError("status 仅支持 on_sale/off_sale", code=40084, status=400)

        calendar = data.get("calendar") or []
        if not isinstance(calendar, list):
            raise ApiError("calendar 必须为数组", code=40085, status=400)

        result = None
        with immediate_transaction() as conn:
            ts = now_str()
            conn.execute(
                """
                INSERT INTO products(
                    merchant_id, title, category_id, status, base_price, cover, detail, depart_city, tags, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(merchant_id),
                    title,
                    int(category_id) if category_id else None,
                    status,
                    base_price,
                    cover,
                    detail,
                    depart_city,
                    ",".join(tags) if isinstance(tags, list) else str(tags),
                    ts,
                    ts,
                ),
            )
            product_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            if calendar:
                for item in calendar:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO product_sku_calendar(product_id, date, price, stock, sold)
                        VALUES (?, ?, ?, ?, COALESCE((SELECT sold FROM product_sku_calendar WHERE product_id = ? AND date = ?), 0))
                        """,
                        (
                            product_id,
                            item["date"],
                            float(item.get("price") or base_price),
                            int(item.get("stock") or 0),
                            product_id,
                            item["date"],
                        ),
                    )
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="merchant.product.create",
                target_id=str(product_id),
                detail=json.dumps({"title": title}, ensure_ascii=False),
            )
            result = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

        return ok({"product": dict(result)})

    @app.put("/api/merchant/products/<int:product_id>")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_product_update(product_id):
        actor = g.current_user
        data = request.get_json(silent=True) or {}

        conn = get_db()
        product_row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product_row is None:
            raise ApiError("商品不存在", code=40441, status=404)
        if actor["role"] == "merchant" and actor["merchant_id"] != product_row["merchant_id"]:
            raise ApiError("无权限修改该商品", code=40305, status=403)

        allowed_fields = {
            "title": "title",
            "status": "status",
            "basePrice": "base_price",
            "cover": "cover",
            "detail": "detail",
            "departCity": "depart_city",
            "tags": "tags",
            "categoryId": "category_id",
        }
        updates = []
        params = []
        for key, db_key in allowed_fields.items():
            if key in data:
                value = data[key]
                if key == "tags" and isinstance(value, list):
                    value = ",".join(value)
                if key == "basePrice":
                    value = float(value)
                updates.append(f"{db_key} = ?")
                params.append(value)

        if not updates:
            raise ApiError("没有可更新字段", code=40086, status=400)

        params.append(now_str())
        params.append(product_id)
        conn.execute(
            f"UPDATE products SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return ok({"product": dict(updated)})

    @app.delete("/api/merchant/products/<int:product_id>")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_product_delete(product_id):
        actor = g.current_user

        with immediate_transaction() as conn:
            product_row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product_row is None:
                raise ApiError("product not found", code=40443, status=404)
            if actor["role"] == "merchant" and actor["merchant_id"] != product_row["merchant_id"]:
                raise ApiError("no permission to delete this product", code=40309, status=403)

            order_count_row = conn.execute(
                "SELECT COUNT(1) AS c FROM order_items WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            order_count = int(order_count_row["c"] or 0) if order_count_row else 0
            if order_count > 0:
                raise ApiError("product has related orders, cannot delete", code=40089, status=400)

            conn.execute("DELETE FROM product_sku_calendar WHERE product_id = ?", (product_id,))
            conn.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="merchant.product.delete",
                target_id=str(product_id),
                detail=json.dumps({"title": product_row["title"]}, ensure_ascii=False),
            )

        return ok({"productId": product_id, "deleted": True})

    @app.post("/api/merchant/products/<int:product_id>/calendar")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_product_calendar(product_id):
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        calendars = data.get("calendars") or []
        if not calendars or not isinstance(calendars, list):
            raise ApiError("calendars 不能为空且必须是数组", code=40087, status=400)

        with immediate_transaction() as conn:
            product_row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product_row is None:
                raise ApiError("商品不存在", code=40442, status=404)
            if actor["role"] == "merchant" and actor["merchant_id"] != product_row["merchant_id"]:
                raise ApiError("无权限修改该商品日历", code=40306, status=403)

            for item in calendars:
                travel_date = item.get("date")
                if not travel_date:
                    raise ApiError("calendar.date 不能为空", code=40088, status=400)
                price = float(item.get("price") or product_row["base_price"])
                stock = int(item.get("stock") or 0)
                sold = int(item.get("sold") or 0)
                conn.execute(
                    """
                    INSERT INTO product_sku_calendar(product_id, date, price, stock, sold)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(product_id, date) DO UPDATE SET
                        price = excluded.price,
                        stock = excluded.stock,
                        sold = excluded.sold
                    """,
                    (product_id, travel_date, price, stock, sold),
                )

            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="merchant.product.calendar",
                target_id=str(product_id),
                detail=json.dumps({"count": len(calendars)}, ensure_ascii=False),
            )

        return ok({"productId": product_id, "count": len(calendars)})

    @app.get("/api/merchant/dashboard")
    @require_auth(roles={"merchant", "admin"}, merchant_approved=True)
    def merchant_dashboard():
        actor = g.current_user
        if actor["role"] == "merchant":
            merchant_id = actor["merchant_id"]
        else:
            merchant_id = to_int(request.args.get("merchantId"), default=0, minimum=0, maximum=999999)
        conn = get_db()

        conditions = []
        params = []
        if merchant_id:
            conditions.append("merchant_id = ?")
            params.append(merchant_id)

        where_sql = " WHERE " + " AND ".join(conditions) if conditions else ""
        summary = conn.execute(
            """
            SELECT
                COUNT(1) AS total_orders,
                SUM(CASE WHEN status IN ('to_travel','completed','after_sale','refunding','refunded') THEN 1 ELSE 0 END) AS paid_orders,
                SUM(CASE WHEN status IN ('to_travel','completed','after_sale','refunding','refunded') THEN pay_amount ELSE 0 END) AS gmv,
                SUM(CASE WHEN status = 'refunded' THEN 1 ELSE 0 END) AS refunded_orders
            FROM orders
            """
            + where_sql,
            tuple(params),
        ).fetchone()
        by_status = conn.execute(
            """
            SELECT status, COUNT(1) AS count
            FROM orders
            """
            + where_sql
            + " GROUP BY status",
            tuple(params),
        ).fetchall()

        paid_orders = int(summary["paid_orders"] or 0)
        refunded_orders = int(summary["refunded_orders"] or 0)
        refund_rate = round(refunded_orders / paid_orders, 4) if paid_orders else 0

        return ok(
            {
                "totalOrders": int(summary["total_orders"] or 0),
                "paidOrders": paid_orders,
                "gmv": float(summary["gmv"] or 0),
                "refundedOrders": refunded_orders,
                "refundRate": refund_rate,
                "statusBreakdown": [dict(row) for row in by_status],
            }
        )

    @app.get("/api/admin/dashboard")
    @require_auth(roles={"admin"})
    def admin_dashboard():
        conn = get_db()
        row = conn.execute(
            """
            SELECT
                (SELECT COUNT(1) FROM users) AS total_users,
                (SELECT COUNT(1) FROM users WHERE role = 'user') AS normal_users,
                (SELECT COUNT(1) FROM users WHERE role = 'merchant') AS merchant_users,
                (SELECT COUNT(1) FROM users WHERE role = 'admin') AS admin_users,
                (SELECT COUNT(1) FROM merchants) AS total_merchants,
                (SELECT COUNT(1) FROM products) AS total_products,
                (SELECT COUNT(1) FROM orders) AS total_orders,
                (SELECT COUNT(1) FROM orders WHERE status = 'pending_payment') AS pending_orders,
                (SELECT COUNT(1) FROM refunds WHERE status = 'pending') AS pending_refunds,
                (SELECT COALESCE(SUM(pay_amount), 0) FROM orders WHERE status IN ('to_travel', 'completed', 'after_sale', 'refunding', 'refunded')) AS total_gmv
            """
        ).fetchone()
        return ok(
            {
                "totalUsers": int(row["total_users"] or 0),
                "normalUsers": int(row["normal_users"] or 0),
                "merchantUsers": int(row["merchant_users"] or 0),
                "adminUsers": int(row["admin_users"] or 0),
                "totalMerchants": int(row["total_merchants"] or 0),
                "totalProducts": int(row["total_products"] or 0),
                "totalOrders": int(row["total_orders"] or 0),
                "pendingOrders": int(row["pending_orders"] or 0),
                "pendingRefunds": int(row["pending_refunds"] or 0),
                "totalGmv": float(row["total_gmv"] or 0),
            }
        )

    @app.get("/api/admin/users")
    @require_auth(roles={"admin"})
    def admin_user_list():
        keyword = (request.args.get("keyword") or "").strip()
        role = (request.args.get("role") or "").strip()
        status = (request.args.get("status") or "").strip()
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=20, minimum=1, maximum=100)

        conditions = ["1=1"]
        params = []
        if keyword:
            conditions.append("(u.username LIKE ? OR u.nickname LIKE ? OR u.phone LIKE ?)")
            like_value = f"%{keyword}%"
            params.extend([like_value, like_value, like_value])
        if role:
            conditions.append("u.role = ?")
            params.append(role)
        if status:
            conditions.append("u.status = ?")
            params.append(status)
        where_sql = " WHERE " + " AND ".join(conditions)

        conn = get_db()
        total = conn.execute(
            "SELECT COUNT(1) AS c FROM users u" + where_sql,
            tuple(params),
        ).fetchone()["c"]

        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT
                u.id,
                u.openid,
                u.username,
                u.nickname,
                u.phone,
                u.role,
                u.status,
                u.created_at,
                m.id AS merchant_id,
                m.name AS merchant_name,
                m.audit_status AS merchant_audit_status
            FROM users u
            LEFT JOIN merchants m ON m.owner_user_id = u.id
            """
            + where_sql
            + " ORDER BY u.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()

        return ok(
            {
                "items": [dict(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "total": total},
            }
        )

    @app.post("/api/admin/users")
    @require_auth(roles={"admin"})
    def admin_user_create():
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        nickname = (data.get("nickname") or "").strip() or username
        phone = (data.get("phone") or "").strip() or None
        role = (data.get("role") or "user").strip()
        status = (data.get("status") or "active").strip()
        merchant_name = (data.get("merchantName") or "").strip() or f"{nickname}的店铺"

        if not username:
            raise ApiError("username 不能为空", code=40096, status=400)
        if len(password) < 6:
            raise ApiError("password 长度至少 6 位", code=40097, status=400)
        if role not in {"user", "merchant", "admin"}:
            raise ApiError("role 仅支持 user/merchant/admin", code=40098, status=400)
        if status not in {"active", "disabled"}:
            raise ApiError("status 仅支持 active/disabled", code=40099, status=400)

        with immediate_transaction() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users(openid, username, password_hash, nickname, phone, role, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"local-{uuid.uuid4().hex[:16]}",
                        username,
                        hash_password(password),
                        nickname,
                        phone,
                        role,
                        status,
                        now_str(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ApiError("用户名已存在", code=40121, status=400) from exc

            user_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            if role == "merchant":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO merchants(name, license_no, owner_user_id, audit_status, rating, created_at)
                    VALUES (?, ?, ?, 'pending', 5, ?)
                    """,
                    (merchant_name, f"LIC-{uuid.uuid4().hex[:8].upper()}", user_id, now_str()),
                )

            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="admin.user.create",
                target_id=str(user_id),
                detail=json.dumps({"username": username, "role": role}, ensure_ascii=False),
            )
            user_row = conn.execute(
                """
                SELECT id, openid, username, nickname, phone, role, status, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

        return ok({"user": dict(user_row)})

    @app.put("/api/admin/users/<int:user_id>")
    @require_auth(roles={"admin"})
    def admin_user_update(user_id):
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        with immediate_transaction() as conn:
            user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_row is None:
                raise ApiError("用户不存在", code=40461, status=404)

            next_role = (data.get("role") or user_row["role"]).strip()
            next_status = (data.get("status") or user_row["status"]).strip()
            if next_role not in {"user", "merchant", "admin"}:
                raise ApiError("role 仅支持 user/merchant/admin", code=40122, status=400)
            if next_status not in {"active", "disabled"}:
                raise ApiError("status 仅支持 active/disabled", code=40123, status=400)
            if actor["id"] == user_id and next_status != "active":
                raise ApiError("不能禁用当前登录管理员", code=40124, status=400)
            if actor["id"] == user_id and next_role != "admin":
                raise ApiError("不能修改当前登录管理员角色", code=40125, status=400)

            updates = []
            params = []
            if "username" in data:
                username = (data.get("username") or "").strip()
                if not username:
                    raise ApiError("username 不能为空", code=40126, status=400)
                updates.append("username = ?")
                params.append(username)
            if "nickname" in data:
                updates.append("nickname = ?")
                params.append((data.get("nickname") or "").strip())
            if "phone" in data:
                updates.append("phone = ?")
                params.append((data.get("phone") or "").strip() or None)
            if "role" in data:
                updates.append("role = ?")
                params.append(next_role)
            if "status" in data:
                updates.append("status = ?")
                params.append(next_status)
            if "password" in data:
                password = (data.get("password") or "").strip()
                if password and len(password) < 6:
                    raise ApiError("password 长度至少 6 位", code=40127, status=400)
                if password:
                    updates.append("password_hash = ?")
                    params.append(hash_password(password))

            if updates:
                params.append(user_id)
                try:
                    conn.execute(
                        f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                        tuple(params),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ApiError("用户名已存在", code=40121, status=400) from exc

            if next_role == "merchant":
                merchant_name = (data.get("merchantName") or "").strip() or f"{(data.get('nickname') or user_row['nickname'])}的店铺"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO merchants(name, license_no, owner_user_id, audit_status, rating, created_at)
                    VALUES (?, ?, ?, 'pending', 5, ?)
                    """,
                    (merchant_name, f"LIC-{uuid.uuid4().hex[:8].upper()}", user_id, now_str()),
                )
            if next_role != "merchant" or next_status == "disabled":
                conn.execute(
                    """
                    UPDATE merchants
                    SET audit_status = 'disabled'
                    WHERE owner_user_id = ?
                    """,
                    (user_id,),
                )

            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="admin.user.update",
                target_id=str(user_id),
                detail=json.dumps({"role": next_role, "status": next_status}, ensure_ascii=False),
            )
            updated = conn.execute(
                """
                SELECT id, openid, username, nickname, phone, role, status, created_at
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

        return ok({"user": dict(updated)})

    @app.delete("/api/admin/users/<int:user_id>")
    @require_auth(roles={"admin"})
    def admin_user_disable(user_id):
        actor = g.current_user
        if actor["id"] == user_id:
            raise ApiError("不能禁用当前登录管理员", code=40124, status=400)

        with immediate_transaction() as conn:
            user_row = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_row is None:
                raise ApiError("用户不存在", code=40461, status=404)
            conn.execute("UPDATE users SET status = 'disabled' WHERE id = ?", (user_id,))
            if user_row["role"] == "merchant":
                conn.execute("UPDATE merchants SET audit_status = 'disabled' WHERE owner_user_id = ?", (user_id,))
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="admin.user.disable",
                target_id=str(user_id),
                detail=None,
            )

        return ok({"userId": user_id, "status": "disabled"})

    @app.get("/api/admin/orders")
    @require_auth(roles={"admin"})
    def admin_order_list():
        status = (request.args.get("status") or "").strip()
        keyword = (request.args.get("keyword") or "").strip()
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=20, minimum=1, maximum=100)
        conditions = ["1=1"]
        params = []
        if status:
            conditions.append("o.status = ?")
            params.append(status)
        if keyword:
            conditions.append("(o.order_no LIKE ? OR u.username LIKE ? OR oi.title LIKE ?)")
            like_value = f"%{keyword}%"
            params.extend([like_value, like_value, like_value])
        where_sql = " WHERE " + " AND ".join(conditions)
        conn = get_db()
        total = conn.execute(
            """
            SELECT COUNT(1) AS c
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            """
            + where_sql,
            tuple(params),
        ).fetchone()["c"]
        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT
                o.order_no,
                o.status,
                o.amount,
                o.pay_amount,
                o.travel_date,
                o.created_at,
                u.username,
                u.nickname,
                oi.title AS product_title
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            """
            + where_sql
            + " ORDER BY o.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()
        return ok(
            {
                "items": [dict(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "total": total},
            }
        )

    @app.get("/api/admin/products")
    @require_auth(roles={"admin"})
    def admin_product_list():
        keyword = (request.args.get("keyword") or "").strip()
        status = (request.args.get("status") or "").strip()
        page = to_int(request.args.get("page"), default=1, minimum=1, maximum=9999)
        page_size = to_int(request.args.get("pageSize"), default=20, minimum=1, maximum=100)
        conditions = ["1=1"]
        params = []
        if keyword:
            conditions.append("p.title LIKE ?")
            params.append(f"%{keyword}%")
        if status:
            conditions.append("p.status = ?")
            params.append(status)
        where_sql = " WHERE " + " AND ".join(conditions)
        conn = get_db()
        total = conn.execute("SELECT COUNT(1) AS c FROM products p" + where_sql, tuple(params)).fetchone()["c"]
        query_params = list(params)
        query_params.extend([page_size, (page - 1) * page_size])
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.status, p.base_price, p.depart_city, p.updated_at, m.name AS merchant_name
            FROM products p
            LEFT JOIN merchants m ON m.id = p.merchant_id
            """
            + where_sql
            + " ORDER BY p.id DESC LIMIT ? OFFSET ?",
            tuple(query_params),
        ).fetchall()
        return ok(
            {
                "items": [dict(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "total": total},
            }
        )

    @app.put("/api/admin/products/<int:product_id>")
    @require_auth(roles={"admin"})
    def admin_product_update(product_id):
        data = request.get_json(silent=True) or {}
        allowed_fields = {
            "title": "title",
            "status": "status",
            "basePrice": "base_price",
            "cover": "cover",
            "detail": "detail",
            "departCity": "depart_city",
            "tags": "tags",
            "categoryId": "category_id",
            "merchantId": "merchant_id",
        }
        updates = []
        params = []
        for key, db_key in allowed_fields.items():
            if key in data:
                value = data[key]
                if key == "tags" and isinstance(value, list):
                    value = ",".join(value)
                if key == "basePrice":
                    value = float(value)
                updates.append(f"{db_key} = ?")
                params.append(value)
        if not updates:
            raise ApiError("没有可更新字段", code=40131, status=400)
        params.append(now_str())
        params.append(product_id)
        conn = get_db()
        conn.execute(
            f"UPDATE products SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise ApiError("商品不存在", code=40471, status=404)
        return ok({"product": dict(row)})

    @app.delete("/api/admin/products/<int:product_id>")
    @require_auth(roles={"admin"})
    def admin_product_disable(product_id):
        conn = get_db()
        row = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise ApiError("商品不存在", code=40471, status=404)
        conn.execute("UPDATE products SET status = 'off_sale', updated_at = ? WHERE id = ?", (now_str(), product_id))
        conn.commit()
        return ok({"productId": product_id, "status": "off_sale"})

    @app.get("/api/admin/merchants")
    @require_auth(roles={"admin"})
    def admin_merchant_list():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.name,
                m.license_no,
                m.owner_user_id,
                m.audit_status,
                m.rating,
                m.created_at,
                u.nickname AS owner_nickname
            FROM merchants m
            JOIN users u ON u.id = m.owner_user_id
            ORDER BY m.id DESC
            """
        ).fetchall()
        return ok([dict(row) for row in rows])

    @app.post("/api/admin/merchants/<int:merchant_id>/audit")
    @require_auth(roles={"admin"})
    def admin_audit_merchant(merchant_id):
        actor = g.current_user
        data = request.get_json(silent=True) or {}
        audit_status = (data.get("auditStatus") or "").strip()
        if audit_status not in {"approved", "rejected", "disabled"}:
            raise ApiError("auditStatus 仅支持 approved/rejected/disabled", code=40091, status=400)

        with immediate_transaction() as conn:
            merchant_row = conn.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,)).fetchone()
            if merchant_row is None:
                raise ApiError("商家不存在", code=40451, status=404)

            conn.execute(
                """
                UPDATE merchants
                SET audit_status = ?
                WHERE id = ?
                """,
                (audit_status, merchant_id),
            )
            if audit_status == "approved":
                conn.execute(
                    "UPDATE users SET role = 'merchant' WHERE id = ?",
                    (merchant_row["owner_user_id"],),
                )
            insert_operation_log(
                conn,
                actor_id=actor["id"],
                actor_role=actor["role"],
                action="admin.auditMerchant",
                target_id=str(merchant_id),
                detail=json.dumps({"auditStatus": audit_status}, ensure_ascii=False),
            )
            updated = conn.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,)).fetchone()

        return ok({"merchant": dict(updated)})

    @app.get("/api/admin/categories")
    @require_auth(roles={"admin"})
    def admin_category_list():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT id, name, status, created_at
            FROM categories
            ORDER BY id DESC
            """
        ).fetchall()
        return ok([dict(row) for row in rows])

    @app.post("/api/admin/categories")
    @require_auth(roles={"admin"})
    def admin_upsert_category():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        status = (data.get("status") or "active").strip()
        if not name:
            raise ApiError("name 不能为空", code=40092, status=400)
        if status not in {"active", "inactive"}:
            raise ApiError("status 仅支持 active/inactive", code=40093, status=400)

        conn = get_db()
        conn.execute(
            """
            INSERT INTO categories(name, status, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET status = excluded.status
            """,
            (name, status, now_str()),
        )
        conn.commit()
        return ok({"name": name, "status": status})

    @app.delete("/api/admin/categories/<int:category_id>")
    @require_auth(roles={"admin"})
    def admin_delete_category(category_id):
        conn = get_db()
        category_row = conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category_row is None:
            raise ApiError("类目不存在", code=40481, status=404)
        product_count = conn.execute(
            "SELECT COUNT(1) AS c FROM products WHERE category_id = ?",
            (category_id,),
        ).fetchone()["c"]
        if product_count > 0:
            raise ApiError("该类目下存在商品，不能删除", code=40141, status=400)
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        return ok({"categoryId": category_id})

    @app.get("/api/admin/banners")
    @require_auth(roles={"admin"})
    def admin_banner_list():
        conn = get_db()
        rows = conn.execute(
            """
            SELECT id, title, image, link, sort, enabled, updated_at
            FROM banners
            ORDER BY sort ASC, id DESC
            """
        ).fetchall()
        return ok([dict(row) for row in rows])

    @app.post("/api/admin/banners")
    @require_auth(roles={"admin"})
    def admin_config_banner():
        data = request.get_json(silent=True) or {}
        banners = data.get("banners") or []
        if not isinstance(banners, list):
            raise ApiError("banners 必须是数组", code=40094, status=400)

        with immediate_transaction() as conn:
            conn.execute("DELETE FROM banners")
            for index, banner in enumerate(banners):
                title = (banner.get("title") or "").strip() or f"运营位{index + 1}"
                image = (banner.get("image") or "").strip()
                link = (banner.get("link") or "").strip() or None
                sort = int(banner.get("sort") or (index + 1))
                enabled = 1 if banner.get("enabled", True) else 0
                if not image:
                    raise ApiError("banner.image 不能为空", code=40095, status=400)
                conn.execute(
                    """
                    INSERT INTO banners(title, image, link, sort, enabled, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title, image, link, sort, enabled, now_str()),
                )
            insert_operation_log(
                conn,
                actor_id=g.current_user["id"],
                actor_role=g.current_user["role"],
                action="admin.configBanner",
                target_id="banners",
                detail=json.dumps({"count": len(banners)}, ensure_ascii=False),
            )

        return ok({"count": len(banners)})

    return app


def ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data, "traceId": g.get("trace_id")})


def to_int(value, default=0, minimum=None, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None and result < minimum:
        result = minimum
    if maximum is not None and result > maximum:
        result = maximum
    return result


def parse_json_array(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if not isinstance(value, str):
        return []
    stripped = value.strip()
    if not stripped:
        return []
    try:
        parsed = json.loads(stripped)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def sanitize_text(value):
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if all(ch in {"?", "？"} for ch in stripped):
        return ""
    return value


def get_order_by_no(conn, order_no):
    order_row = conn.execute(
        "SELECT * FROM orders WHERE order_no = ?",
        (order_no,),
    ).fetchone()
    if order_row is None:
        raise ApiError("订单不存在", code=40411, status=404)
    return order_row


def ensure_order_access(user, order_row):
    if user["role"] == "admin":
        return
    if user["role"] == "merchant":
        if user["merchant_id"] != order_row["merchant_id"]:
            raise ApiError("无权限操作该订单", code=40307, status=403)
        return
    if user["id"] != order_row["user_id"]:
        raise ApiError("无权限操作该订单", code=40308, status=403)


def get_order_payload(conn, order_row):
    item_rows = conn.execute(
        """
        SELECT product_id, sku_date, unit_price, qty, title
        FROM order_items
        WHERE order_id = ?
        ORDER BY id ASC
        """,
        (order_row["id"],),
    ).fetchall()
    items = []
    for row in item_rows:
        item = dict(row)
        item["unit_price"] = float(item["unit_price"])
        items.append(item)

    payment_row = conn.execute(
        """
        SELECT pay_method, pay_status, mock_txn_no, paid_at
        FROM payments
        WHERE order_id = ?
        """,
        (order_row["id"],),
    ).fetchone()

    review_row = conn.execute(
        """
        SELECT id, score, content, images, reply, created_at, updated_at
        FROM reviews
        WHERE order_id = ?
        LIMIT 1
        """,
        (order_row["id"],),
    ).fetchone()
    review = None
    if review_row is not None:
        review = dict(review_row)
        review["content"] = sanitize_text(review.get("content"))
        review["reply"] = sanitize_text(review.get("reply"))
        review["images"] = parse_json_array(review.get("images"))

    return {
        "orderNo": order_row["order_no"],
        "clientReqNo": order_row["client_req_no"],
        "userId": order_row["user_id"],
        "merchantId": order_row["merchant_id"],
        "amount": float(order_row["amount"]),
        "payAmount": float(order_row["pay_amount"]),
        "status": order_row["status"],
        "statusLabel": ORDER_STATUS_LABELS.get(order_row["status"], order_row["status"]),
        "contactName": order_row["contact_name"],
        "contactPhone": order_row["contact_phone"],
        "travelDate": order_row["travel_date"],
        "qty": order_row["qty"],
        "remark": order_row["remark"],
        "cancelledReason": order_row["cancelled_reason"],
        "createdAt": order_row["created_at"],
        "updatedAt": order_row["updated_at"],
        "items": items,
        "payInfo": dict(payment_row) if payment_row else None,
        "review": review,
    }


def generate_order_no(conn):
    while True:
        candidate = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        exists = conn.execute("SELECT 1 FROM orders WHERE order_no = ?", (candidate,)).fetchone()
        if exists is None:
            return candidate


def generate_refund_no(conn):
    while True:
        candidate = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        exists = conn.execute("SELECT 1 FROM refunds WHERE refund_no = ?", (candidate,)).fetchone()
        if exists is None:
            return candidate


def insert_operation_log(conn, actor_id, actor_role, action, target_id, detail=None):
    conn.execute(
        """
        INSERT INTO operation_logs(actor_id, actor_role, action, target_id, trace_id, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (actor_id, actor_role, action, target_id, g.get("trace_id"), detail, now_str()),
    )


def get_idempotent_response(scope, idem_key):
    conn = get_db()
    row = conn.execute(
        """
        SELECT response
        FROM idempotency_records
        WHERE scope = ? AND idem_key = ?
        """,
        (scope, idem_key),
    ).fetchone()
    if row is None:
        return None
    return json.loads(row["response"])


def rollback_order_stock(conn, order_id):
    items = conn.execute(
        """
        SELECT product_id, sku_date, qty
        FROM order_items
        WHERE order_id = ?
        """,
        (order_id,),
    ).fetchall()
    for item in items:
        conn.execute(
            """
            UPDATE product_sku_calendar
            SET stock = stock + ?,
                sold = CASE WHEN sold >= ? THEN sold - ? ELSE 0 END
            WHERE product_id = ? AND date = ?
            """,
            (item["qty"], item["qty"], item["qty"], item["product_id"], item["sku_date"]),
        )


@contextmanager
def immediate_transaction():
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
