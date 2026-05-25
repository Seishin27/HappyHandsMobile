from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict

from flask import request, session, current_app as app
from flask_jwt_extended import decode_token
from flask_socketio import join_room, emit

from .chat_controller import save_message
from .chat_models import build_room_key
from .support_chat_model import (
    ADMIN_FALLBACK_ID,
    ADMIN_NOTIFICATIONS_ROOM,
    build_customer_room,
    mark_room_read,
    save_support_message,
)

_connected: Dict[str, set] = defaultdict(set)
_sid_identity: Dict[str, dict] = {}
_LIMIT = 20
_WINDOW = 30
_buckets: Dict[str, deque] = defaultdict(deque)


def _decode_identity_from_token(token):
    from app import authentication

    decoded = decode_token(token)
    return authentication.extract_identity_from_decoded(decoded)


def _auth_from_socket(auth=None):
    sid = getattr(request, "sid", None)
    cached = _sid_identity.get(sid) if sid else None
    if cached:
        return cached

    role_hint = None
    session_token = None
    if isinstance(auth, dict):
        role_hint = auth.get("role") or auth.get("auth_role")
        session_token = auth.get("session") or auth.get("session_token")
    try:
        if request.args:
            role_hint = request.args.get('role') or request.args.get('auth_role') or role_hint
            session_token = request.args.get('session') or request.args.get('session_token') or session_token
    except Exception:
        pass

    # Force Admin Role if session exists and hint is admin (or missing)
    # This bypasses potential ambiguity in resolve_socket_identity
    if (not role_hint or role_hint == 'admin') and session.get('admin'):
        admin_data = session.get('admin')
        # Handle case where adminID might be 0
        aid = admin_data.get('adminID')
        if aid is None:
            aid = admin_data.get('id')
        try:
            aid_val = int(aid)
        except (TypeError, ValueError):
            aid_val = 0
        if aid_val <= 0:
            aid_val = ADMIN_FALLBACK_ID
        
        ident = {"role": "admin", "adminID": aid_val}
        if sid:
            _sid_identity[sid] = ident
        return ident

    ident = None
    try:
        from app import authentication

        role, user_id = authentication.resolve_socket_identity(role_hint=role_hint, session_token=session_token)
        if role and user_id is not None:
            ident = {"role": role, f"{role}ID": user_id}
    except Exception:
        ident = None

    if not ident:
        # Fallback: honor the hinted role first, then fall back to known priority order.
        priority_pairs = []
        if role_hint in ("admin", "seller", "rider", "user"):
            priority_pairs.append((role_hint, role_hint))
        for role_key in (("admin", "admin"), ("seller", "seller"), ("rider", "rider"), ("user", "user")):
            if role_key not in priority_pairs:
                priority_pairs.append(role_key)

        for role, key in priority_pairs:
            obj = session.get(key)
            if obj:
                val = obj.get(f"{role}ID")
                if val is None:
                    val = obj.get("id")
                if val is not None:
                    ident = {"role": role, f"{role}ID": val}
                    break

    if ident and sid:
        _sid_identity[sid] = ident
    return ident


def _identity_to_role_id(identity):
    if not isinstance(identity, dict):
        return None, None
    role = identity.get("role")
    if role in ("user", "seller", "rider", "admin"):
        key = f"{role}ID"
        val = identity.get(key) or identity.get("id")
        if val is not None:
            return role, int(val)
    for r in ("user", "seller", "rider", "admin"):
        key = f"{r}ID"
        if identity.get(key) is not None:
            return r, int(identity[key])
    return None, None


def _allowed_pair(sr: str, rr: str) -> bool:
    if sr == "admin" or rr == "admin":
        return True
    if sr == "rider":
        return rr in ("user", "seller")
    if rr == "rider":
        return sr in ("user", "seller")
    return {sr, rr} == {"user", "seller"}


def _rate_limited(sid: str) -> bool:
    now = datetime.utcnow()
    q = _buckets[sid]
    while q and q[0] < now - timedelta(seconds=_WINDOW):
        q.popleft()
    if len(q) >= _LIMIT:
        return True
    q.append(now)
    return False


def register_chat_socket_handlers(socketio):
    def _resolve_admin_id_from_payload(payload, fallback_uid):
        candidate = None
        if isinstance(payload, dict):
            candidate = payload.get('admin_id')
            if candidate is None:
                candidate = payload.get('adminID')
        try:
            candidate_val = int(candidate)
        except (TypeError, ValueError):
            candidate_val = None
        if candidate_val and candidate_val > 0:
            return candidate_val
        try:
            fallback_val = int(fallback_uid)
        except (TypeError, ValueError):
            fallback_val = None
        if fallback_val and fallback_val > 0:
            return fallback_val
        return ADMIN_FALLBACK_ID

    @socketio.on("connect", namespace="/chat2")
    def on_connect(auth):
        ident = _auth_from_socket(auth)
        role, uid = _identity_to_role_id(ident)
        if not role:
            app.logger.debug("socket connect rejected: unauthenticated")
            return False
        sid = request.sid
        key = f"{role}:{uid}"
        _connected[key].add(sid)
        join_room(key, sid=sid)
        app.logger.info(f"socket connected {key} sid={sid}")

    @socketio.on("disconnect", namespace="/chat2")
    def on_disconnect():
        sid = request.sid
        _sid_identity.pop(sid, None)
        for key, sids in list(_connected.items()):
            if sid in sids:
                sids.remove(sid)
                if not sids:
                    _connected.pop(key, None)
                break

    @socketio.on("message", namespace="/chat2")
    def on_message(data):
        if not isinstance(data, dict):
            return
        ident = _auth_from_socket()
        role, uid = _identity_to_role_id(ident)
        if not role:
            return
        sid = request.sid
        if _rate_limited(sid):
            emit("error", {"type": "rate_limit", "msg": "Too many messages"}, to=sid)
            return

        raw = (data.get("content") or data.get("message") or "").strip()
        if not raw:
            return
        text = raw.replace("<", "&lt;").replace(">", "&gt;")

        peer_role = data.get("to_role")
        peer_id = data.get("to_id")
        if peer_role not in ("user", "seller", "rider", "admin") or peer_id is None:
            return
        try:
            peer_id = int(peer_id)
        except Exception:
            return

        if not _allowed_pair(role, peer_role):
            app.logger.warning(f"blocked chat pair {role}->{peer_role}")
            return

        payload = save_message(role, uid, peer_role, peer_id, text)
        
        # Pass through localId if present to support optimistic UI updates
        if isinstance(data, dict) and (data.get('localId') or data.get('local_id')):
            payload['localId'] = data.get('localId') or data.get('local_id')

        room = build_room_key(role, uid, peer_role, peer_id)
        me_key = f"{role}:{uid}"
        peer_key = f"{peer_role}:{peer_id}"

        join_room(room, sid=sid)
        for s in _connected.get(me_key, set()):
            join_room(room, sid=s)
        for s in _connected.get(peer_key, set()):
            join_room(room, sid=s)

        socketio.emit("message", payload, room=room, namespace="/chat2")
        notif = {
            "from_role": role,
            "from_id": uid,
            "content": text,
            "conversation_id": payload["conversation_id"],
        }
        socketio.emit("notification", notif, room=peer_key, namespace="/chat2")

    # Support Chat Handlers (V2 - Strict Separation)
    @socketio.on("connect", namespace="/support")
    def on_support_connect(auth):
        ident = _auth_from_socket(auth)
        role, uid = _identity_to_role_id(ident)
        if role == 'admin':
            join_room(ADMIN_NOTIFICATIONS_ROOM)

    @socketio.on("join_admin_room", namespace="/support")
    def on_join_admin_room(data):
        # Admin joins a customer-service room: room_customer_<role>_<id>
        ident = _auth_from_socket()
        role, uid = _identity_to_role_id(ident)
        
        if role != 'admin':
            emit('error', {'msg': 'Unauthorized join'}, to=request.sid)
            return
            
        target_role = data.get('role')
        target_id = data.get('id')
        
        if target_role and target_id:
            try:
                target_id_int = int(target_id)
            except (TypeError, ValueError):
                emit('error', {'msg': 'Invalid participant id'}, to=request.sid)
                return

            room_id = build_customer_room(target_role, target_id_int)
            join_room(room_id)
            admin_id = _resolve_admin_id_from_payload(data, uid)
            mark_room_read(target_role, target_id_int, 'admin', admin_id)
            emit('admin_joined', {'room': room_id})

    @socketio.on("client_join_support", namespace="/support")
    def on_client_join_support(data):
        # Client joins their customer-service room: room_customer_<role>_<id>
        ident = _auth_from_socket()
        role, uid = _identity_to_role_id(ident)
        
        if not role or role == 'admin':
            return
            
        room_id = build_customer_room(role, uid)
        join_room(room_id)
        
        # Resolve admin_id from payload to ensure we mark the correct conversation as read
        # (though usually client joining implies they read admin messages)
        admin_id = _resolve_admin_id_from_payload(data, ADMIN_FALLBACK_ID)
        
        mark_room_read(role, uid, role, admin_id)
        emit('client_joined', {'room': room_id})

    @socketio.on("admin_send_message", namespace="/support")
    def on_admin_send_message(data):
        ident = _auth_from_socket()
        role, uid = _identity_to_role_id(ident)
        
        if role != 'admin':
            emit('error', {'msg': 'Unauthorized: You are not an admin'}, to=request.sid)
            return
            
        admin_id = _resolve_admin_id_from_payload(data, uid)
        target_role = (data.get('role') or '').lower()
        message = (data.get('message') or '').strip()

        try:
            target_id = int(data.get('id'))
        except (TypeError, ValueError):
            emit('error', {'msg': 'Invalid participant id'}, to=request.sid)
            return

        if target_role not in {'user', 'seller', 'rider'} or not message:
            emit('error', {'msg': 'Missing data'}, to=request.sid)
            return

        room_id = build_customer_room(target_role, target_id)
        saved_msg = save_support_message(room_id, 'admin', admin_id, target_role, target_id, message, admin_id=admin_id)

        if not saved_msg:
            emit('error', {'msg': 'Failed to save message'}, to=request.sid)
            return

        mark_room_read(target_role, target_id, 'admin', admin_id)
        emit('receive_admin_message', saved_msg, room=room_id)
        emit('receive_admin_message', saved_msg, room=ADMIN_NOTIFICATIONS_ROOM)

    @socketio.on("client_send_message_to_admin", namespace="/support")
    def on_client_send_message_to_admin(data):
        ident = _auth_from_socket()
        role, uid = _identity_to_role_id(ident)
        
        if not role or role == 'admin':
            return
            
        message = (data.get('message') or '').strip()
        if not message:
            return
            
        room_id = build_customer_room(role, uid)
        
        # Use the admin_id provided by the client (e.g. 1), fallback to default if invalid
        admin_id = _resolve_admin_id_from_payload(data, ADMIN_FALLBACK_ID)
        
        saved_msg = save_support_message(room_id, role, uid, 'admin', admin_id, message, admin_id=admin_id)

        if saved_msg:
            emit('receive_client_message', saved_msg, room=room_id)
            emit('receive_client_message', saved_msg, room=ADMIN_NOTIFICATIONS_ROOM)
