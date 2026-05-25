from typing import Tuple


def build_room_key(role_a: str, id_a: int, role_b: str, id_b: int) -> str:
    """Return deterministic 1:1 room key like conv_role:id__role:id.

    This helper is kept for backwards compatibility with the /chat2
    conversation model, which persists a generic conversation key.
    New room-based chat flows should prefer ``build_human_room_name``
    to construct explicit Socket.IO room names such as
    ``room-user-12-seller-5``.
    """
    a = f"{role_a}:{id_a}"
    b = f"{role_b}:{id_b}"
    p1, p2 = sorted([a, b])
    return f"conv_{p1}__{p2}"


def normalize_pair(
    role_a: str, id_a: int, role_b: str, id_b: int
) -> Tuple[str, int, str, int, str]:
    """Return ordered pair (r1,id1,r2,id2,room_key).

    The ``room_key`` here is the stable conversation key used by the
    chat2 controller layer. For concrete Socket.IO rooms that follow
    the stricter naming convention (room-user-*-seller-* etc.), call
    ``build_human_room_name`` instead.
    """
    room_key = build_room_key(role_a, id_a, role_b, id_b)
    a = f"{role_a}:{id_a}"
    b = f"{role_b}:{id_b}"
    if a <= b:
        return role_a, id_a, role_b, id_b, room_key
    return role_b, id_b, role_a, id_a, room_key


def build_human_room_name(me_role: str, me_id: int, peer_role: str, peer_id: int) -> str:
    """Return a canonical Socket.IO room name like ``room-user-1-seller-5``.

    The rules mirror the product/order chat requirements:

    - user <-> seller   -> room-user-{userID}-seller-{sellerID}
    - user <-> rider    -> room-user-{userID}-rider-{riderID}
    - rider <-> seller  -> room-rider-{riderID}-seller-{sellerID}
    - admin <-> account -> room-admin-{adminID}-account-{accountID}

    Role order in the string is fixed (user before seller, user before
    rider, rider before seller, admin first) so that both parties join
    the same room regardless of who initiated the chat.
    """
    role_a = (me_role or "").lower()
    role_b = (peer_role or "").lower()

    try:
        id_a = int(me_id)
    except Exception:
        id_a = int(str(me_id)) if str(me_id).isdigit() else me_id
    try:
        id_b = int(peer_id)
    except Exception:
        id_b = int(str(peer_id)) if str(peer_id).isdigit() else peer_id

    pair = {role_a, role_b}

    # Admin can chat with any account type; always put admin first.
    if "admin" in pair:
        if role_a == "admin":
            admin_id, account_id = id_a, id_b
        else:
            admin_id, account_id = id_b, id_a
        return f"room-admin-{admin_id}-account-{account_id}"

    # Rider specific rules
    if pair == {"rider", "seller"}:
        rider_id = id_a if role_a == "rider" else id_b
        seller_id = id_b if role_a == "rider" else id_a
        return f"room-rider-{rider_id}-seller-{seller_id}"

    if pair == {"rider", "user"}:
        rider_id = id_a if role_a == "rider" else id_b
        user_id = id_b if role_a == "rider" else id_a
        return f"room-rider-{rider_id}-user-{user_id}"

    # User/seller pair (includes generic buyer/seller chat not bound to rider)
    if pair == {"user", "seller"}:
        user_id = id_a if role_a == "user" else id_b
        seller_id = id_b if role_a == "user" else id_a
        return f"room-user-{user_id}-seller-{seller_id}"

    # Fallback: generic deterministic ordering to avoid mismatched rooms
    # even for unsupported role combinations.
    ordered = sorted([
        (role_a, id_a),
        (role_b, id_b),
    ], key=lambda x: (x[0], str(x[1])))
    (r1, i1), (r2, i2) = ordered
    return f"room-{r1}-{i1}-{r2}-{i2}"
