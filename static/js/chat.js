(function(){
  if (typeof io === 'undefined') return;

  let socket = null;
  let CURRENT = null;
  const DEFAULT_CONFIG = { panelSelector: '#userChatPanel', overlaySelector: '#userChatsOverlay' };
  let CONFIG = { ...DEFAULT_CONFIG };

  function readCookie(name){
    const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function sessionForRole(role){
    if (!role) return null;
    if (role === 'seller') return readCookie('seller_session');
    if (role === 'rider') return readCookie('rider_session');
    if (role === 'admin') return readCookie('admin_session');
    return readCookie('user_session');
  }

  function initSocket(authToken){
    if (socket) return socket;
    const opts = { withCredentials: true };
    if (authToken){ opts.extraHeaders = { Authorization: 'Bearer ' + authToken }; }
    if (CURRENT && CURRENT.role){
      const sessionToken = sessionForRole(CURRENT.role);
      opts.auth = { role: CURRENT.role };
      if (sessionToken) opts.auth.session = sessionToken;
    }
    socket = io('/chat2', opts);
    socket.on('connect', function(){ console.log('chat socket connected', socket.id); });
    socket.on('message', handleMessageEvent);
    socket.on('notification', handleNotificationEvent);
    return socket;
  }

  function handleMessageEvent(payload){
    if (!payload) return;
    const box = document.querySelector('[data-chat-box][data-chat-active="1"]');
    if (!box) return;
    const peerRole = box.getAttribute('data-peer-role');
    const peerId = box.getAttribute('data-peer-id');
    if (!peerRole || !peerId) return;
    const sRole = String(payload.sender_role||'');
    const sId = String(payload.sender_id||'');
    const rRole = String(payload.receiver_role||'');
    const rId = String(payload.receiver_id||'');
    const match = (sRole === peerRole && sId === peerId) || (rRole === peerRole && rId === peerId);
    if (!match) return;
    appendMessage(box, payload);
    markRead(box);
  }

  function handleNotificationEvent(_n){
    refreshUnreadBadges();
  }

  function appendMessage(box, payload){
    const list = box.querySelector('.chat-messages');
    if (!list) return;
    const me = CURRENT;
    const isMe = !!(me && payload.sender_role === me.role && String(payload.sender_id) === String(me.id));
    const el = document.createElement('div');
    el.className = 'chat-bubble ' + (isMe ? 'chat-bubble-me' : 'chat-bubble-them');
    el.textContent = payload.content || payload.message || '';
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
  }

  async function loadHistory(box){
    const peerRole = box.getAttribute('data-peer-role');
    const peerId = box.getAttribute('data-peer-id');
    if (!peerRole || !peerId) return;
    let url = '/api/chat2/history?peer_role=' + encodeURIComponent(peerRole) + '&peer_id=' + encodeURIComponent(peerId);
    if (CURRENT && CURRENT.role) {
        url += '&role=' + encodeURIComponent(CURRENT.role);
    }
    const r = await fetch(url, { credentials:'same-origin' });
    const j = await r.json().catch(function(){ return null; });
    const list = box.querySelector('.chat-messages');
    if (!list) return;
    list.innerHTML = '';
    if (!j || !j.success || !Array.isArray(j.messages)) return;
    j.messages.forEach(function(m){ appendMessage(box, m); });
  }

  async function markRead(box){
    const peerRole = box.getAttribute('data-peer-role');
    const peerId = box.getAttribute('data-peer-id');
    if (!peerRole || !peerId) return;
    try{
      let headers = {'Content-Type':'application/json'};
      if (CURRENT && CURRENT.role) {
          headers['X-Chat-Role'] = CURRENT.role;
      }
      await fetch('/api/chat2/mark_read', {
        method:'POST',
        credentials:'same-origin',
        headers: headers,
        body: JSON.stringify({ peer_role: peerRole, peer_id: peerId })
      });
    }catch(e){}
  }

  async function refreshUnreadBadges(){
    try{
      let url = '/api/chat2/unread';
      if (CURRENT && CURRENT.role) {
          url += '?role=' + encodeURIComponent(CURRENT.role);
      }
      const r = await fetch(url, { credentials:'same-origin' });
      const j = await r.json().catch(function(){ return null; });
      if (!j || !j.success || !Array.isArray(j.items)) return;
      const map = {};
      j.items.forEach(function(i){ map[i.sender_role + ':' + i.sender_id] = i.unread_count; });
      let total = 0;
      document.querySelectorAll('[data-chat-peer-role][data-chat-peer-id]').forEach(function(el){
        const key = el.getAttribute('data-chat-peer-role') + ':' + el.getAttribute('data-chat-peer-id');
        const count = map[key] || 0;
        total += count;
        const badge = el.querySelector('[data-chat-unread]');
        if (badge){
          badge.textContent = count > 0 ? String(count) : '';
          badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
      });
      const navBadge = document.getElementById('userChatBadge');
      if (navBadge){
        navBadge.textContent = total > 0 ? String(total) : '';
        navBadge.style.display = total > 0 ? 'inline-block' : 'none';
      }
    }catch(e){}
  }

  async function sendMessage(box){
    const input = box.querySelector('.chat-input');
    if (!input) return;
    const txt = (input.value||'').trim();
    if (!txt) return;
    input.value = '';
    const peerRole = box.getAttribute('data-peer-role');
    const peerId = box.getAttribute('data-peer-id');
    if (!peerRole || !peerId) return;
    const s = initSocket(window.CHAT_TOKEN || null);
    s.emit('message', { content: txt, to_role: peerRole, to_id: peerId });
    const fake = { content: txt, sender_role: CURRENT && CURRENT.role, sender_id: CURRENT && CURRENT.id };
    appendMessage(box, fake);
  }

  function bindBox(box){
    if (!box || box.getAttribute('data-chat-bound') === '1') return;
    box.setAttribute('data-chat-bound','1');
    const sendBtn = box.querySelector('.chat-send');
    const input = box.querySelector('.chat-input');
    if (sendBtn) sendBtn.addEventListener('click', function(){ sendMessage(box); });
    if (input) input.addEventListener('keydown', function(e){ if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(box); } });
  }

  function resolveBox(panelOverride){
    if (panelOverride){
      const el = document.querySelector(panelOverride);
      if (el) return el;
    }
    if (CONFIG.panelSelector){
      const el = document.querySelector(CONFIG.panelSelector);
      if (el) return el;
    }
    return document.querySelector('#userChatPanel[data-chat-box]') || document.getElementById('userChatPanel');
  }

  function resolveOverlay(overlayOverride){
    if (overlayOverride === null) return null;
    if (overlayOverride){
      return document.querySelector(overlayOverride);
    }
    if (CONFIG.overlaySelector === null) return null;
    if (CONFIG.overlaySelector){
      return document.querySelector(CONFIG.overlaySelector);
    }
    return document.getElementById('userChatsOverlay');
  }

  function openBox(box){
    box.setAttribute('data-chat-active','1');
    loadHistory(box).then(function(){ markRead(box); });
  }

  window.ChatUI = {
    init: function(currentRole, currentId, authToken, options){
      CURRENT = { role: currentRole, id: currentId };
      CONFIG = { ...DEFAULT_CONFIG, ...(options || {}) };
      if (authToken) window.CHAT_TOKEN = authToken;
      initSocket(authToken);
      document.querySelectorAll('[data-chat-box]').forEach(function(box){ bindBox(box); });
      refreshUnreadBadges();
    },
    openOverlayFor: function(peerRole, peerId, overrides){
      const panelOverride = overrides && overrides.panelSelector;
      const overlayOverride = overrides && Object.prototype.hasOwnProperty.call(overrides, 'overlaySelector') ? overrides.overlaySelector : undefined;
      var box = resolveBox(panelOverride);
      if (!box) return;
      box.setAttribute('data-chat-box','1');
      box.setAttribute('data-peer-role', peerRole);
      box.setAttribute('data-peer-id', peerId);
      bindBox(box);
      var overlay = resolveOverlay(overlayOverride);
      if (overlay) overlay.style.display = 'flex';
      openBox(box);
    },
    closeOverlay: function(){
      var overlay = document.getElementById('userChatsOverlay');
      if (overlay) overlay.style.display = 'none';
      var box = document.querySelector('#userChatPanel[data-chat-box]');
      if (box) box.removeAttribute('data-chat-active');
    },
    refreshUnread: function(){
      refreshUnreadBadges();
    }
  };
})();
