from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, URLSafeSerializer

from db import get_db
from errors import ApiError


def _serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="travel-miniapp-auth")


def create_token(payload):
    return _serializer().dumps(payload)


def parse_token(token):
    try:
        return _serializer().loads(token)
    except BadSignature as exc:
        raise ApiError("登录态失效，请重新登录", code=40102, status=401) from exc


def _extract_token():
    auth_value = request.headers.get("Authorization", "")
    if auth_value.startswith("Bearer "):
        return auth_value.replace("Bearer ", "", 1).strip()
    return ""


def load_current_user(optional=False):
    token = _extract_token()
    if not token:
        if optional:
            g.current_user = None
            return None
        raise ApiError("未登录", code=40101, status=401)

    payload = parse_token(token)
    user_id = payload.get("uid")
    if not user_id:
        raise ApiError("无效登录态", code=40103, status=401)

    conn = get_db()
    user_row = conn.execute(
        """
        SELECT id, openid, username, nickname, phone, role, status, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if user_row is None or user_row["status"] != "active":
        raise ApiError("账号不可用", code=40104, status=401)

    user = dict(user_row)
    if user["role"] == "merchant":
        merchant_row = conn.execute(
            """
            SELECT id, name, audit_status
            FROM merchants
            WHERE owner_user_id = ?
            """,
            (user["id"],),
        ).fetchone()
        if merchant_row is None:
            raise ApiError("商家信息不存在", code=40302, status=403)
        user["merchant_id"] = merchant_row["id"]
        user["merchant_name"] = merchant_row["name"]
        user["merchant_audit_status"] = merchant_row["audit_status"]

    g.current_user = user
    return user


def require_auth(roles=None, merchant_approved=False):
    role_set = set(roles) if roles else None

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = load_current_user(optional=False)
            if role_set and user["role"] not in role_set:
                raise ApiError("无权限访问该接口", code=40301, status=403)
            if merchant_approved and user["role"] == "merchant":
                if user.get("merchant_audit_status") != "approved":
                    raise ApiError("商家审核未通过，暂不可操作", code=40303, status=403)
            return func(*args, **kwargs)

        return wrapper

    return decorator
