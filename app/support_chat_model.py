from datetime import datetime
from typing import Dict, List, Tuple

from app import authentication

CUSTOMER_SERVICE_TYPE = 'customer_service'
ADMIN_FALLBACK_ID = 1
ADMIN_NOTIFICATIONS_ROOM = 'admin_customer_service_hub'


def get_db():
    return authentication.get_db_connection()


def _coerce_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_admin_id(value) -> int:
    admin_id = _coerce_int(value)
    return admin_id or ADMIN_FALLBACK_ID


def build_customer_room(role: str, entity_id: int) -> str:
    return f"room_customer_{role}_{entity_id}"


def _map_customer_ids(sender_role: str, sender_id: int, receiver_role: str, receiver_id: int, admin_id: int) -> Dict[str, int]:
    ids = {'userID': 0, 'sellerID': 0, 'riderID': 0, 'adminID': _normalize_admin_id(admin_id)}

    for role, identifier in ((sender_role, sender_id), (receiver_role, receiver_id)):
        numeric_id = _coerce_int(identifier)
        if role == 'user':
            ids['userID'] = numeric_id
        elif role == 'seller':
            ids['sellerID'] = numeric_id
        elif role == 'rider':
            ids['riderID'] = numeric_id
        elif role == 'admin':
            ids['adminID'] = _normalize_admin_id(numeric_id)

    return ids


def _customer_filters(target_role: str, target_id: int, admin_id: int) -> Tuple[List[str], List[int]]:
    filters = ['chat_type = %s', 'adminID = %s']
    params = [CUSTOMER_SERVICE_TYPE, _normalize_admin_id(admin_id)]

    role = (target_role or '').lower()
    target = _coerce_int(target_id)

    if role == 'user':
        filters.append('userID = %s')
        params.append(target)
        filters.extend(['(sellerID = 0 OR sellerID IS NULL)', '(riderID = 0 OR riderID IS NULL)'])
    elif role == 'seller':
        filters.append('sellerID = %s')
        params.append(target)
        filters.extend(['(userID = 0 OR userID IS NULL)', '(riderID = 0 OR riderID IS NULL)'])
    elif role == 'rider':
        filters.append('riderID = %s')
        params.append(target)
        filters.extend(['(userID = 0 OR userID IS NULL)', '(sellerID = 0 OR sellerID IS NULL)'])

    return filters, params


def save_support_message(room_hint, sender_role, sender_id, receiver_role, receiver_id, message, admin_id=None):
    room_id = room_hint if isinstance(room_hint, str) and room_hint.startswith('room_customer_') else None
    admin_identifier = admin_id
    if admin_identifier is None:
        if sender_role == 'admin':
            admin_identifier = sender_id
        elif receiver_role == 'admin':
            admin_identifier = receiver_id
        else:
            admin_identifier = ADMIN_FALLBACK_ID

    ids = _map_customer_ids(sender_role, sender_id, receiver_role, receiver_id, admin_identifier)

    participant_role = receiver_role if sender_role == 'admin' else sender_role
    participant_id = ids['userID'] or ids['sellerID'] or ids['riderID']
    if not room_id and participant_role and participant_id:
        room_id = build_customer_room(participant_role, participant_id)

    conn = get_db()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        query = """
            INSERT INTO chats (
                userID, sellerID, riderID, adminID,
                messages, messages_image, sender_role,
                chat_type, is_read, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
        """
        cur.execute(query, (
            ids['userID'], ids['sellerID'], ids['riderID'], ids['adminID'],
            (message or '')[:10000], '', sender_role, CUSTOMER_SERVICE_TYPE
        ))
        message_id = cur.lastrowid
        conn.commit()

        cur.execute("SELECT created_at FROM chats WHERE chatID = %s", (message_id,))
        row = cur.fetchone()
        created_at = row[0] if row else datetime.utcnow()

        return {
            'id': message_id,
            'room_id': room_id,
            'sender_role': sender_role,
            'sender_id': _coerce_int(sender_id),
            'receiver_role': receiver_role,
            'receiver_id': _coerce_int(receiver_id),
            'message': message,
            'chat_type': CUSTOMER_SERVICE_TYPE,
            'created_at': created_at.isoformat(),
            'is_read': False
        }
    finally:
        conn.close()


def get_support_history(target_role: str, target_id: int, admin_id: int = ADMIN_FALLBACK_ID, limit: int = 50):
    conn = get_db()
    if not conn:
        return []

    filters, params = _customer_filters(target_role, target_id, admin_id)
    where_clause = ' AND '.join(filters)

    try:
        cur = conn.cursor(dictionary=True)
        query = f"""
            SELECT chatID AS id, messages AS message, sender_role, created_at
            FROM chats
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
        """
        cur.execute(query, tuple(params + [limit]))
        rows = cur.fetchall()
        rows.reverse()

        for row in rows:
            if row.get('created_at'):
                row['created_at'] = row['created_at'].isoformat()
        return rows
    finally:
        conn.close()


def get_admin_conversations(admin_id: int = ADMIN_FALLBACK_ID):
    conn = get_db()
    if not conn:
        return []

    admin_id = _normalize_admin_id(admin_id)

    try:
        cur = conn.cursor(dictionary=True)
        query = """
            SELECT 
                COALESCE(NULLIF(userID, 0), NULLIF(sellerID, 0), NULLIF(riderID, 0)) AS participant_id,
                CASE
                    WHEN userID > 0 THEN 'user'
                    WHEN sellerID > 0 THEN 'seller'
                    WHEN riderID > 0 THEN 'rider'
                    ELSE 'unknown'
                END AS participant_role,
                MAX(created_at) AS last_message_time,
                SUM(CASE WHEN sender_role != 'admin' AND is_read = 0 THEN 1 ELSE 0 END) AS unread_count
            FROM chats
            WHERE chat_type = %s AND adminID = %s
            GROUP BY participant_role, participant_id
            HAVING participant_role != 'unknown' AND participant_id IS NOT NULL
            ORDER BY last_message_time DESC
        """
        cur.execute(query, (CUSTOMER_SERVICE_TYPE, admin_id))
        rows = cur.fetchall()

        conversations = []
        for row in rows:
            participant_role = row['participant_role']
            participant_id = _coerce_int(row['participant_id'])
            if not participant_role or not participant_id:
                continue

            filters, params = _customer_filters(participant_role, participant_id, admin_id)
            where_clause = ' AND '.join(filters)
            cur.execute(
                f"SELECT messages FROM chats WHERE {where_clause} ORDER BY created_at DESC LIMIT 1",
                tuple(params)
            )
            last_message_row = cur.fetchone()
            last_message = last_message_row['messages'] if last_message_row else ''

            conversations.append({
                'room_id': build_customer_room(participant_role, participant_id),
                'role': participant_role,
                'id': participant_id,
                'name': f"{participant_role.capitalize()} #{participant_id}",
                'last_message': last_message,
                'last_message_time': row['last_message_time'].isoformat() if row['last_message_time'] else None,
                'unread_count': row['unread_count'] or 0
            })

        return conversations
    finally:
        conn.close()


def mark_room_read(target_role: str, target_id: int, reader_role: str, admin_id: int = ADMIN_FALLBACK_ID):
    conn = get_db()
    if not conn:
        return

    filters, params = _customer_filters(target_role, target_id, admin_id)
    if reader_role == 'admin':
        filters.append("sender_role != 'admin'")
    else:
        filters.append("sender_role = 'admin'")
    filters.append('is_read = 0')
    where_clause = ' AND '.join(filters)

    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE chats SET is_read = 1 WHERE {where_clause}", tuple(params))
        conn.commit()
    finally:
        conn.close()
