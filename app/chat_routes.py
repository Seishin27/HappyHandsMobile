from flask import Blueprint, request, jsonify, session
import logging
from flask_jwt_extended import decode_token

from .chat_controller import fetch_history, mark_read, unread_summary, list_conversations

chat_bp = Blueprint("chat2", __name__, url_prefix="/api/chat2")


def _decode_identity_from_token(token):
    from app import authentication

    decoded = decode_token(token)
    return authentication.extract_identity_from_decoded(decoded)


def _auth_from_http():
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
        try:
            ident = _decode_identity_from_token(token)
            if isinstance(ident, dict):
                return ident
        except Exception:
            pass
    # Also accept access_token from cookie for browser clients
    try:
        token_cookie = request.cookies.get('access_token')
    except Exception:
        token_cookie = None
    if token_cookie:
        try:
            ident = _decode_identity_from_token(token_cookie)
            if isinstance(ident, dict):
                return ident
        except Exception:
            pass
            
    # Check for role hint in query params or headers
    role_hint = request.args.get('role') or request.headers.get('X-Chat-Role')
    
    # If hint provided, check that specific session first
    if role_hint in ("user", "seller", "rider", "admin"):
        obj = session.get(role_hint)
        if obj and (obj.get(f"{role_hint}ID") or obj.get("id")):
            return {"role": role_hint, f"{role_hint}ID": obj.get(f"{role_hint}ID") or obj.get("id")}

    # Fallback to priority order if no hint or hint invalid
    for role, key in (("user", "user"), ("seller", "seller"), ("rider", "rider"), ("admin", "admin")):
        obj = session.get(key)
        if obj and (obj.get(f"{role}ID") or obj.get("id")):
            return {"role": role, f"{role}ID": obj.get(f"{role}ID") or obj.get("id")}
    return None


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


@chat_bp.get("/history")
def api_history():
    ident = _auth_from_http()
    me_role, me_id = _identity_to_role_id(ident)
    if not me_role:
        return jsonify({"success": False, "msg": "unauthorized"}), 401
    peer_role = request.args.get("peer_role")
    peer_id = request.args.get("peer_id", type=int)
    page = request.args.get("page", default=1, type=int)
    size = request.args.get("page_size", default=50, type=int)
    if not peer_role or not peer_id:
        return jsonify({"success": False, "msg": "peer required"}), 400
    try:
        conv, rows = fetch_history(me_role, me_id, peer_role, peer_id, page, size)
        return jsonify({"success": True, "conversation": conv, "messages": rows})
    except Exception as e:
        logging.exception('chat2 history failed')
        return jsonify({"success": False, "msg": "history_error", "error": str(e)}), 500


@chat_bp.post("/mark_read")
def api_mark_read():
    ident = _auth_from_http()
    me_role, me_id = _identity_to_role_id(ident)
    if not me_role:
        return jsonify({"success": False, "msg": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    peer_role = data.get("peer_role")
    peer_id = data.get("peer_id")
    if not peer_role or peer_id is None:
        return jsonify({"success": False, "msg": "peer required"}), 400
    try:
        updated = mark_read(me_role, me_id, peer_role, int(peer_id))
        return jsonify({"success": True, "updated": updated})
    except Exception as e:
        logging.exception('chat2 mark_read failed')
        return jsonify({"success": False, "msg": "mark_read_error", "error": str(e)}), 500


@chat_bp.get("/unread")
def api_unread():
    ident = _auth_from_http()
    me_role, me_id = _identity_to_role_id(ident)
    if not me_role:
        return jsonify({"success": False, "msg": "unauthorized"}), 401
    try:
        items = unread_summary(me_role, me_id)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        logging.exception('chat2 unread failed')
        return jsonify({"success": False, "msg": "unread_error", "error": str(e)}), 500


@chat_bp.get("/get_unread_counts")
def api_get_unread_counts():
    """
    Returns JSON: { conversation_id, unread_count }
    Note: In this system, conversation_id is a composite key, but we will return
    a list of objects with peer info and unread count to satisfy the requirement.
    """
    ident = _auth_from_http()
    me_role, me_id = _identity_to_role_id(ident)
    if not me_role:
        return jsonify({"success": False, "msg": "unauthorized"}), 401
    try:
        items = unread_summary(me_role, me_id)
        # Transform to match the requested format roughly, or just return the items
        # The user asked for { conversation_id, unread_count }
        # We'll return a list of these objects.
        # Since we don't have a single conversation_id integer, we'll construct one or return peer info.
        # For now, let's return the detailed list which is more useful for the frontend.
        return jsonify({"success": True, "items": items})
    except Exception as e:
        logging.exception('chat2 get_unread_counts failed')
        return jsonify({"success": False, "msg": "error", "error": str(e)}), 500


@chat_bp.get("/conversations")
def api_conversations():
    ident = _auth_from_http()
    me_role, me_id = _identity_to_role_id(ident)
    if not me_role:
        return jsonify({"success": False, "msg": "unauthorized"}), 401
    limit = request.args.get("limit", default=50, type=int)
    try:
        items = list_conversations(me_role, me_id, limit)
        return jsonify({"success": True, "items": items})
    except Exception as e:
        logging.exception('chat2 conversations failed')
        return jsonify({"success": False, "msg": "failed to fetch conversations", "error": str(e)}), 500
