from errors import ApiError

ORDER_STATUS_LABELS = {
    "pending_payment": "待支付",
    "cancelled": "已取消",
    "to_travel": "待出行",
    "completed": "已完成",
    "after_sale": "售后中",
    "refunding": "退款中",
    "refunded": "已退款",
}

PAY_SUCCESS_STATES = {"to_travel", "completed", "after_sale", "refunding", "refunded"}

ORDER_STATE_TRANSITIONS = {
    "pending_payment": {"cancelled", "to_travel"},
    "to_travel": {"completed", "after_sale", "refunding"},
    "after_sale": {"completed", "refunded"},
    "refunding": {"refunded", "to_travel"},
    "completed": set(),
    "cancelled": set(),
    "refunded": set(),
}


def ensure_transition(current_status, target_status):
    allowed = ORDER_STATE_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise ApiError(
            f"非法状态流转: {current_status} -> {target_status}",
            code=40012,
            status=400,
        )
