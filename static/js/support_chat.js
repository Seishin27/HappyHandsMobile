document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('supportChatBtn');
    if (!toggleBtn) return;

    const closeBtn = document.getElementById('supportChatCloseBtn');
    const chatWindow = document.getElementById('supportChatModal');
    const messagesContainer = document.getElementById('supportChatMessages');
    const input = document.getElementById('supportChatInput');
    const sendBtn = document.getElementById('supportChatSendBtn');

    const SUPPORT_ADMIN_ID = 1;
    function sanitizeId(value) {
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    // Get user info from body data attributes
    const body = document.body;
    const userId = sanitizeId(body.dataset.userId);
    const sellerId = sanitizeId(body.dataset.sellerId);
    const riderId = sanitizeId(body.dataset.riderId);
    
    let role = 'user';
    let id = userId;

    if (sellerId) {
        role = 'seller';
        id = sellerId;
    } else if (riderId) {
        role = 'rider';
        id = riderId;
    } else if (!id) {
        id = null;
    }

    function getCookie(name) {
        try {
            const prefix = name + '=';
            return document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith(prefix))?.substring(prefix.length) || null;
        } catch (err) {
            return null;
        }
    }

    const socketOptions = {
        query: { role: role || 'user' },
        withCredentials: true
    };
    
    const sellerSession = getCookie('seller_session');
    const riderSession = getCookie('rider_session');
    const userSession = getCookie('user_session');

    if (role === 'seller' && sellerSession) {
        socketOptions.auth = { role: 'seller', session: sellerSession };
    } else if (role === 'rider' && riderSession) {
        socketOptions.auth = { role: 'rider', session: riderSession };
    } else if (role === 'user' && userSession) {
        socketOptions.auth = { role: 'user', session: userSession };
    } else {
        socketOptions.auth = { role: role || 'user' };
    }

    let socket;
    try {
        if (typeof io !== 'undefined') {
            socket = io('/support', socketOptions);
        } else {
            console.warn('Socket.io is not loaded. Chat functionality will be limited.');
        }
    } catch (e) {
        console.error('Error initializing socket.io:', e);
    }

    let joinedRoom = false;
    let historyLoaded = false;

    // Toggle window
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Prevent any default action
            console.log('Support chat button clicked');
            
            const isHidden = chatWindow.style.display === 'none' || chatWindow.style.display === '';
            chatWindow.style.display = isHidden ? 'flex' : 'none';
            
            if (isHidden) {
                if (!historyLoaded && id) {
                    fetchHistory();
                }
                scrollToBottom();
                if (!joinedRoom && id && socket) {
                    connectSocket();
                }
                // Focus input
                if (input) setTimeout(() => input.focus(), 100);
            }
        });
    }

    function fetchHistory() {
        if (!role || !id) return;
        fetch(`/api/support/conversations/${role}/${id}/messages?role=${role}`, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    if (messagesContainer) {
                        messagesContainer.innerHTML = ''; 
                        data.messages.forEach(msg => {
                            const type = msg.sender_role === 'admin' ? 'received' : 'sent';
                            appendMessage(msg.content || msg.message, type);
                        });
                        historyLoaded = true;
                        scrollToBottom();
                    }
                }
            })
            .catch(err => console.error('Error fetching support history:', err));
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            chatWindow.style.display = 'none';
        });
    }

    function connectSocket() {
        if (!socket || !id) return;
        const joinPayload = { role: role, id: id, admin_id: SUPPORT_ADMIN_ID };
        if (socket.connected) {
            socket.emit('client_join_support', joinPayload);
            joinedRoom = true;
        } else {
            socket.once('connect', function handleConnect() {
                socket.emit('client_join_support', joinPayload);
                joinedRoom = true;
            });
            try { socket.connect(); } catch (err) {}
        }
    }

    if (socket) {
        socket.on('receive_admin_message', function(data) {
            // data: { message, sender_role, ... }
            if (data.sender_role === 'admin') {
                appendMessage(data.message, 'received');
            }
        });
        
        socket.on('receive_client_message', function(data) {
            // We might receive our own message if we are in the room.
            // Ignore if we appended optimistically.
        });
    }

    function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        if (!id) {
            alert('Please log in to contact support.');
            return;
        }

        if (socket) {
                if (!joinedRoom) {
                    connectSocket();
                }
                socket.emit('client_send_message_to_admin', {
                    role: role,
                    id: id,
                    admin_id: SUPPORT_ADMIN_ID,
                    message: text
                });
        } else {
            console.warn('Cannot send message: Socket not connected');
            alert('Chat service is currently unavailable. Please try again later.');
            return;
        }

        appendMessage(text, 'sent');
        input.value = '';
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    if (input) {
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    function appendMessage(text, type) {
        if (!messagesContainer) return;
        // Remove empty placeholder if present
        const empty = messagesContainer.querySelector('.ai-chat-empty');
        if (empty) empty.remove();

        const div = document.createElement('div');
        const cssClass = type === 'sent' ? 'user' : 'assistant';
        div.className = `ai-msg ${cssClass}`;
        div.textContent = text;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
});
