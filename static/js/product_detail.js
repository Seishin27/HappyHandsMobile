// =========================
// Product Image Gallery
// =========================
function initProductGallery() {
    const gallery = document.getElementById('productGallery');
    const mainImage = document.getElementById('productMainImage');
    const modal = document.getElementById('productGalleryModal');
    if (!gallery || !mainImage || !modal) return;

    const placeholder = gallery.dataset.placeholder || '';
    let images = [];
    try {
        images = JSON.parse(gallery.dataset.images || '[]') || [];
    } catch (err) {
        images = [];
    }
    if (!images.length && placeholder) {
        images = [placeholder];
    }

    let activeIndex = Number(mainImage.dataset.activeIndex || 0) || 0;
    const thumbs = Array.from(gallery.querySelectorAll('[data-role="thumb"]'));

    const modalImage = modal.querySelector('[data-role="modal-image"]');
    const modalThumbContainer = modal.querySelector('[data-role="modal-thumbnails"]');
    const modalPrev = modal.querySelector('[data-role="modal-prev"]');
    const modalNext = modal.querySelector('[data-role="modal-next"]');
    const modalCloseEls = modal.querySelectorAll('[data-role="modal-close"]');
    const modalBackdrop = modal.querySelector('.gallery-modal-backdrop');

    if (!modalImage || !modalThumbContainer) return;

    function clampIndex(index) {
        if (!images.length) return 0;
        if (index < 0) return images.length - 1;
        if (index >= images.length) return 0;
        return index;
    }

    function highlightThumbs(index) {
        thumbs.forEach(btn => {
            btn.classList.toggle('is-active', Number(btn.dataset.index) === index);
        });
        Array.from(modalThumbContainer.querySelectorAll('button')).forEach(btn => {
            btn.classList.toggle('is-active', Number(btn.dataset.index) === index);
        });
    }

    function swapImage(index, opts = {}) {
        if (!images.length) return;
        const nextIndex = clampIndex(index);
        if (!opts.force && nextIndex === activeIndex) return;
        const nextSrc = images[nextIndex] || placeholder;
        activeIndex = nextIndex;
        mainImage.dataset.activeIndex = String(activeIndex);
        highlightThumbs(activeIndex);

        mainImage.classList.add('is-transitioning');
        const handleLoad = () => {
            mainImage.classList.remove('is-transitioning');
            mainImage.removeEventListener('load', handleLoad);
        };
        mainImage.addEventListener('load', handleLoad);
        mainImage.src = nextSrc;
        setTimeout(() => {
            mainImage.classList.remove('is-transitioning');
        }, 250);

        if (modalImage) {
            modalImage.src = nextSrc;
            modalImage.dataset.activeIndex = String(activeIndex);
        }
    }

    function buildModalThumbnails() {
        modalThumbContainer.innerHTML = '';
        images.forEach((src, index) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.dataset.index = String(index);
            if (index === activeIndex) btn.classList.add('is-active');
            const img = document.createElement('img');
            img.src = src;
            img.alt = 'Gallery thumbnail ' + (index + 1);
            img.loading = 'lazy';
            btn.appendChild(img);
            btn.addEventListener('click', () => {
                swapImage(index, { force: true });
            });
            modalThumbContainer.appendChild(btn);
        });
    }

    function openModal() {
        buildModalThumbnails();
        modalImage.src = images[activeIndex] || placeholder;
        modal.setAttribute('aria-hidden', 'false');
        modal.hidden = false;
        modal.classList.add('is-visible');
        document.addEventListener('keydown', handleModalKeydown);
        modal.querySelector('.gallery-modal-close')?.focus();
    }

    function closeModal() {
        modal.setAttribute('aria-hidden', 'true');
        modal.classList.remove('is-visible');
        modal.hidden = true;
        document.removeEventListener('keydown', handleModalKeydown);
    }

    function handleModalKeydown(event) {
        if (modal.getAttribute('aria-hidden') === 'true') return;
        if (event.key === 'Escape') {
            event.preventDefault();
            closeModal();
        } else if (event.key === 'ArrowRight') {
            event.preventDefault();
            swapImage(activeIndex + 1, { force: true });
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            swapImage(activeIndex - 1, { force: true });
        }
    }

    thumbs.forEach(btn => {
        const index = Number(btn.dataset.index);
        btn.addEventListener('click', () => swapImage(index));
        btn.addEventListener('mouseenter', () => {
            if (window.matchMedia('(pointer:fine)').matches) {
                swapImage(index);
            }
        });
        btn.addEventListener('focus', () => swapImage(index));
    });

    const triggerElements = [gallery.querySelector('[data-role="gallery-modal-trigger"]'), mainImage]
        .filter((el, idx, arr) => el && arr.indexOf(el) === idx);
    triggerElements.forEach(el => {
        el.addEventListener('click', openModal);
        el.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                openModal();
            }
        });
    });

    modalPrev?.addEventListener('click', () => swapImage(activeIndex - 1, { force: true }));
    modalNext?.addEventListener('click', () => swapImage(activeIndex + 1, { force: true }));
    modalCloseEls.forEach(el => {
        el.addEventListener('click', closeModal);
    });
    if (modalBackdrop) {
        modalBackdrop.addEventListener('click', closeModal);
    }

    // Initialize modal image and thumbs
    swapImage(activeIndex, { force: true });
}

document.addEventListener('DOMContentLoaded', initProductGallery);

// =========================
// Quantity Controls (Plus/Minus)
// =========================
function initQuantityControls() {
    const qtyInput = document.getElementById('quantity');
    const minusBtn = document.querySelector('.qty-btn.minus');
    const plusBtn = document.querySelector('.qty-btn.plus');
    const qtyError = document.querySelector('.qty-error');

    if (!qtyInput || !minusBtn || !plusBtn) return;

    const min = Number(qtyInput.getAttribute('min') || 1) || 1;
    const max = Number(qtyInput.getAttribute('max') || 1) || 1;

    function setQty(next) {
        let value = Number(next);
        if (Number.isNaN(value)) value = min;
        if (value < min) value = min;
        if (value > max) value = max;
        qtyInput.value = String(value);

        // UI feedback for invalid attempts
        const invalid = next < min || next > max;
        qtyInput.classList.toggle('qty-invalid', !!invalid);
        if (qtyError) {
            if (invalid) {
                qtyError.textContent = next > max ? `Only ${max} in stock` : 'Quantity must be at least 1';
                qtyError.style.display = 'block';
            } else {
                qtyError.style.display = 'none';
            }
        }

        // Enable/disable buttons at bounds
        minusBtn.disabled = (value <= min);
        plusBtn.disabled = (value >= max);
    }

    minusBtn.addEventListener('click', function(){
        const current = Number(qtyInput.value || min) || min;
        setQty(current - 1);
    });

    plusBtn.addEventListener('click', function(){
        const current = Number(qtyInput.value || min) || min;
        setQty(current + 1);
    });

    qtyInput.addEventListener('input', function(){
        const parsed = Number(qtyInput.value);
        setQty(parsed);
    });

    qtyInput.addEventListener('blur', function(){
        const parsed = Number(qtyInput.value);
        setQty(parsed);
    });

    // Initialize state
    setQty(Number(qtyInput.value || min) || min);
}

document.addEventListener('DOMContentLoaded', initQuantityControls);

// =========================
// Product Specific Chat (Chat Now button)
// =========================
// Minimal Socket.IO chat wiring (client side)
let chatSocket = null;

async function ChatButton() {
    const chatBtn = document.getElementById('chatBtn');
    if (!chatBtn) return;

    const socketListeners = [];
    function readCookie(name) {
        const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : null;
    }
    const initSocket = (room, onMessage) => {
        if (typeof io === 'undefined') {
            console.warn('Socket.IO client not found. Make sure socket.io script is loaded.');
            return;
        }
        // register callback
        if (typeof onMessage === 'function') socketListeners.push(onMessage);
        if (!chatSocket) {
            // connect to same origin
            const opts = { withCredentials: true };
            const role = (chatBtn.dataset && chatBtn.dataset.userId) ? 'user' : null;
            if (role) {
                opts.auth = { role: role };
                const token = readCookie(role === 'user' ? 'user_session' : null);
                if (token) opts.auth.session = token;
            }
            chatSocket = io(opts);
            chatSocket.on('connect', () => console.log('chat: connected'));
            chatSocket.on('system', (p) => console.log('chat system:', p));
            chatSocket.on('chat_message', (payload) => {
                if (!payload) return;
                // normalize payload shape: message text may be in 'message' or 'messages'
                try{ if (payload.messages && !payload.message) payload.message = payload.messages; }catch(e){}
                try{
                    socketListeners.forEach(cb => { try{ cb && cb(payload); }catch(e){console.error('chat listener error',e);} });
                }catch(e){ console.error('dispatch chat listeners', e); }
            });
        }
        // No explicit room/join for private support chat; server routes messages by recipient id.
    };

    // Connect socket immediately so realtime messages arrive even if modal is not open yet.
    // The global handler will append to the modal if it's open.
    initSocket(null, (payload) => {
        try{
            const text = payload.message || payload.messages || '';
            const currentUserId = (chatBtn && chatBtn.dataset) ? (chatBtn.dataset.userId || '') : '';
            // filter: only deliver messages for the currently open seller conversation and this user
            const overlay = document.getElementById('copilot-chat-overlay');
            if (!overlay) return;
            // avoid duplicate appends: when modal-specific handler is active, skip global handler
            if (overlay.getAttribute('data-modal-handler') === '1') return;
            const convSellerId = overlay.getAttribute('data-seller-id') || '';
            const plSellerId = String(payload.sellerID || payload.sellerId || payload.seller_id || payload.recipientID || payload.recipientId || payload.recipient_id || '');
            const plUserId = String(payload.userID || payload.userId || payload.user_id || '');
            if (convSellerId && plSellerId && String(convSellerId) !== plSellerId) return;
            if (currentUserId && plUserId && String(currentUserId) !== plUserId) return;

            // determine if message bubble should be styled as user or seller
            let isUser = false;
            if (payload.sender === 'user' || payload.sender_role === 'user' || payload.sender_type === 'user') isUser = true;
            else {
                const senderId = payload.senderID || payload.senderId || payload.sender_id || null;
                if (senderId && currentUserId && String(senderId) === String(currentUserId)) isUser = true;
            }
            const messages = overlay.querySelector('.copilot-chat-messages');
            if (!messages) return;
            const mid = payload.messageID || payload.messageId || payload.chatID || null;
            try{ if (mid && messages.querySelector(`[data-message-id="${mid}"]`)) return; }catch(e){}
            // If server didn't provide an id, try to reconcile with any optimistic local message
            if (!mid) {
                try {
                    const localEl = Array.from(messages.querySelectorAll('[data-local="1"]')).find(el => el.textContent === String(text) && el.getAttribute('data-sender') === (isUser ? 'user' : 'seller'));
                    if (localEl) {
                        localEl.removeAttribute('data-local');
                        localEl.classList.toggle('user-bubble', !!isUser);
                        localEl.classList.toggle('seller-bubble', !isUser);
                        messages.scrollTop = messages.scrollHeight;
                        return;
                    }
                } catch (e) { /* ignore */ }
            }
            const b = document.createElement('div');
            if (mid) b.setAttribute('data-message-id', String(mid));
            b.textContent = text;
            if (isUser) { b.setAttribute('data-sender','user'); b.classList.add('user-bubble'); }
            else { b.setAttribute('data-sender','seller'); b.classList.add('seller-bubble'); }
            b.style.cssText = `max-width:85%;padding:8px 10px;border-radius:10px;font-size:14px;${isUser ? 'align-self:flex-end;background:#007bff;color:#fff;' : 'align-self:flex-start;background:#f1f1f3;color:#111;'}`;
            messages.appendChild(b);
            messages.scrollTop = messages.scrollHeight;
        }catch(e){ console.error('chat global handler', e); }
    });

    const openChatModal = (sellerId, productId) => {
        // If modal already exists, just focus input
        const existing = document.getElementById('copilot-chat-overlay');
        if (existing) {
            const input = existing.querySelector('.copilot-chat-input');
            input?.focus();
            return;
        }

        // Overlay
        const overlay = document.createElement('div');
        overlay.id = 'copilot-chat-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;z-index:10000;padding:16px;';
        // store conversation seller id for realtime filtering
        try{ overlay.setAttribute('data-seller-id', String(sellerId||'')); }catch(e){}
        // mark that modal has its own socket handler to prevent duplicate appends
        overlay.setAttribute('data-modal-handler','1');

        // Modal
        const modal = document.createElement('div');
        modal.id = 'copilot-chat-modal';
        modal.style.cssText = 'width:360px;max-width:100%;background:#fff;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.2);display:flex;flex-direction:column;overflow:hidden;font-family:Arial,Helvetica,sans-serif;';

        // Header
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:#f5f5f7;border-bottom:1px solid #e6e6e8;';
        const title = document.createElement('div');
        title.textContent = 'Chat with us';
        title.style.cssText = 'font-weight:600;color:#111;font-size:15px;';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.innerHTML = '&times;';
        closeBtn.setAttribute('aria-label', 'Close chat');
        closeBtn.style.cssText = 'border:none;background:transparent;font-size:22px;line-height:1;cursor:pointer;color:#333;padding:6px;';
        header.appendChild(title);
        header.appendChild(closeBtn);

        // Messages container
        const messages = document.createElement('div');
        messages.className = 'copilot-chat-messages';
        messages.style.cssText = 'padding:12px;display:flex;flex-direction:column;gap:8px;max-height:300px;overflow:auto;background:#fff;';

        // Welcome message
        const welcome = document.createElement('div');
        welcome.style.cssText = 'align-self:flex-start;background:#f1f1f3;color:#111;padding:8px 10px;border-radius:10px;max-width:85%;font-size:14px;';
        welcome.textContent = 'Hi! How can we help you today?';
        messages.appendChild(welcome);

        // Footer (input + send)
        const footer = document.createElement('div');
        footer.style.cssText = 'display:flex;gap:8px;padding:10px;border-top:1px solid #e6e6e8;background:#fafafa;';
        const input = document.createElement('input');
        input.className = 'copilot-chat-input';
        input.type = 'text';
        input.placeholder = 'Type a message...';
        input.style.cssText = 'flex:1;padding:8px 10px;border-radius:6px;border:1px solid #ddd;font-size:14px;';
        const send = document.createElement('button');
        send.type = 'button';
        send.textContent = 'Send';
        send.style.cssText = 'padding:8px 12px;background:#007bff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-size:14px;';

        footer.appendChild(input);
        footer.appendChild(send);

        modal.appendChild(header);
        modal.appendChild(messages);
        modal.appendChild(footer);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

    // expose a global hook so other pages can open the chat modal via URL params or UI
    try { window.openChatModal = openChatModal; } catch (e) { /**/ }

        // Helpers: append message with optional id to avoid duplicates
        // Supports optimistic local messages (msgId starting with 'local-') and will reconcile when server echo arrives.
        const appendMessage = (text, isUser = true, msgId = null) => {
            try{
                // If this is a server-ack (real id), try to reconcile with any optimistic local message
                if (msgId && String(msgId).indexOf('local-') !== 0) {
                    // if element with this message-id already exists, skip
                    if (messages.querySelector(`[data-message-id="${msgId}"]`)) return;
                    // try to find a local optimistic message with the same text+sender and replace its id
                    const localEl = Array.from(messages.querySelectorAll('[data-local="1"]')).find(el => el.textContent === String(text) && el.getAttribute('data-sender') === (isUser ? 'user' : 'seller'));
                    if (localEl) {
                        localEl.setAttribute('data-message-id', String(msgId));
                        localEl.removeAttribute('data-local');
                        // ensure classes/style remain correct
                        localEl.classList.toggle('user-bubble', !!isUser);
                        localEl.classList.toggle('seller-bubble', !isUser);
                        messages.scrollTop = messages.scrollHeight;
                        return;
                    }
                } else if (msgId && String(msgId).indexOf('local-') === 0) {
                    // local optimistic append - don't dedupe by message-id
                    // but avoid creating duplicates of same local id
                    if (messages.querySelector(`[data-message-local-id="${msgId}"]`)) return;
                }
                // If the server sent no message id (msgId falsy), try to reconcile with an optimistic local message
                // to avoid creating a duplicate when the server echo lacks an id.
                if (!msgId) {
                    try {
                        const localElNoId = Array.from(messages.querySelectorAll('[data-local="1"]')).find(el => el.textContent === String(text) && el.getAttribute('data-sender') === (isUser ? 'user' : 'seller'));
                        if (localElNoId) {
                            // Mark this optimistic message as confirmed (remove optimistic flag) and keep UI intact
                            localElNoId.removeAttribute('data-local');
                            // Ensure classes are correct
                            localElNoId.classList.toggle('user-bubble', !!isUser);
                            localElNoId.classList.toggle('seller-bubble', !isUser);
                            messages.scrollTop = messages.scrollHeight;
                            return; // don't append a duplicate
                        }
                    } catch (e) { /* ignore reconciliation errors */ }
                }
            }catch(e){}

            const b = document.createElement('div');
            if (msgId && String(msgId).indexOf('local-') !== 0) b.setAttribute('data-message-id', String(msgId));
            if (msgId && String(msgId).indexOf('local-') === 0) b.setAttribute('data-message-local-id', String(msgId));
            // mark optimistic local messages
            if (msgId && String(msgId).indexOf('local-') === 0) b.setAttribute('data-local', '1');
            b.textContent = text;
            if (isUser) { b.setAttribute('data-sender','user'); b.classList.add('user-bubble'); }
            else { b.setAttribute('data-sender','seller'); b.classList.add('seller-bubble'); }
            b.style.cssText = `max-width:85%;padding:8px 10px;border-radius:10px;font-size:14px;${isUser ? 'align-self:flex-end;background:#007bff;color:#fff;' : 'align-self:flex-start;background:#f1f1f3;color:#111;'}`;
            messages.appendChild(b);
            messages.scrollTop = messages.scrollHeight;
        };

        // Event listeners
        const closeModal = () => {
            document.removeEventListener('keydown', onKeyDown);
            overlay.remove();
        };

        const onKeyDown = (ev) => {
            if (ev.key === 'Escape') closeModal();
            if (ev.key === 'Enter' && document.activeElement === input) {
                ev.preventDefault();
                send.click();
            }
        };

        // Initialize socket for this seller/product
        const room = `seller_${sellerId}_product_${productId || '0'}`;

        // Load recent chat history (if any)
        try {
            const q = [];
            const currentUserId = (chatBtn && chatBtn.dataset) ? (chatBtn.dataset.userId || '') : '';
            if (sellerId) q.push(`sellerID=${encodeURIComponent(sellerId)}`);
            if (currentUserId) q.push(`userID=${encodeURIComponent(currentUserId)}`);
            if (productId) q.push(`productID=${encodeURIComponent(productId)}`);
            const url = '/api/chat/history' + (q.length ? '?' + q.join('&') : '');
            fetch(url, { credentials: 'same-origin' })
                .then(r => r.json())
                .then(j => {
                    if (j && j.success && Array.isArray(j.messages)) {
                        // append messages in chronological order
                        j.messages.forEach(m => {
                            // normalize message text
                            const text = m.message || m.messages || m.messages_text || '';
                            // Determine if this message was sent by the current user.
                            // Prefer explicit sender_role/sender fields, then senderID. Avoid using m.userID
                            // because that often represents the conversation's user (constant) rather than the sender.
                            let isUser = false;
                            if (m.sender === 'user' || m.sender_type === 'user' || m.sender_role === 'user') {
                                isUser = true;
                            } else {
                                const senderId = m.senderID || m.senderId || m.sender_id || null;
                                if (senderId && currentUserId && String(senderId) === String(currentUserId)) {
                                    isUser = true;
                                }
                            }
                            // append with chatID to prevent duplicates
                            appendMessage(text, isUser, m.chatID || m.chatId || m.id || null);
                        });
                    }
                })
                .catch(() => {});
        } catch (e) {
            // ignore history fetch errors
        }

        initSocket(room, (payload) => {
            // normalize message text and id
            const text = payload.message || payload.messages || '';
            // Determine sender: prefer explicit sender_role or sender, fallback to senderID match
            let isUser = false;
            if (payload.sender === 'user' || payload.sender_role === 'user' || payload.sender_type === 'user') {
                isUser = true;
            } else {
                const senderId = payload.senderID || payload.senderId || payload.sender_id || null;
                const currentUserId = (chatBtn && chatBtn.dataset) ? (chatBtn.dataset.userId || '') : '';
                if (senderId && currentUserId && String(senderId) === String(currentUserId)) isUser = true;
            }
            const mid = payload.messageID || payload.messageId || payload.chatID || null;
            appendMessage(text, isUser, mid);
        });

        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', (ev) => {
            if (ev.target === overlay) closeModal();
        });
        modal.addEventListener('click', (ev) => ev.stopPropagation());

        send.addEventListener('click', () => {
            const val = input.value.trim();
            if (!val) return;
            input.value = '';
            input.focus();

            // Ensure socket exists and ALWAYS emit  Socket.IO will buffer until connected.
            try{
                const currentUserId = (chatBtn && chatBtn.dataset) ? (chatBtn.dataset.userId || '') : '';
                const productName = (document.querySelector('.product-title')?.textContent || '').trim();
                const payload = { message: val, productID: productId, productName: productName, sellerID: sellerId, userID: currentUserId };
                // create socket if missing
                if (!chatSocket) {
                    if (typeof io === 'undefined') { console.warn('Socket.IO client missing'); }
                    else {
                        const opts = { withCredentials: true };
                        const role = (chatBtn.dataset && chatBtn.dataset.userId) ? 'user' : null;
                        if (role) {
                            opts.auth = { role: role };
                            const token = readCookie(role === 'user' ? 'user_session' : null);
                            if (token) opts.auth.session = token;
                        }
                        chatSocket = io(opts);
                        if (chatSocket && typeof chatSocket.on === 'function') chatSocket.on('connect', ()=>console.log('chat: connected'));
                    }
                }
                try { chatSocket.emit('chat_message', payload); }
                catch(e) { console.error('emit failed', e); }
                // Optimistic local append so user sees their message immediately. Will be reconciled when server echoes back a real id.
                try{ const localId = 'local-' + Date.now(); appendMessage(val, true, localId); }catch(e){ console.error('local append failed', e); }
                console.debug('chat: emitted', payload, { connected: !!(chatSocket && chatSocket.connected) });
            } catch (err) { console.error('chat send error', err); appendMessage(val, true); }
        });

        document.addEventListener('keydown', onKeyDown);
        // Focus input after append
        setTimeout(() => input.focus(), 50);
    };

    chatBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const sellerId = chatBtn.getAttribute('data-seller-id') || '';
        const productId = chatBtn.getAttribute('data-product-id') || '';
        const currentUserId = (chatBtn && chatBtn.dataset) ? (chatBtn.dataset.userId || '') : '';
        if (!currentUserId) {
            try {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'info',
                        title: 'Log in required',
                        text: 'You must log in first to chat with the seller.',
                        confirmButtonText: 'Go to Login'
                    }).then(() => { window.location.href = '/login'; });
                } else {
                    alert('You must log in first to chat with the seller.');
                    window.location.href = '/login';
                }
            } catch (e) {
                window.location.href = '/login';
            }
            return;
        }
        openChatModal(sellerId, productId);
    });
}

// Initialize chat button wiring
ChatButton();

// If URL contains open_chat (or openChat) param, auto-open the chat modal when possible
document.addEventListener('DOMContentLoaded', function () {
    try {
        const params = new URLSearchParams(window.location.search);
        const shouldOpen = params.get('open_chat') || params.get('openChat');
        if (!shouldOpen) return;
        const sellerId = params.get('seller_id') || params.get('sellerID') || document.querySelector('[data-seller-id]')?.getAttribute('data-seller-id') || '';
        const productId = params.get('product_id') || params.get('productID') || document.querySelector('[data-product-id]')?.getAttribute('data-product-id') || '';
        const tryOpen = () => {
            if (window.openChatModal) { window.openChatModal(sellerId, productId); return true; }
            return false;
        };
        if (!tryOpen()) {
            // If chat wiring isn't ready yet, retry shortly
            const t = setInterval(() => { if (tryOpen()) clearInterval(t); }, 250);
            setTimeout(() => clearInterval(t), 5000);
        }
    } catch (e) { console.error('auto-open chat error', e); }
});

function sanitizeProductDescription(input) {
    if (!input) return '';
    const template = document.createElement('template');
    template.innerHTML = String(input);
    const allowed = new Set(['BR','P','UL','OL','LI','STRONG','B','EM','I','DIV','SPAN']);
    (function clean(node){
        Array.from(node.childNodes).forEach(child => {
            if (child.nodeType === 1) {
                clean(child);
                if (!allowed.has(child.tagName)) {
                    while (child.firstChild) child.parentNode.insertBefore(child.firstChild, child);
                    child.remove();
                } else {
                    Array.from(child.attributes).forEach(attr => child.removeAttribute(attr.name));
                }
            } else if (child.nodeType === 8) {
                child.remove();
            }
        });
    })(template.content || template);
    return template.innerHTML.replace(/\u00a0/g, ' ').trim();
}

function normalizeDescriptionBreaks(html) {
    if (!html) return '';
    if (/(<\s*(br|p|ul|ol|li|div|span))/i.test(html)) return html;
    const normalized = html.replace(/\r\n|\r/g, '\n');
    return normalized
        .split(/\n\n+/)
        .map(block => block.replace(/\n/g, '<br>'))
        .join('<br><br>');
}

function formatProductDescription(value) {
    if (!value) return '';
    return normalizeDescriptionBreaks(sanitizeProductDescription(value));
}

document.addEventListener('DOMContentLoaded', function(){
    const descriptionBody = document.getElementById('productDescriptionBody');
    if (!descriptionBody) return;
    const toggleBtn = document.getElementById('productDescriptionToggle');
    let raw = descriptionBody.dataset.rawDescription || '';
    if (raw) {
        try { raw = JSON.parse(raw); }
        catch (e) { /* raw stays string */ }
    }
    const formatted = formatProductDescription(raw || descriptionBody.innerHTML || '');
    if (formatted) {
        descriptionBody.innerHTML = formatted;
    } else {
        descriptionBody.innerHTML = '<p>No description available.</p>';
        if (toggleBtn) toggleBtn.hidden = true;
        return;
    }
    if (!toggleBtn) return;
    const MAX_HEIGHT = 240;
    const updateToggleState = () => {
        if (descriptionBody.scrollHeight > MAX_HEIGHT + 8) {
            if (!descriptionBody.classList.contains('expanded')) {
                descriptionBody.classList.add('collapsed');
            }
            toggleBtn.hidden = false;
        } else {
            descriptionBody.classList.remove('collapsed');
            descriptionBody.classList.remove('expanded');
            toggleBtn.hidden = true;
        }
    };
    toggleBtn.addEventListener('click', () => {
        const expanded = descriptionBody.classList.toggle('expanded');
        if (expanded) {
            descriptionBody.classList.remove('collapsed');
        } else {
            descriptionBody.classList.add('collapsed');
        }
        toggleBtn.textContent = expanded ? 'See less' : 'See more';
    });
    updateToggleState();
    window.addEventListener('resize', updateToggleState);
});
