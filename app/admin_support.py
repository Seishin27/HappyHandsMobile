from flask import Blueprint, request, jsonify, session
from .support_chat_model import (
    ADMIN_FALLBACK_ID,
    ADMIN_NOTIFICATIONS_ROOM,
    build_customer_room,
    get_admin_conversations,
    get_support_history,
    mark_room_read,
    save_support_message,
)

support_bp = Blueprint('support', __name__, url_prefix='/api/support')

def _get_current_user():
    # Check for role hint in query params or headers
    role_hint = request.args.get('role') or request.headers.get('X-Chat-Role')
    
    # If hint provided, check that specific session first
    if role_hint == 'admin' and session.get('admin'):
        aid = session['admin'].get('adminID')
        if aid is None: aid = session['admin'].get('id')
        if not aid: aid = ADMIN_FALLBACK_ID
        return 'admin', int(aid)
    elif role_hint == 'seller' and session.get('seller'):
        sid = session['seller'].get('sellerID')
        if sid is None: sid = session['seller'].get('id')
        return 'seller', int(sid) if sid is not None else None
    elif role_hint == 'rider' and session.get('rider'):
        rid = session['rider'].get('riderID')
        if rid is None: rid = session['rider'].get('id')
        return 'rider', int(rid) if rid is not None else None
    elif role_hint == 'user' and session.get('user'):
        uid = session['user'].get('userID')
        if uid is None: uid = session['user'].get('id')
        return 'user', int(uid) if uid is not None else None

    # Fallback to priority order
    if session.get('admin'):
        # Handle 0 correctly (0 is falsy in python)
        aid = session['admin'].get('adminID')
        if aid is None:
            aid = session['admin'].get('id')
        if not aid:
            aid = ADMIN_FALLBACK_ID
        return 'admin', int(aid)
        
    elif session.get('seller'):
        sid = session['seller'].get('sellerID')
        if sid is None: sid = session['seller'].get('id')
        return 'seller', int(sid) if sid is not None else None
        
    elif session.get('rider'):
        rid = session['rider'].get('riderID')
        if rid is None: rid = session['rider'].get('id')
        return 'rider', int(rid) if rid is not None else None
        
    elif session.get('user'):
        uid = session['user'].get('userID')
        if uid is None: uid = session['user'].get('id')
        return 'user', int(uid) if uid is not None else None
        
    return None, None

@support_bp.route('/conversations', methods=['GET'])
def get_conversations():
    role, user_id = _get_current_user()
    if not role or role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    admin_id = user_id or ADMIN_FALLBACK_ID
    conversations = get_admin_conversations(admin_id)
    return jsonify({'success': True, 'conversations': conversations, 'admin_id': admin_id})

@support_bp.route('/conversations/<target_role>/<int:target_id>/messages', methods=['GET'])
def get_messages(target_role, target_id):
    role, user_id = _get_current_user()
    if not role:
        return jsonify({'error': 'Unauthorized'}), 401
        
    limit = int(request.args.get('limit', 50))
    admin_id = ADMIN_FALLBACK_ID

    if role == 'admin':
        admin_id = user_id or ADMIN_FALLBACK_ID
        mark_room_read(target_role, target_id, 'admin', admin_id)
        messages = get_support_history(target_role, target_id, admin_id, limit)
    else:
        if user_id is None or role != target_role or int(user_id) != int(target_id):
            return jsonify({'error': 'Unauthorized access to this conversation'}), 403
        mark_room_read(role, user_id, role, admin_id)
        messages = get_support_history(role, user_id, admin_id, limit)

    return jsonify({'success': True, 'messages': messages})

@support_bp.route('/conversations/<target_role>/<int:target_id>/messages', methods=['POST'])
def post_message(target_role, target_id):
    role, user_id = _get_current_user()
    if not role:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    content = (data.get('message') or '').strip()
    if not content:
        return jsonify({'error': 'Message content required'}), 400

    if role == 'admin':
        admin_id = user_id or ADMIN_FALLBACK_ID
    else:
        admin_id = ADMIN_FALLBACK_ID
    payload = None
    event_name = None
    room_name = None

    if role == 'admin':
        payload = save_support_message(
            build_customer_room(target_role, target_id),
            'admin', admin_id, target_role, target_id, content,
            admin_id=admin_id
        )
        event_name = 'receive_admin_message'
        room_name = build_customer_room(target_role, target_id)
    else:
        if user_id is None or role != target_role or int(user_id) != int(target_id):
            return jsonify({'error': 'Unauthorized'}), 403

        payload = save_support_message(
            build_customer_room(role, user_id),
            role, user_id, 'admin', admin_id, content,
            admin_id=admin_id
        )
        event_name = 'receive_client_message'
        room_name = build_customer_room(role, user_id)

    if not payload:
        return jsonify({'error': 'Failed to save message'}), 500

    from app.authentication import socketio
    if socketio and room_name and event_name:
        socketio.emit(event_name, payload, room=room_name, namespace='/support')
        socketio.emit(event_name, payload, room=ADMIN_NOTIFICATIONS_ROOM, namespace='/support')

    return jsonify({'success': True, 'message': payload})
