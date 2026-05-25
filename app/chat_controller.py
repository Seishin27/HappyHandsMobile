from typing import List, Dict, Any, Tuple
from datetime import datetime

def _get_db_connection():
    from app import authentication
    return authentication.get_db_connection()

def _ensure_columns(conn):
    """Ensure adminID and riderID columns exist in chats table."""
    try:
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM chats")
        columns = [row[0] for row in cur.fetchall()]
        
        if 'riderID' not in columns:
            try:
                cur.execute("ALTER TABLE chats ADD COLUMN riderID INT NULL AFTER sellerID")
                cur.execute("CREATE INDEX idx_chats_admin_rider ON chats (adminID, riderID)")
            except Exception: pass
            
        if 'adminID' not in columns:
            try:
                cur.execute("ALTER TABLE chats ADD COLUMN adminID INT NULL AFTER riderID")
                cur.execute("CREATE INDEX idx_chats_admin_user ON chats (adminID, userID)")
                cur.execute("CREATE INDEX idx_chats_admin_seller ON chats (adminID, sellerID)")
            except Exception:
                pass

        if 'chat_type' not in columns:
            try:
                cur.execute("ALTER TABLE chats ADD COLUMN chat_type VARCHAR(30) NOT NULL DEFAULT 'customer_service' AFTER sender_role")
                cur.execute("CREATE INDEX idx_chats_chat_type ON chats (chat_type)")
            except Exception:
                pass

        cur.close()
    except Exception:
        pass

def _map_ids(role1, id1, role2, id2):
    """Map two participants to userID, sellerID, riderID, adminID dict."""
    mapping = {'userID': 0, 'sellerID': 0, 'riderID': 0, 'adminID': 0}

    for r, i in ((role1, id1), (role2, id2)):
        if i is None:
            continue
        try:
            value = int(i)
        except (TypeError, ValueError):
            continue

        if r == 'user':
            mapping['userID'] = value
        elif r == 'seller':
            mapping['sellerID'] = value
        elif r == 'rider':
            mapping['riderID'] = value
        elif r == 'admin':
            mapping['adminID'] = value

    if mapping['adminID'] == 0 and (role1 == 'admin' or role2 == 'admin'):
        mapping['adminID'] = 1

    return mapping


def _resolve_chat_type(role1: str, role2: str) -> str:
    """Infer chat_type based on participant roles."""
    roles = {role1 or '', role2 or ''}
    roles = {r.lower() for r in roles if r}

    if 'admin' in roles:
        return 'customer_service'
    if roles == {'user', 'seller'}:
        return 'user_seller'
    if 'rider' in roles:
        return 'seller_rider'
    return 'system_notification'


def _conversation_filters(chat_type: str, ids: Dict[str, int]) -> Tuple[List[str], List[int]]:
    filters: List[str] = ['chat_type = %s']
    params: List[int] = [chat_type]

    if chat_type == 'customer_service':
        if ids['adminID']:
            filters.append('adminID = %s')
            params.append(ids['adminID'])
        if ids['userID']:
            filters.append('userID = %s')
            params.append(ids['userID'])
            filters.extend(['(sellerID = 0 OR sellerID IS NULL)', '(riderID = 0 OR riderID IS NULL)'])
        elif ids['sellerID']:
            filters.append('sellerID = %s')
            params.append(ids['sellerID'])
            filters.extend(['(userID = 0 OR userID IS NULL)', '(riderID = 0 OR riderID IS NULL)'])
        elif ids['riderID']:
            filters.append('riderID = %s')
            params.append(ids['riderID'])
            filters.extend(['(userID = 0 OR userID IS NULL)', '(sellerID = 0 OR sellerID IS NULL)'])
    elif chat_type == 'user_seller':
        filters.append('userID = %s')
        params.append(ids['userID'])
        filters.append('sellerID = %s')
        params.append(ids['sellerID'])
        filters.extend(['(riderID = 0 OR riderID IS NULL)', '(adminID = 0 OR adminID IS NULL)'])
    elif chat_type == 'seller_rider':
        if ids['sellerID']:
            filters.append('sellerID = %s')
            params.append(ids['sellerID'])
        if ids['riderID']:
            filters.append('riderID = %s')
            params.append(ids['riderID'])
        if ids['userID']:
            filters.append('userID = %s')
            params.append(ids['userID'])
        filters.append('(adminID = 0 OR adminID IS NULL)')
    else:
        for col, val in ids.items():
            filters.append(f"{col} = %s")
            params.append(val)

    return filters, params


def _infer_peer(chat_type: str, me_role: str, ids: Dict[str, int]) -> Tuple[str | None, int | None]:
    if chat_type == 'customer_service':
        if me_role == 'admin':
            for role, column in (('user', 'userID'), ('seller', 'sellerID'), ('rider', 'riderID')):
                if ids.get(column, 0):
                    return role, ids[column]
            return None, None
        return 'admin', ids.get('adminID') or 1

    if chat_type == 'user_seller':
        if me_role == 'user':
            return 'seller', ids.get('sellerID')
        if me_role == 'seller':
            return 'user', ids.get('userID')

    if chat_type == 'seller_rider':
        if me_role == 'seller':
            if ids.get('riderID'):
                return 'rider', ids['riderID']
            if ids.get('userID'):
                return 'user', ids['userID']
        elif me_role == 'rider':
            if ids.get('sellerID'):
                return 'seller', ids['sellerID']
            if ids.get('userID'):
                return 'user', ids['userID']
        elif me_role == 'user':
            if ids.get('sellerID'):
                return 'seller', ids['sellerID']
            if ids.get('riderID'):
                return 'rider', ids['riderID']

    return None, None

def save_message(
    me_role: str, me_id: int, peer_role: str, peer_id: int, content: str
) -> Dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("empty message")

    chat_type = _resolve_chat_type(me_role, peer_role)
    ids = _map_ids(me_role, me_id, peer_role, peer_id)
    conn = _get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")
    _ensure_columns(conn)
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
            content[:10000], '', me_role, chat_type
        ))
        msg_id = cur.lastrowid
        conn.commit()
        
        return {
            "id": msg_id,
            "conversation_id": 0, 
            "content": content,
            "sender_role": me_role,
            "sender_id": me_id,
            "receiver_role": peer_role,
            "receiver_id": peer_id,
            "chat_type": chat_type,
            "created_at": datetime.now().isoformat()
        }
    finally:
        conn.close()

def fetch_history(
    me_role: str,
    me_id: int,
    peer_role: str,
    peer_id: int,
    page: int,
    page_size: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    chat_type = _resolve_chat_type(me_role, peer_role)
    ids = _map_ids(me_role, me_id, peer_role, peer_id)
    offset = max(0, (page - 1) * page_size)
    conn = _get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")
    _ensure_columns(conn)
    try:
        cur = conn.cursor(dictionary=True)

        filters, params = _conversation_filters(chat_type, ids)
        where_clause = " AND ".join(filters)

        query = f"""
            SELECT chatID as id, messages as content, sender_role, created_at, chat_type
            FROM chats
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        
        messages = []
        for r in reversed(rows): 
            s_role = r['sender_role']
            s_id = None
            if s_role == 'user': s_id = ids['userID']
            elif s_role == 'seller': s_id = ids['sellerID']
            elif s_role == 'rider': s_id = ids['riderID']
            elif s_role == 'admin': s_id = ids['adminID']
            
            r_role = peer_role if s_role == me_role else me_role
            r_id = peer_id if s_role == me_role else me_id

            messages.append({
                "id": r['id'],
                "content": r['content'],
                "sender_role": s_role,
                "sender_id": s_id,
                "receiver_role": r_role,
                "receiver_id": r_id,
                "chat_type": r.get('chat_type'),
                "created_at": r['created_at'].isoformat() if r['created_at'] else None
            })
            
        return {"id": 0}, messages
    finally:
        conn.close()

def mark_read(me_role: str, me_id: int, peer_role: str, peer_id: int) -> int:
    # Use a more direct update approach that doesn't rely on strict NULL/0 checks for other columns
    # This ensures we catch all messages between these two parties where I am the receiver.
    
    conn = _get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")
    _ensure_columns(conn)
    try:
        cur = conn.cursor()
        
        # Determine my column and peer column
        my_col = None
        if me_role == 'user': my_col = 'userID'
        elif me_role == 'seller': my_col = 'sellerID'
        elif me_role == 'rider': my_col = 'riderID'
        elif me_role == 'admin': my_col = 'adminID'
        
        peer_col = None
        if peer_role == 'user': peer_col = 'userID'
        elif peer_role == 'seller': peer_col = 'sellerID'
        elif peer_role == 'rider': peer_col = 'riderID'
        elif peer_role == 'admin': peer_col = 'adminID'
        
        if not my_col or not peer_col:
            return 0
            
        # Update query: 
        # WHERE my_col = me_id AND peer_col = peer_id AND sender_role = peer_role AND is_read = 0
        
        query = f"UPDATE chats SET is_read=1 WHERE {my_col}=%s AND {peer_col}=%s AND sender_role=%s AND is_read=0"
        cur.execute(query, (me_id, peer_id, peer_role))
        count = cur.rowcount
        conn.commit()
        return count
    finally:
        conn.close()

def unread_summary(me_role: str, me_id: int) -> List[Dict[str, Any]]:
    conn = _get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")
    _ensure_columns(conn)
    try:
        cur = conn.cursor(dictionary=True)
        
        my_col = None
        if me_role == 'user': my_col = 'userID'
        elif me_role == 'seller': my_col = 'sellerID'
        elif me_role == 'rider': my_col = 'riderID'
        elif me_role == 'admin': my_col = 'adminID'
        
        if not my_col:
            return []

        chat_types_map = {
            'user': ('user_seller', 'customer_service'),
            'seller': ('user_seller', 'seller_rider', 'customer_service'),
            'rider': ('seller_rider', 'customer_service'),
            'admin': ('customer_service',),
        }
        allowed_types = chat_types_map.get(me_role, ())
        if not allowed_types:
            return []

        placeholders = ','.join(['%s'] * len(allowed_types))
            
        query = f"""
            SELECT 
                sender_role,
                CASE 
                    WHEN sender_role='user' THEN userID
                    WHEN sender_role='seller' THEN sellerID
                    WHEN sender_role='rider' THEN riderID
                    WHEN sender_role='admin' THEN adminID
                END as sender_id,
                chat_type,
                COUNT(*) as unread_count,
                MAX(created_at) as last_ts
            FROM chats
            WHERE {my_col} = %s AND sender_role != %s AND is_read = 0
              AND chat_type IN ({placeholders})
            GROUP BY sender_role, sender_id, chat_type
            ORDER BY last_ts DESC
        """

        params = [me_id, me_role, *allowed_types]
        cur.execute(query, tuple(params))
        return cur.fetchall() or []
    finally:
        conn.close()

def list_conversations(
    me_role: str,
    me_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    conn = _get_db_connection()
    if not conn:
        raise RuntimeError("DB connection failed")
    _ensure_columns(conn)
    try:
        cur = conn.cursor(dictionary=True)
        
        my_col = None
        if me_role == 'user':
            my_col = 'userID'
        elif me_role == 'seller':
            my_col = 'sellerID'
        elif me_role == 'rider':
            my_col = 'riderID'
        elif me_role == 'admin':
            my_col = 'adminID'

        if not my_col:
            return []

        chat_types_map = {
            'user': ('user_seller', 'customer_service'),
            'seller': ('user_seller', 'seller_rider', 'customer_service'),
            'rider': ('seller_rider', 'customer_service'),
            'admin': ('customer_service',),
        }
        allowed_types = chat_types_map.get(me_role, ())
        if not allowed_types:
            return []

        placeholders = ','.join(['%s'] * len(allowed_types))

        query_id = me_id
        if me_role == 'admin' and me_id == 0:
            query_id = 1

        query = f"""
            SELECT DISTINCT userID, sellerID, riderID, adminID, chat_type
            FROM chats
            WHERE {my_col} = %s AND chat_type IN ({placeholders})
        """
        cur.execute(query, (query_id, *allowed_types))
        rows = cur.fetchall()

        conversations: List[Dict[str, Any]] = []
        seen_peers = set()

        for r in rows:
            ids = {
                'userID': int(r.get('userID') or 0),
                'sellerID': int(r.get('sellerID') or 0),
                'riderID': int(r.get('riderID') or 0),
                'adminID': int(r.get('adminID') or 0),
            }
            chat_type = r.get('chat_type')
            if not chat_type:
                if ids['riderID'] and (me_role == 'seller' or me_role == 'rider'):
                    chat_type = 'seller_rider'
                elif ids['adminID']:
                    chat_type = 'customer_service'
                else:
                    chat_type = _resolve_chat_type(me_role, 'admin' if me_role != 'admin' else 'user')
            
            peer_role, peer_id = _infer_peer(chat_type, me_role, ids)
            if not peer_role or not peer_id:
                continue

            key = (chat_type, peer_role, peer_id)
            if key in seen_peers:
                continue
            seen_peers.add(key)

            filters, params = _conversation_filters(chat_type, ids)
            where_clause = " AND ".join(filters)

            cur.execute(
                f"SELECT messages, created_at FROM chats WHERE {where_clause} ORDER BY created_at DESC LIMIT 1",
                tuple(params)
            )
            last_msg = cur.fetchone()

            cur.execute(
                f"SELECT COUNT(*) as cnt FROM chats WHERE {where_clause} AND sender_role = %s AND is_read = 0",
                tuple(params) + (peer_role,)
            )
            unread = cur.fetchone()

            if last_msg:
                conversations.append({
                    "conversation_id": 0,
                    "peer_role": peer_role,
                    "peer_id": peer_id,
                    "chat_type": chat_type,
                    "lastMessage": last_msg['messages'],
                    "lastMessageAt": last_msg['created_at'],
                    "unreadCount": unread['cnt'] if unread else 0
                })

        conversations.sort(key=lambda x: x['lastMessageAt'] or datetime.min, reverse=True)
        return conversations[:limit]

    finally:
        conn.close()

def get_or_create_conversation(me_role, me_id, peer_role, peer_id):
    # Dummy implementation for compatibility if imported elsewhere
    return {"id": 0, "room_key": f"{me_role}:{me_id}_{peer_role}:{peer_id}"}
