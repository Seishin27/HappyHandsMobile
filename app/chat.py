from flask import current_app as app
from typing import List, Optional, Tuple, Dict, Any


def save_chat_message(conn, room: str, sender_type: str, senderID: str, message: str, productID: Optional[int] = None, sellerID: Optional[int] = None, userID: Optional[int] = None, riderID: Optional[int] = None, adminID: Optional[int] = None) -> Optional[Dict[str, Any]]:
    
    if not conn:
        return None
    if not isinstance(message, str) or not message.strip():
        return None
    try:
        # Determine which ID to populate based on sender_type and provided IDs
        user_id_val = None
        seller_id_val = None
        rider_id_val = None
        admin_id_val = None
        try:
            if sender_type == 'user' and senderID:
                # try to coerce numeric id when possible
                user_id_val = int(senderID) if str(senderID).isdigit() else senderID
        except Exception:
            user_id_val = senderID
        try:
            if sellerID is not None:
                seller_id_val = int(sellerID) if str(sellerID).isdigit() else sellerID
            elif sender_type == 'seller' and senderID:
                seller_id_val = int(senderID) if str(senderID).isdigit() else senderID
        except Exception:
            seller_id_val = sellerID or (senderID if sender_type == 'seller' else None)
        try:
            if riderID is not None:
                rider_id_val = int(riderID) if str(riderID).isdigit() else riderID
            elif sender_type == 'rider' and senderID:
                rider_id_val = int(senderID) if str(senderID).isdigit() else senderID
        except Exception:
            rider_id_val = riderID or (senderID if sender_type == 'rider' else None)
        try:
            if adminID is not None:
                admin_id_val = int(adminID) if str(adminID).isdigit() else adminID
            elif sender_type == 'admin' and senderID:
                admin_id_val = int(senderID) if str(senderID).isdigit() else senderID
        except Exception:
            admin_id_val = adminID or (senderID if sender_type == 'admin' else None)

        cur = conn.cursor()

        # Inspect columns so we can safely insert optional fields (created_at, is_read, sender_role)
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            existing_cols = [r[0] for r in meta.fetchall()]
            try:
                meta.close()
            except Exception:
                pass
        except Exception:
            existing_cols = []

        # Ensure riderID column exists when we are about to store a rider association
        if rider_id_val is not None and 'riderID' not in existing_cols:
            try:
                schema_cur = conn.cursor()
                schema_cur.execute("ALTER TABLE chats ADD COLUMN riderID INT NULL AFTER sellerID")
                existing_cols.append('riderID')
                try:
                    schema_cur.close()
                except Exception:
                    pass
            except Exception:
                # If alteration fails (lack of privileges / already exists), continue without raising
                pass

        # Ensure adminID column exists when we are about to store an admin association
        if admin_id_val is not None and 'adminID' not in existing_cols:
            try:
                schema_cur = conn.cursor()
                schema_cur.execute("ALTER TABLE chats ADD COLUMN adminID INT NULL AFTER riderID")
                existing_cols.append('adminID')
                try:
                    schema_cur.close()
                except Exception:
                    pass
            except Exception:
                pass

        # Ensure productID column exists when we are about to store a product association
        if productID is not None and 'productID' not in existing_cols:
            try:
                schema_cur = conn.cursor()
                schema_cur.execute("ALTER TABLE chats ADD COLUMN productID INT NULL AFTER adminID")
                existing_cols.append('productID')
                try:
                    schema_cur.close()
                except Exception:
                    pass
            except Exception:
                pass

        insert_cols = []
        insert_vals = []

        # Always include messages
        insert_cols.append('messages')
        insert_vals.append(message[:10000])

        # include userID/sellerID when available
        if user_id_val is not None or userID is not None:
            # prefer explicit userID param when provided (recipient mapping)
            uid = userID if userID is not None else user_id_val
            # Ensure we only insert valid IDs (>0)
            if (isinstance(uid, int) and uid > 0) or (isinstance(uid, str) and uid.isdigit() and int(uid) > 0):
                insert_cols.append('userID')
                insert_vals.append(int(uid))
            else:
                print(f"DEBUG: Skipping userID insert because uid={uid} is invalid")

        if seller_id_val is not None:
            try:
                sid = int(seller_id_val)
                if sid > 0:
                    insert_cols.append('sellerID')
                    insert_vals.append(sid)
                else:
                    print(f"DEBUG: Skipping sellerID insert because sid={sid} <= 0")
            except (ValueError, TypeError):
                pass
        
        if rider_id_val is not None and 'riderID' in existing_cols:
            try:
                rid = int(rider_id_val)
                if rid > 0:
                    insert_cols.append('riderID')
                    insert_vals.append(rid)
            except (ValueError, TypeError):
                pass

        if admin_id_val is not None and 'adminID' in existing_cols:
            # Allow adminID 0 if it's used for system, but prefer > 0
            insert_cols.append('adminID')
            insert_vals.append(admin_id_val)

        if productID is not None and 'productID' in existing_cols:
            insert_cols.append('productID')
            insert_vals.append(productID)
            
        # sender_role column (if exists) to easily determine who sent the message
        if 'sender_role' in existing_cols:
            insert_cols.append('sender_role')
            insert_vals.append(sender_type or 'user')

        # is_read flag (default 0)
        if 'is_read' in existing_cols:
            insert_cols.append('is_read')
            insert_vals.append(0)

        # messages_image (if exists and not provided, default to empty string to satisfy NOT NULL)
        if 'messages_image' in existing_cols:
            insert_cols.append('messages_image')
            insert_vals.append('')

        # chat_type column (if exists)
        if 'chat_type' in existing_cols:
            insert_cols.append('chat_type')
            # Infer chat_type
            inferred_type = 'user_seller'
            if admin_id_val:
                inferred_type = 'customer_service'
            elif rider_id_val:
                inferred_type = 'seller_rider'
            insert_vals.append(inferred_type)

        # build SQL; if created_at exists we'll let DB set default CURRENT_TIMESTAMP; don't set it explicitly
        cols_sql = ','.join(insert_cols)
        placeholders = ','.join(['%s'] * len(insert_vals))
        sql = f"INSERT INTO chats ({cols_sql}) VALUES ({placeholders})"
        cur.execute(sql, tuple(insert_vals))
        conn.commit()
        inserted = getattr(cur, 'lastrowid', None)

        created_at = None
        try:
            if inserted and 'created_at' in existing_cols:
                cur2 = conn.cursor()
                cur2.execute('SELECT created_at FROM chats WHERE chatID = %s LIMIT 1', (inserted,))
                r = cur2.fetchone()
                try:
                    cur2.close()
                except Exception:
                    pass
                if r:
                    created_at = r[0]
        except Exception:
            try:
                app.logger.exception('Failed to fetch created_at for inserted chat')
            except Exception:
                pass

        try:
            cur.close()
        except Exception:
            pass

        return {'chatID': inserted, 'created_at': created_at}
    except Exception as e:
        try:
            app.logger.exception('Failed to save chat message: %s', e)
        except Exception:
            pass
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def get_chat_history(conn, sellerID: Optional[int] = None, userID: Optional[int] = None, riderID: Optional[int] = None, adminID: Optional[int] = None, limit: int = 50) -> List[dict]:
    """Return list of chat rows from `chats` table ordered oldest->newest.

    Because the existing `chats` table doesn't include a timestamp column in this schema
    we order by `chatID` as a surrogate for chronological order (descending -> newest first).
    """
    if not conn:
        return []
    try:
        # detect available columns and include them when present
        try:
            meta = conn.cursor()
            meta.execute("SHOW COLUMNS FROM chats")
            existing_cols = [r[0] for r in meta.fetchall()]
            try: meta.close()
            except Exception: pass
        except Exception:
            existing_cols = []

        cur = conn.cursor(dictionary=True)
        base_cols = ['chatID', 'userID', 'sellerID', 'messages', 'messages_image']
        if 'riderID' in existing_cols:
            base_cols.append('riderID')
        if 'adminID' in existing_cols:
            base_cols.append('adminID')
        if 'sender_role' in existing_cols:
            base_cols.append('sender_role')
        if 'is_read' in existing_cols:
            base_cols.append('is_read')
        if 'created_at' in existing_cols:
            base_cols.append('created_at')

        sql = 'SELECT ' + ', '.join(base_cols) + ' FROM chats'
        clauses = []
        params = []
        if sellerID is not None:
            clauses.append('sellerID = %s')
            params.append(sellerID)
        if userID is not None:
            clauses.append('userID = %s')
            params.append(userID)
        if riderID is not None and 'riderID' in existing_cols:
            clauses.append('riderID = %s')
            params.append(riderID)
        if adminID is not None and 'adminID' in existing_cols:
            clauses.append('adminID = %s')
            params.append(adminID)
            
        if clauses:
            sql += ' WHERE ' + ' AND '.join(clauses)
        sql += ' ORDER BY chatID DESC LIMIT %s'
        params.append(limit)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        try:
            cur.close()
        except Exception:
            pass
        # return oldest-first
        return list(reversed(rows))
    except Exception:
        try:
            app.logger.exception('Failed to fetch chat history')
        except Exception:
            pass
        try:
            cur.close()
        except Exception:
            pass
        return []


# Note: This project already uses a `chats` table. Example columns expected:
#   chatID (PK), userID, sellerID, messages, messages_image
# If you prefer the more feature-rich model (room/product/time) consider adding
# columns or creating a new `chat_messages` table, but current helpers use `chats`.
