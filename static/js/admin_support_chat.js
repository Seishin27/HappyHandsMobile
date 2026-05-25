document.addEventListener('DOMContentLoaded', function() {
    const conversationsList = document.getElementById('supportConversationsList');
    const chatMessages = document.getElementById('adminChatMessages');
    const chatInput = document.getElementById('adminChatInput');
    const sendBtn = document.getElementById('adminChatSendBtn');
    const chatHeader = document.getElementById('adminChatHeader');
    const chatInputArea = document.getElementById('adminChatInputArea');
    const currentChatUserSpan = document.getElementById('currentChatUser');
    const currentChatRoleSpan = document.getElementById('currentChatRole');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const bodyEl = document.body;
    const FALLBACK_ADMIN_ID = 1;
    const bodyAdminId = bodyEl && bodyEl.dataset && bodyEl.dataset.adminId ? parseInt(bodyEl.dataset.adminId, 10) : NaN;
    const defaultAdminId = Number.isFinite(bodyAdminId) && bodyAdminId > 0 ? bodyAdminId : FALLBACK_ADMIN_ID;

    let currentConversation = null;
    // Pass role='admin' to help server resolve identity correctly
    let socket = io('/support', {
        query: { role: 'admin' }
    });
    let adminId = null; 
    let allConversations = [];

    function sanitizeAdminId(value) {
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }

    function resolveAdminId() {
        return sanitizeAdminId(adminId) || defaultAdminId;
    }

    function joinConversationRoom(conv) {
        if (!socket || !conv) {
            return;
        }
        socket.emit('join_admin_room', {
            role: conv.role,
            id: conv.id,
            admin_id: resolveAdminId()
        });
    }

    function handleSupportTabActivation() {
        if (currentConversation) {
            joinConversationRoom(currentConversation);
            return;
        }
        if (allConversations.length) {
            loadConversation(allConversations[0]);
        } else {
            fetchConversations();
        }
    }

    document.addEventListener('click', function(evt) {
        const navLink = evt.target.closest && evt.target.closest('.nav-link');
        if (navLink && navLink.dataset && navLink.dataset.target === 'support-chat') {
            // Clear main badge
            const mainBadge = document.getElementById('adminMsgBadge');
            if (mainBadge) {
                mainBadge.style.display = 'none';
                mainBadge.textContent = '0';
            }
            handleSupportTabActivation();
        }
    });

    // Initialize Socket.IO
    socket.on('connect', function() {
        console.log('Connected to chat server');
        fetchConversations();
    });

    socket.on('error', function(data) {
        console.error('Socket Error:', data);
        alert('Error: ' + (data.msg || 'Unknown socket error'));
    });

    socket.on('receive_client_message', function(data) {
        console.log('Received client message:', data);

        // Increment main sidebar badge if not on support-chat tab
        const supportTab = document.getElementById('support-chat');
        if (!supportTab || supportTab.style.display === 'none' || !supportTab.classList.contains('active')) {
            const mainBadge = document.getElementById('adminMsgBadge');
            if (mainBadge) {
                const cur = parseInt(mainBadge.textContent || '0') || 0;
                mainBadge.textContent = String(cur + 1);
                mainBadge.style.display = 'inline-block';
            }
        }
        
        // data: { room_id, sender_role, sender_id, message, ... }
        // Parse room_id to get context
        const parts = data.room_id.split('_');
        // room_customer_<role>_<id>
        const contextRole = parts[2];
        const contextId = parts[3];
        
        // If we are currently chatting with this context
        if (currentConversation && 
            currentConversation.role === contextRole && 
            currentConversation.id == contextId) {
            
            appendMessage(data.message, 'received', data.created_at);
            scrollToBottom();
            
            // Mark as read immediately since we are viewing it
            fetch('/api/chat2/mark_read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ peer_role: contextRole, peer_id: contextId }),
                credentials: 'include'
            }).catch(e => console.error('Failed to mark read on live message', e));
        }

        // Refresh conversations list to update last message
        fetchConversations(false);  
    });
    
    socket.on('receive_admin_message', function(data) {
        // We might receive our own message if we are in the room, 
        // but we usually append it optimistically. 
        // If we want to confirm delivery, we can use this.
        // For now, ignore to avoid duplicates if we append on send.
    });

    // Filter handling
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => {
                b.classList.remove('active');
                b.style.background = '#fff';
                b.style.color = '#000';
            });
            btn.classList.add('active');
            btn.style.background = '#0b73ff';
            btn.style.color = '#fff';
            const filter = btn.dataset.filter;
            renderConversations(filter);
        });
    });

    function fetchConversations(resetFilter = true) {
        fetch('/api/support/conversations?role=admin', { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    allConversations = data.conversations;
                    const fetchedAdminId = sanitizeAdminId(data.admin_id);
                    if (fetchedAdminId) {
                        adminId = fetchedAdminId;
                        console.log("Admin ID set to:", adminId);
                    }
                    
                    // Ensure the currently active conversation is marked as read in our local list
                    // so the badge doesn't reappear if the list refreshes while we are chatting.
                    if (currentConversation) {
                        const active = allConversations.find(c => c.role === currentConversation.role && c.id === currentConversation.id);
                        if (active) {
                            active.unread_count = 0;
                        }
                    }

                    // Server auto-subscribes admins to the notification hub on connect, no extra join needed.

                    if (resetFilter) {
                        const activeFilterBtn = document.querySelector('.filter-btn.active');
                        const filter = activeFilterBtn ? activeFilterBtn.dataset.filter : 'all';
                        renderConversations(filter);
                    } else {
                        // Just re-render with current filter
                        const activeFilterBtn = document.querySelector('.filter-btn.active');
                        const filter = activeFilterBtn ? activeFilterBtn.dataset.filter : 'all';
                        renderConversations(filter);
                    }
                }
            })
            .catch(error => console.error('Error fetching conversations:', error));
    }

    function renderConversations(filter) {
        conversationsList.innerHTML = '';
        
        let filtered = allConversations;
        if (filter !== 'all') {
            filtered = allConversations.filter(c => c.role === filter);
        }

        if (filtered.length === 0) {
            conversationsList.innerHTML = '<li style="padding:12px;color:#64748b;text-align:center;">No conversations found.</li>';
            return;
        }

        filtered.forEach(conv => {
            const li = document.createElement('li');
            li.className = 'message-item';
            li.dataset.role = conv.role;
            li.dataset.id = conv.id;
            li.style.cursor = 'pointer';
            li.style.padding = '10px';
            li.style.borderBottom = '1px solid #f1f5f9';
            
            // Highlight active conversation
            if (currentConversation && currentConversation.role === conv.role && currentConversation.id === conv.id) {
                li.style.backgroundColor = '#f8fafc';
                li.style.borderLeft = '3px solid #0b73ff';
            }

            const unread = conv.unread_count || 0;
            const avatarIcon = conv.role === 'seller' ? '<i class="fas fa-store"></i>' : (conv.role === 'rider' ? '<i class="fas fa-motorcycle"></i>' : '<i class="fas fa-user"></i>');
            const avatarClass = conv.role;

            li.innerHTML = `
                <div style="display:flex; gap:10px; align-items:center;">
                    <div class="avatar-wrapper" style="position:relative;">
                        <div class="avatar ${avatarClass}" style="width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#f1f5f9;color:#64748b;">${avatarIcon}</div>
                        <span class="unread-badge" style="${unread > 0 ? '' : 'display:none;'}">${unread}</span>
                    </div>
                    <div style="flex:1; min-width:0;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-weight:bold; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${conv.name}</div>
                            <div style="font-size:11px; color:#94a3b8; flex-shrink:0; margin-left:4px;">${formatTime(conv.last_message_time)}</div>
                        </div>
                        <div style="font-size:12px; color:#64748b; text-transform:capitalize;">${conv.role} #${conv.id}</div>
                        <div style="font-size:13px; color:#475569; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-top:4px;">
                            ${conv.last_message || 'No messages yet'}
                        </div>
                    </div>
                </div>
            `;

            li.addEventListener('click', () => loadConversation(conv));
            conversationsList.appendChild(li);
        });
    }

    function loadConversation(conv) {
        currentConversation = conv;
        
        // Update local state to clear unread count
        const found = allConversations.find(c => c.role === conv.role && c.id === conv.id);
        if (found) {
            found.unread_count = 0;
        }

        // Mark as read in database
        fetch('/api/chat2/mark_read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ peer_role: conv.role, peer_id: conv.id }),
            credentials: 'include'
        }).catch(e => console.error('Failed to mark conversation as read', e));

        // Join the specific room for this conversation to receive real-time updates
        joinConversationRoom(conv);
        
        // Update UI
        currentChatUserSpan.textContent = conv.name;
        // Check if currentChatRoleSpan exists before setting textContent
        if (currentChatRoleSpan) {
            currentChatRoleSpan.textContent = `${conv.role.charAt(0).toUpperCase() + conv.role.slice(1)} #${conv.id}`;
        }
        chatHeader.style.display = 'flex';
        chatInputArea.style.display = 'flex';
        chatMessages.innerHTML = '<div style="text-align:center; padding:20px; color:#94a3b8;">Loading messages...</div>';
        
        // Re-render list to show active state and clear badge
        const activeFilterBtn = document.querySelector('.filter-btn.active');
        renderConversations(activeFilterBtn ? activeFilterBtn.dataset.filter : 'all');

        // Fetch messages
        fetch(`/api/support/conversations/${conv.role}/${conv.id}/messages?role=admin`, { credentials: 'include' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    chatMessages.innerHTML = '';
                    data.messages.forEach(msg => {
                        const type = msg.sender_role === 'admin' ? 'sent' : 'received';
                        appendMessage(msg.message, type, msg.created_at);
                    });
                    scrollToBottom();
                }
            })
            .catch(error => {
                console.error('Error loading messages:', error);
                chatMessages.innerHTML = '<div style="text-align:center; color:red;">Error loading messages</div>';
            });
    }

    function appendMessage(text, type, timestamp) {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        
        if (type === 'sent') {
            div.style.alignSelf = 'flex-end';
            div.style.backgroundColor = '#ffffff';
            div.style.color = '#0f172a';
            div.style.border = '1px solid #0b73ff';
            div.style.padding = '8px 12px';
            div.style.borderRadius = '12px 12px 0 12px';
            div.style.maxWidth = '70%';
            div.style.marginBottom = '8px';
            div.style.fontSize = '14px';
        } else {
            div.style.alignSelf = 'flex-start';
            div.style.backgroundColor = '#f1f5f9';
            div.style.color = '#1e293b';
            div.style.padding = '8px 12px';
            div.style.borderRadius = '12px 12px 12px 0';
            div.style.maxWidth = '70%';
            div.style.marginBottom = '8px';
            div.style.fontSize = '14px';
        }

        div.innerHTML = `
            <div>${text}</div>
            <div style="font-size:10px; opacity:0.8; text-align:right; margin-top:4px;">${formatTime(timestamp)}</div>
        `;
        chatMessages.appendChild(div);
    }

    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text || !currentConversation) return;

        console.log('Sending admin message:', {
            role: currentConversation.role,
            id: currentConversation.id,
            message: text
        });

        if (socket && socket.connected) {
            socket.emit('admin_send_message', {
                role: currentConversation.role,
                id: currentConversation.id,
                admin_id: resolveAdminId(),
                message: text
            });
        }

        appendMessage(text, 'sent', new Date().toISOString());
        scrollToBottom();

        chatInput.value = '';
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function formatTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
});
