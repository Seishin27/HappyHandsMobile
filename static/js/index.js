  const searchBtn = document.getElementById('searchBtn');
  const searchBar = document.getElementById('searchBar');
  function filterFeaturedProducts(q){
    const grid = document.querySelector('.featured-products .products-grid');
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll('.product-card'));
    const query = String(q||'').toLowerCase().trim();
    let visible = 0;
    cards.forEach(card=>{
      const nameEl = card.querySelector('h3');
      const name = String(nameEl ? nameEl.textContent : '').toLowerCase();
      const ok = query === '' || name.includes(query);
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    // Removed "No matching products" message as requested
  }
  if (searchBtn && searchBar){
    searchBtn.addEventListener('click', function(e) {
      e.preventDefault();
      // If bar is already active and has text, treat click as "Go"
      if (searchBar.classList.contains('active') && searchBar.value.trim()) {
          window.location.href = '/search?q=' + encodeURIComponent(searchBar.value.trim());
          return;
      }
      
      searchBar.classList.toggle('active');
      if (searchBar.classList.contains('active')) {
        searchBar.focus();
      } else {
        searchBar.value = '';
        filterFeaturedProducts('');
      }
    });
    searchBar.addEventListener('input', function(){
      filterFeaturedProducts(searchBar.value);
    });
    searchBar.addEventListener('keydown', function(ev){
      if (ev.key === 'Enter') {
          ev.preventDefault();
          const q = searchBar.value.trim();
          if (q) {
              // If we are on the home page, we might want to just filter featured products
              // But if the user wants to search ALL products, we should go to search page
              // The user requested "no refresh", which implies AJAX search.
              // Since index.js is for the home page, let's keep the redirect for now
              // unless we want to implement full AJAX search on home page too.
              // However, the user specifically complained about "page refreshed" when searching.
              // So let's try to use the same AJAX search logic if possible, but index.js
              // doesn't have the product grid structure of category pages.
              // For now, let's keep the redirect on Home Page as it's the standard behavior
              // unless the user explicitly asks for Home Page AJAX search replacement.
              // Wait, the user said "when the user search a product, the page refreshed. make sure it does not refresh."
              // This likely applies to the category pages where I just fixed it.
              // On the home page, filtering is already client-side (no refresh) for featured products.
              // But if they hit Enter, it redirects.
              // Let's leave the redirect here for now as Home Page usually leads to a Search Results page.
              window.location.href = '/search?q=' + encodeURIComponent(q);
          }
      }
      if (ev.key === 'Escape'){ searchBar.value = ''; filterFeaturedProducts(''); }
    });
  }
  
    // --- Search suggestions dropdown ---
    (function setupSearchSuggestions(){
        try{
            const SUG_ID = 'searchSuggestions';
            // inject minimal styles for the dropdown
            const css = `
                #${SUG_ID} { position: absolute; z-index: 9999; background:#fff;border:1px solid #e6eef8;border-radius:8px;box-shadow:0 8px 24px rgba(16,24,40,0.08); max-height:320px; overflow:auto; width:320px; }
                #${SUG_ID} .s-item { display:flex; gap:8px; align-items:center; padding:8px 10px; cursor:pointer; border-bottom:1px solid #f1f5f9; }
                #${SUG_ID} .s-item:last-child{ border-bottom:0; }
                #${SUG_ID} .s-item:hover, #${SUG_ID} .s-item.active { background:#f8fafc; }
                #${SUG_ID} .s-thumb { width:44px;height:44px;border-radius:6px;object-fit:cover;background:#f3f4f6;flex:0 0 44px;display:flex;align-items:center;justify-content:center;color:#64748b;font-weight:700 }
                #${SUG_ID} .s-title { font-weight:600; color:#0f1724; }
                #${SUG_ID} .s-sub { font-size:13px; color:#64748b; }
            `;
            if (!document.querySelector('style[data-generated="search-suggestions-styles"]')){
                const s = document.createElement('style'); s.setAttribute('data-generated','search-suggestions-styles'); s.appendChild(document.createTextNode(css)); document.head.appendChild(s);
            }

            // create container
            let suggestions = document.getElementById(SUG_ID);
            if (!suggestions){
                suggestions = document.createElement('div'); suggestions.id = SUG_ID; suggestions.style.display = 'none'; document.body.appendChild(suggestions);
            }

            // helper: find potential category input/select on page
            function getCategoryValue(){
                const ids = ['productCategory','categorySelect','searchCategory','filterCategory'];
                for (const id of ids){ const el = document.getElementById(id); if (el && (el.tagName==='SELECT' || el.tagName==='INPUT')) return el.value || null; }
                // fallback: any element with data-search-category
                const el = document.querySelector('[data-search-category]'); if (el) return el.value || el.getAttribute('data-search-category') || null;
                return null;
            }

            // collect product candidates from DOM product cards
            function collectProducts(){
                const cards = Array.from(document.querySelectorAll('.product-card'));
                return cards.map(card=>{
                    const id = card.getAttribute('data-product-id') || card.dataset.productId || null;
                    const titleEl = card.querySelector('h3') || card.querySelector('.product-title');
                    const title = titleEl ? String(titleEl.textContent || titleEl.innerText || '').trim() : '';
                    const imgEl = card.querySelector('img') || null;
                    const img = imgEl ? (imgEl.getAttribute('src') || imgEl.dataset.src || '') : '';
                    const category = card.getAttribute('data-category') || card.dataset.category || null;
                    const url = id ? ('/product/' + id) : (card.querySelector('a') ? card.querySelector('a').href : '#');
                    return { id, title, img, category, url };
                }).filter(p=>p.title);
            }

            // simple debounce
            function debounce(fn, ms){ let t=null; return function(...a){ clearTimeout(t); t=setTimeout(()=>fn.apply(this,a), ms); }; }

            let currentIndex = -1;
            function renderSuggestions(list, anchorRect){
                if (!suggestions) return;
                suggestions.innerHTML = '';
                if (!list || !list.length){ suggestions.style.display = 'none'; return; }
                // position dropdown under searchBar
                const rect = anchorRect || (searchBar && searchBar.getBoundingClientRect());
                if (rect){ suggestions.style.width = Math.max(280, rect.width) + 'px'; suggestions.style.left = (rect.left + window.scrollX) + 'px'; suggestions.style.top = (rect.bottom + window.scrollY + 6) + 'px'; }

                list.forEach((p, idx)=>{
                    const el = document.createElement('div'); el.className = 's-item'; el.setAttribute('data-idx', idx);
                    const thumb = document.createElement('div'); thumb.className = 's-thumb';
                    if (p.img) { const im = document.createElement('img'); im.src = p.img; im.style.width='100%'; im.style.height='100%'; im.style.objectFit='cover'; im.style.borderRadius='6px'; thumb.appendChild(im); } else { thumb.textContent = (p.title||'').charAt(0).toUpperCase(); }
                    const txt = document.createElement('div'); txt.style.flex='1';
                    const t = document.createElement('div'); t.className = 's-title'; t.textContent = p.title;
                    const s = document.createElement('div'); s.className = 's-sub'; s.textContent = p.category ? String(p.category) : p.url || '';
                    txt.appendChild(t); txt.appendChild(s);
                    el.appendChild(thumb); el.appendChild(txt);
                    el.addEventListener('click', ()=>{ if (p.url && p.url !== '#') window.location.href = p.url; else if (p.id) window.location.href = '/product/' + p.id; else { /* nothing */ } });
                    suggestions.appendChild(el);
                });
                currentIndex = -1;
                suggestions.style.display = 'block';
            }

            function hideSuggestions(){ if (suggestions) suggestions.style.display = 'none'; currentIndex = -1; }

              async function updateSuggestions(){
                        const q = (searchBar && String(searchBar.value||'').trim()) || '';
                        const cat = getCategoryValue();
                        // If query is empty, don't show suggestions
                        if (!q) { renderSuggestions([]); return; }

                        // Call server-side search to cover all categories and products
                        try{
                            const params = new URLSearchParams();
                            params.set('q', q);
                            if (cat) params.set('category', cat);
                            const r = await fetch('/api/products/search?' + params.toString(), { credentials: 'same-origin' });
                            if (!r.ok) { renderSuggestions([]); return; }
                            const j = await r.json().catch(()=>null);
                            if (!j || !j.success || !Array.isArray(j.products)) { renderSuggestions([]); return; }
                            const results = (j.products || []).slice(0, 8).map(p=>({ id: p.productID, title: p.name, img: p.image, category: p.category, url: p.url }));
                            renderSuggestions(results);
                        }catch(e){ console.error('search API failed', e); renderSuggestions([]); }
                    }

            const debouncedUpdate = debounce(updateSuggestions, 160);

            // wire events
            searchBar.addEventListener('input', function(){ debouncedUpdate(); });
            searchBar.addEventListener('focus', function(){ debouncedUpdate(); });
            searchBar.addEventListener('keydown', function(ev){
                if (!suggestions || suggestions.style.display === 'none') return;
                const items = suggestions.querySelectorAll('.s-item');
                if (!items || !items.length) return;
                if (ev.key === 'ArrowDown'){ ev.preventDefault(); currentIndex = Math.min(currentIndex+1, items.length-1); items.forEach(i=>i.classList.remove('active')); items[currentIndex].classList.add('active'); items[currentIndex].scrollIntoView({block:'nearest'}); }
                else if (ev.key === 'ArrowUp'){ ev.preventDefault(); currentIndex = Math.max(currentIndex-1, 0); items.forEach(i=>i.classList.remove('active')); items[currentIndex].classList.add('active'); items[currentIndex].scrollIntoView({block:'nearest'}); }
                else if (ev.key === 'Enter'){ ev.preventDefault(); if (currentIndex >=0 && items[currentIndex]) items[currentIndex].click(); }
                else if (ev.key === 'Escape'){ hideSuggestions(); }
            });

            // hide when clicking outside
            document.addEventListener('click', function(ev){ if (!searchBar.contains(ev.target) && !suggestions.contains(ev.target)) hideSuggestions(); });

            // if there's a category select, update on change
            ['productCategory','categorySelect','searchCategory','filterCategory'].forEach(id=>{ const el = document.getElementById(id); if (el) el.addEventListener('change', ()=>{ debouncedUpdate(); }); });

        }catch(e){ console.error('setupSearchSuggestions', e); }
    })();
    // Inject user chat bubble styles so user chat matches seller chat appearance
    (function injectUserChatStyles(){
        try{
            const css = `
                /* User chat bubbles */
                .user-bubble { background:#ffffff; color:#0f1724; align-self:flex-end; border: 1px solid #0b73ff; }
                .seller-bubble { background:#ffffff; color:#0f1724; align-self:flex-start; border: 1px solid #cbd5e1; }
                #userChatMessages { padding:12px; background:#fbfdff; display:flex; flex-direction:column; gap:8px; overflow:auto; }
                #userChatsOverlay > div { border-radius:12px; overflow:hidden; }
            `;
            const s = document.createElement('style'); s.setAttribute('data-generated','user-chat-styles'); s.appendChild(document.createTextNode(css));
            document.head.appendChild(s);
        }catch(e){ console.error('injectUserChatStyles', e); }
    })();
    // Cart button logic - redirect to cart page
    const cartBtn = document.getElementById('cartBtn');
    if (cartBtn) {
        cartBtn.addEventListener('click', () => {
            window.location.href = '/cart';
        });
    }
    
        // Categories dropdown logic
        const categoriesDropdown = document.getElementById('categoriesDropdown');
        const categoriesMenu = document.getElementById('categoriesMenu');
        if (categoriesDropdown && categoriesMenu) {
            const toggleBtn = categoriesDropdown.querySelector('.dropdown-toggle');
            toggleBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                const isOpen = categoriesDropdown.classList.toggle('open');
                toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            });
            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!categoriesDropdown.contains(e.target)) {
                    categoriesDropdown.classList.remove('open');
                    toggleBtn.setAttribute('aria-expanded', 'false');
                }
            });
            // Optional: close dropdown when a category is clicked
            Array.from(categoriesMenu.querySelectorAll('.dropdown-item')).forEach(function(item) {
                item.addEventListener('click', function() {
                    categoriesDropdown.classList.remove('open');
                    toggleBtn.setAttribute('aria-expanded', 'false');
                });
            });
        }

    // User dropdown logic (account avatar + menu)
    const ActBtn = document.getElementById('ActBtn');
    const userDropdown = document.getElementById('userDropdown');
    
    if (ActBtn) {
        const loggedIn = ActBtn.getAttribute('data-logged-in') === '1';
        
        if (loggedIn && userDropdown) {
            // Handle dropdown for logged-in users
            ActBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                userDropdown.classList.toggle('show');
            });
            
            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!ActBtn.contains(e.target) && !userDropdown.contains(e.target)) {
                    userDropdown.classList.remove('show');
                }
            });

            // Messages item inside dropdown opens existing chat overlay
            const dropdownMessages = document.querySelector('.dropdown-messages');
            if (dropdownMessages) {
                dropdownMessages.addEventListener('click', function(ev) {
                    ev.preventDefault();
                    const chatBtn = document.getElementById('userChatBtn');
                    if (chatBtn) {
                        chatBtn.click();
                    }
                    userDropdown.classList.remove('show');
                });
            }

            // Avatar image fallback: if the image fails, hide it and rely on the initial/gradient
            const avatarImgs = document.querySelectorAll('.account-avatar-img');
            avatarImgs.forEach(function(img) {
                img.addEventListener('error', function() {
                    img.style.display = 'none';
                });
            });
        } else {
            // Handle click for non-logged-in users
            ActBtn.addEventListener('click', () => {
                window.location.href = '/login';
            });
        }
    }
    
    // Logout function (improved for better debugging and user feedback)
    async function handleLogout() {
        try {
            const response = await fetch('/logout', {
                method: 'POST',
                // If your frontend and backend are served from the same origin this is fine;
                // if you use a different origin for API, change this to 'include'.
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            // Try to parse JSON response if any
            let data = null;
            try {
                data = await response.json();
            } catch (e) {
                // no JSON body
            }

            if (!response.ok) {
                console.error('Logout failed:', response.status, data);
                // Pick a friendly message from JSON if present
                const serverMsg = data && (data.msg || data.message || data.error) ? (data.msg || data.message || data.error) : `Status ${response.status}`;
                alert('Logout failed: ' + serverMsg + '\nSee console for details.');
                return;
            }

            // Success: redirect
            window.location.href = '/';
        } catch (err) {
            console.error('Logout error (network):', err);
            alert('Logout failed: network error. See console for details.');
        }
    }


// ------------------
// Notifications (polling)
// ------------------
const notificationBtn = document.getElementById('notificationBtn');
const notificationMenu = document.getElementById('notificationMenu');
const notificationList = document.getElementById('notificationList');
const notifCountEl = document.querySelector('.notif-count');
const bodyEl = document.body || document.querySelector('body');
const isUserLoggedIn = Boolean(bodyEl && bodyEl.dataset && bodyEl.dataset.userId);

function escapeHtml(value) {
    const str = value == null ? '' : String(value);
    return str.replace(/[&<>"']/g, function (match) {
        switch (match) {
            case '&': return '&amp;';
            case '<': return '&lt;';
            case '>': return '&gt;';
            case '"': return '&quot;';
            case "'": return '&#39;';
            default: return match;
        }
    });
}

function formatNotificationTimestamp(value) {
    if (!value) return '';
    try {
        const date = new Date(value);
        if (!Number.isNaN(date.valueOf())) {
            return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        }
    } catch (e) {}
    const raw = String(value);
    return raw.length > 19 ? raw.slice(0, 19) : raw;
}

async function fetchNotifications() {
    if (!isUserLoggedIn) {
        return { chat: [], system: [] };
    }
    try {
        const r = await fetch('/api/notifications', { credentials: 'same-origin' });
        if (!r.ok) return { chat: [], system: [] };
        const j = await r.json();
        if (!j.success) return { chat: [], system: [] };
        return {
            chat: j.notifications || [],
            system: j.system_notifications || []
        };
    } catch (e) {
        return { chat: [], system: [] };
    }
}

function renderNotifications(payload) {
    if (!notificationList) return;

    const chatItems = payload && Array.isArray(payload.chat) ? payload.chat : (Array.isArray(payload) ? payload : []);
    const systemItems = (payload && Array.isArray(payload.system)) ? payload.system : [];

    if ((!chatItems || !chatItems.length) && (!systemItems || !systemItems.length)) {
        notificationList.innerHTML = '<div class="notif-empty">No notifications</div>';
        if (notifCountEl) { notifCountEl.style.display = 'none'; notifCountEl.textContent = '0'; }
        return;
    }

    const parts = [];

    // System notifications section (order updates, back-in-stock, etc.)
    if (systemItems && systemItems.length) {
        parts.push('<div class="notif-section-title">Updates</div>');
        systemItems.forEach(n => {
            const rows = ['<div class="notif-card">'];
            const title = escapeHtml(n.title || 'Notification');
            rows.push('<div class="notif-card-title">' + title + '</div>');
            if (n.body) {
                rows.push('<div class="notif-card-body">' + escapeHtml(n.body) + '</div>');
            }
            const metaPieces = [];
            const ts = formatNotificationTimestamp(n.created_at);
            if (ts) metaPieces.push(escapeHtml(ts));
            if (metaPieces.length) {
                rows.push('<div class="notif-card-meta">' + metaPieces.join(' &bull; ') + '</div>');
            }
            rows.push('</div>');
            parts.push(rows.join(''));
        });
    }

    // Chat notifications section
    if (chatItems && chatItems.length) {
        parts.push('<div class="notif-section-title">Messages</div>');
        chatItems.forEach(n => {
            const productId = n.productID || '';
            const sellerId = n.sellerID || '';
            const href = '/product/' + encodeURIComponent(productId) + '?open_chat=1&seller_id=' + encodeURIComponent(sellerId) + '&product_id=' + encodeURIComponent(productId);
            const rows = ['<a class="notif-card notif-card-link" href="' + escapeHtml(href) + '">'];
            const sellerName = n.sellerName || ('Seller ' + sellerId);
            rows.push('<div class="notif-card-title">' + escapeHtml(sellerName) + '</div>');
            if (n.lastMessage) {
                rows.push('<div class="notif-card-body">' + escapeHtml(n.lastMessage) + '</div>');
            }
            const metaPieces = [];
            const unread = Number(n.unreadCount || 0);
            if (unread) {
                const unreadLabel = unread === 1 ? '1 unread' : unread + ' unread';
                metaPieces.push(escapeHtml(unreadLabel));
            }
            const ts = formatNotificationTimestamp(n.lastMessageAt || n.created_at);
            if (ts) metaPieces.push(escapeHtml(ts));
            if (metaPieces.length) {
                rows.push('<div class="notif-card-meta">' + metaPieces.join(' &bull; ') + '</div>');
            }
            rows.push('</a>');
            parts.push(rows.join(''));
        });
    }

    notificationList.innerHTML = parts.join('');

    // Keep badge behavior based on chat unread count to preserve existing semantics
    let totalUnread = 0;
    (chatItems || []).forEach(n => { totalUnread += (n.unreadCount || 0); });
    if (notifCountEl) { notifCountEl.style.display = totalUnread ? 'inline-flex' : 'none'; notifCountEl.textContent = String(totalUnread || 0); }
}

let notifPollTimer = null;
async function startNotifPolling(intervalMs = 8000) {
    try {
        const payload = await fetchNotifications();
        renderNotifications(payload);
    } catch (e) {}
    if (notifPollTimer) clearTimeout(notifPollTimer);
    notifPollTimer = setTimeout(() => startNotifPolling(intervalMs), intervalMs);
}

if (notificationBtn) {
    notificationBtn.addEventListener('click', function (e) {
        e.preventDefault();
        if (!notificationMenu) return;
        const isOpen = notificationMenu.style.display === 'block';
        notificationMenu.style.display = isOpen ? 'none' : 'block';
    });
    // close when clicking outside
    document.addEventListener('click', function (e) {
        if (!notificationMenu) return;
        if (!notificationBtn.contains(e.target) && !notificationMenu.contains(e.target)) {
            notificationMenu.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    // start polling for notifications only when logged in
    if (isUserLoggedIn) {
        try { startNotifPolling(8000); } catch (e) {}
    }
    // clear notifs button
    const clearBtn = document.getElementById('clearNotifs');
    if (clearBtn && isUserLoggedIn) {
        clearBtn.addEventListener('click', async function (ev) {
            ev.preventDefault();
            try {
                await fetch('/api/notifications/mark_read', { method: 'POST', credentials: 'same-origin' });
                // refresh list
                const items = await fetchNotifications();
                renderNotifications(items);
            } catch (e) { console.error('Failed to mark notifications read', e); }
        });
    }
});

// ------------------
// Additional site behaviors moved from inline scripts in index.html
// - Hero carousel
// - Debug logs & product-card checks
// - showLoginPrompt helper
// - Server flashes JSON parsing
// - User chat (socket) wiring (reads USER ID from body data attribute)
// ------------------

(function(){
    function qs(sel, ctx){ return (ctx||document).querySelector(sel); }
    function qsa(sel, ctx){ return Array.from((ctx||document).querySelectorAll(sel)); }

    // Parse server flashes from the JSON script tag (if present)
    try {
        const sf = document.getElementById('server-flashes');
        window.__server_flashes = sf ? JSON.parse(sf.textContent || '[]') : [];
    } catch (e) {
        window.__server_flashes = [];
    }

    // Debug helpers
    try { console.log('Cart object:', window.cart); } catch(e){}
    document.addEventListener('DOMContentLoaded', function(){
        try{
            const productCards = document.querySelectorAll('.product-card');
            console.log('Product cards found:', productCards.length);
            productCards.forEach((card, index) => {
                const productId = card.getAttribute('data-product-id');
                console.log(`Card ${index}: productId = ${productId}`);
            });
        }catch(e){}
    });

    // showLoginPrompt exported so other modules can call it
    window.showLoginPrompt = async function showLoginPrompt(){
        try{
            var ok = false;
            if (window.confirmAction) {
                ok = await window.confirmAction({ title: 'You need to log in to add items to your cart.', text: 'Would you like to go to the login page?', icon: 'question', confirmButtonText: 'Login', cancelButtonText: 'Cancel' });
            } else {
                ok = window.confirm('You need to log in to add items to your cart. Would you like to go to the login page?');
            }
            if (ok) window.location.href = '/login';
        }catch(e){ if (window.confirm('You need to log in to add items to your cart. Would you like to go to the login page?')) window.location.href = '/login'; }
    };

    // Hero carousel behavior
    document.addEventListener('DOMContentLoaded', function(){
        const carousel = qs('#heroCarousel');
        if (!carousel) return;
        const slides = qsa('.hero-slide', carousel);
        const dots = qsa('.hero-dot', carousel);
        const prev = qs('#heroPrev');
        const next = qs('#heroNext');
        let index = 0;
        let autoplay = true;
        let timer = null;

        function show(i){
            slides.forEach(s=>s.classList.remove('active'));
            dots.forEach(d=>d.classList.remove('active'));
            const s = slides[i]; if (!s) return;
            s.classList.add('active');
            const d = dots[i]; if (d) d.classList.add('active');
            index = i;
        }

        function nextSlide(){ show((index+1) % slides.length); }
        function prevSlide(){ show((index-1+slides.length) % slides.length); }

        if (next) next.addEventListener('click', (e)=>{ e.stopPropagation(); autoplay=false; nextSlide(); resetTimer(); });
        if (prev) prev.addEventListener('click', (e)=>{ e.stopPropagation(); autoplay=false; prevSlide(); resetTimer(); });
        dots.forEach(d=> d.addEventListener('click', (e)=>{ const i = Number(d.dataset.index||0); autoplay=false; show(i); resetTimer(); }));

        function resetTimer(){ if (timer) clearInterval(timer); if (autoplay) timer = setInterval(nextSlide, 5000); }
        resetTimer();

        carousel.addEventListener('mouseenter', ()=>{ autoplay=false; resetTimer(); });
        carousel.addEventListener('mouseleave', ()=>{ autoplay=true; resetTimer(); });

        // touch support
        let startX = null;
        carousel.addEventListener('touchstart', (ev)=>{ startX = ev.touches[0].clientX; }, {passive:true});
        carousel.addEventListener('touchend', (ev)=>{ if (startX==null) return; const dx = (ev.changedTouches[0].clientX - startX); if (Math.abs(dx) > 40){ if (dx < 0) nextSlide(); else prevSlide(); } startX = null; resetTimer(); }, {passive:true});
    });

    // Wire logout buttons (removed inline onclick handlers in template)
    try{
        document.querySelectorAll('.logout-btn').forEach(btn => btn.addEventListener('click', function(ev){ ev.preventDefault(); if (typeof handleLogout === 'function') handleLogout(); else console.warn('handleLogout not defined'); }));
    }catch(e){}

    // User chat wiring using new ChatUI + /api/chat2 backend. Reads USER ID from body data attribute.
    (function(){
        const USER_ID = (document.body && document.body.dataset && document.body.dataset.userId) ? document.body.dataset.userId : null;
        if (!USER_ID) return; // only wire for logged-in users

        function openUserChats(){
            const overlay = document.getElementById('userChatsOverlay');
            if (overlay) overlay.style.display = 'flex';
        }

        function closeUserChats(){
            const overlay = document.getElementById('userChatsOverlay');
            if (overlay) overlay.style.display = 'none';
            const msgs = document.getElementById('userChatMessages');
            if (msgs) msgs.innerHTML = '';
        }

        async function loadUserConversations(){
            const listEl = document.getElementById('userConvoItems');
            if (!listEl) return;
            listEl.innerHTML = '<div style="padding:12px;color:#64748b;">Loading…</div>';
            try{
                const r = await fetch('/api/chat2/conversations?limit=50', { credentials: 'same-origin' });
                const j = await r.json().catch(()=>null);
                if (!r.ok || !j || !j.success){
                    listEl.innerHTML = '<div style="padding:12px;color:#64748b;">No conversations</div>';
                    return;
                }
                const items = j.items || [];
                if (!items.length){
                    listEl.innerHTML = '<div style="padding:12px;color:#64748b;">No conversations</div>';
                    return;
                }
                listEl.innerHTML = items.map(function(c){
                    const role = c.peer_role || '';
                    const id = c.peer_id;
                    const labelBase = (role === 'seller')
                        ? 'Seller ' + id
                        : (role === 'rider')
                            ? 'Rider ' + id
                            : (role === 'admin')
                                ? 'Admin ' + id
                                : 'User ' + id;
                    const initials = String(labelBase).charAt(0).toUpperCase();
                    const last = (c.lastMessage || '').slice(0,60);
                    const unread = c.unreadCount || 0;
                    const badgeText = unread > 0 ? String(unread) : '';
                    const badgeDisplay = unread > 0 ? '' : 'display:none;';
                    return '<button class="convoItem" data-chat-peer-role="'+role+'" data-chat-peer-id="'+id+'" style="display:flex;gap:10px;align-items:center;padding:10px;border-radius:8px;border:0;background:transparent;width:100%;text-align:left;position:relative;">'
                        + '<div class="avatar">'+initials+'</div>'
                        + '<div style="flex:1"><div style="font-weight:600">'+labelBase+'</div><div class="convo-meta">'+last+'</div></div>'
                        + '<span class="unread-badge" data-chat-unread style="'+badgeDisplay+'">'+badgeText+'</span>'
                        + '</button>';
                }).join('');

                const convoButtons = listEl.querySelectorAll('.convoItem');
                convoButtons.forEach(function(btn){
                    btn.addEventListener('click', function(){
                        const role = btn.getAttribute('data-chat-peer-role');
                        const id = btn.getAttribute('data-chat-peer-id');
                        if (window.ChatUI && role && id){
                            window.ChatUI.openOverlayFor(role, id);
                            if (typeof window.ChatUI.refreshUnread === 'function'){
                                window.ChatUI.refreshUnread();
                            }
                        }
                        const badge = btn.querySelector('[data-chat-unread]');
                        if (badge){
                            badge.textContent = '';
                            badge.style.display = 'none';
                        }
                    });
                });
            }catch(e){
                console.error('loadUserConversations', e);
                listEl.innerHTML = '<div style="padding:12px;color:#64748b;">Failed to load</div>';
            }
        }

        document.addEventListener('DOMContentLoaded', function(){
            if (window.ChatUI){
                try{
                    window.ChatUI.init('user', USER_ID, null);
                }catch(e){ console.error('ChatUI.init failed', e); }
            }

            const btn = document.getElementById('userChatBtn');
            if (btn) {
                btn.addEventListener('click', async function(e){
                    e.preventDefault();
                    openUserChats();
                    await loadUserConversations();
                });
            }

            const closeBtn = document.getElementById('userChatClose');
            if (closeBtn){
                closeBtn.addEventListener('click', closeUserChats);
            }
            const overlay = document.getElementById('userChatsOverlay');
            if (overlay){
                overlay.addEventListener('click', function(ev){ if (ev.target.id === 'userChatsOverlay') closeUserChats(); });
            }
        });
    })();

})();

// Product Image Hover Cycle
function initHoverCycleImages(scope) {
    const root = scope || document;
    const cycleImages = root.querySelectorAll('.hover-cycle');

    const toImageUrl = (value) => {
        const trimmed = (value || '').trim();
        if (!trimmed) return '';
        if (/^(https?:)?\/\//i.test(trimmed) || trimmed.startsWith('data:')) {
            return trimmed;
        }
        return '/uploads/' + trimmed.replace(/^\/+/, '');
    };

    cycleImages.forEach(img => {
        if (img.dataset.cycleBound === '1') return;
        img.dataset.cycleBound = '1';

        const imagesAttr = img.getAttribute('data-images') || '';
        const rawImages = imagesAttr.split(',').map(s => s.trim()).filter(Boolean);
        if (!rawImages.length) return;

        const normalizedImages = rawImages.map(toImageUrl).filter(Boolean);
        if (!normalizedImages.length) return;

        let interval = null;
        let currentIndex = 0;
        const originalSrc = normalizedImages[0];
        img.src = originalSrc;

        normalizedImages.forEach(src => {
            const i = new Image();
            i.src = src;
        });

        if (normalizedImages.length === 1) {
            return;
        }

        const container = img.closest('.featured-image') || img.parentElement;
        if (!container) return;

        container.addEventListener('mouseenter', function() {
            if (interval) clearInterval(interval);
            interval = setInterval(() => {
                currentIndex = (currentIndex + 1) % normalizedImages.length;
                img.src = normalizedImages[currentIndex];
            }, 1000);
        });

        container.addEventListener('mouseleave', function() {
            if (interval) clearInterval(interval);
            interval = null;
            currentIndex = 0;
            img.src = originalSrc;
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initHoverCycleImages(document);
});


(function initFeaturedPagination(){
    const section = document.getElementById('featuredProducts');
    if (!section) return;
    const grid = section.querySelector('[data-role="grid"]');
    const pagination = section.querySelector('[data-role="pagination"]');
    const countEl = section.querySelector('[data-role="count"]');
    const statusEl = section.querySelector('[data-role="status"]');
    const endpoint = section.dataset.productsEndpoint;
    const homeUrl = section.dataset.homeUrl || '/';
    if (!grid || !endpoint) return;
    let isLoading = false;

    const safeText = (typeof escapeHtml === 'function')
        ? escapeHtml
        : (value => String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;'));

    const defaultEmptyMarkup = '<p class="featured-empty" data-role="empty">No products available yet.</p>';

    function buildPageHref(page){
        const base = homeUrl || window.location.pathname || '/';
        try {
            const url = new URL(base, window.location.origin);
            url.searchParams.set('page', page);
            url.hash = 'featuredProducts';
            return url.pathname + url.search + url.hash;
        } catch (err) {
            return base + '?page=' + encodeURIComponent(page) + '#featuredProducts';
        }
    }

    function formatPrice(value){
        if (value === null || value === undefined || value === '') {
            return '₱—';
        }
        const num = Number(value);
        if (!Number.isNaN(num)) {
            return '₱' + num.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        return '₱' + value;
    }

    function setStatus(message, isError){
        if (!statusEl) return;
        if (!message) {
            statusEl.textContent = '';
            statusEl.hidden = true;
            statusEl.classList.remove('error');
            return;
        }
        statusEl.textContent = message;
        statusEl.hidden = false;
        statusEl.classList.toggle('error', Boolean(isError));
    }

    function normalizeImages(images){
        if (!Array.isArray(images) || !images.length) return '';
        return images.map((img) => String(img || '').trim()).filter(Boolean).join(',');
    }

    function renderProducts(items){
        if (!items || !items.length) {
            grid.innerHTML = defaultEmptyMarkup;
            return;
        }

        const cards = items.map((item) => {
            const id = item.id;
            const name = safeText(item.name || 'Product');
            const price = formatPrice(item.price);
            const stock = (item.stock === null || item.stock === undefined || item.stock === '') ? '—' : safeText(item.stock);
            const detailUrl = safeText(item.detail_url || ('/product/' + id));
            const imageUrl = safeText(item.image_url || '');
            const imagesAttr = normalizeImages(item.images);
            return (
                '<div class="product-card" data-product-id="' + safeText(id) + '">' +
                    '<a href="' + detailUrl + '" class="product-link" title="' + name + '">' +
                        '<div class="featured-image">' +
                            '<img src="' + imageUrl + '" alt="' + name + '" class="hover-cycle" data-images="' + imagesAttr + '">' +
                        '</div>' +
                        '<h3>' + name + '</h3>' +
                        '<p class="product-price">' + price + '</p>' +
                        '<p class="product-stock">Stock: ' + stock + '</p>' +
                    '</a>' +
                '</div>'
            );
        }).join('');

        grid.innerHTML = cards;
        initHoverCycleImages(grid);
    }

    function updateCount(meta, renderedCount){
        if (!countEl) return;
        if (!renderedCount) {
            countEl.style.display = 'none';
            return;
        }
        const page = Number(meta.page || section.dataset.currentPage || 1);
        const size = Number(meta.page_size || meta.pageSize || section.dataset.pageSize || 12);
        const total = Number(meta.total_products || meta.totalProducts || section.dataset.totalItems || renderedCount);
        const start = ((page - 1) * size) + 1;
        const end = start + renderedCount - 1;
        countEl.textContent = 'Showing ' + start + '-' + end + ' of ' + total + ' products';
        countEl.style.display = '';
    }

    function rebuildPageNumbers(totalPages, currentPage){
        const fragments = [];
        for (let page = 1; page <= totalPages; page += 1) {
            if (page === currentPage) {
                fragments.push('<span class="page-number active" data-page="' + page + '" aria-current="page">' + page + '</span>');
            } else {
                fragments.push('<a class="page-number" data-page="' + page + '" href="' + buildPageHref(page) + '">' + page + '</a>');
            }
        }
        return fragments.join('');
    }

    function updatePagination(meta){
        if (!pagination) return;
        const totalPages = Number(meta.total_pages || meta.totalPages || section.dataset.totalPages || 1);
        if (totalPages <= 1) {
            pagination.style.display = 'none';
            return;
        }
        pagination.style.display = '';
        const currentPage = Number(meta.page || section.dataset.currentPage || 1);
        const prevBtn = pagination.querySelector('[data-role="prev"]');
        const nextBtn = pagination.querySelector('[data-role="next"]');
        const numbersContainer = pagination.querySelector('.page-numbers');
        const prevTarget = Math.max(1, currentPage - 1);
        const nextTarget = Math.min(totalPages, currentPage + 1);

        if (prevBtn) {
            prevBtn.dataset.page = String(prevTarget);
            prevBtn.href = buildPageHref(prevTarget);
            if (currentPage <= 1) {
                prevBtn.classList.add('disabled');
                prevBtn.setAttribute('aria-disabled', 'true');
            } else {
                prevBtn.classList.remove('disabled');
                prevBtn.removeAttribute('aria-disabled');
            }
        }

        if (nextBtn) {
            nextBtn.dataset.page = String(nextTarget);
            nextBtn.href = buildPageHref(nextTarget);
            if (currentPage >= totalPages) {
                nextBtn.classList.add('disabled');
                nextBtn.setAttribute('aria-disabled', 'true');
            } else {
                nextBtn.classList.remove('disabled');
                nextBtn.removeAttribute('aria-disabled');
            }
        }

        if (numbersContainer) {
            numbersContainer.innerHTML = rebuildPageNumbers(totalPages, currentPage);
        }
    }

    async function fetchPage(page){
        if (!endpoint || isLoading) return;
        isLoading = true;
        section.classList.add('is-loading');
        setStatus('Loading products…');
        try {
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('page', page);
            const resp = await fetch(url.toString(), { credentials: 'same-origin' });
            if (!resp.ok) throw new Error('request_failed');
            const data = await resp.json();
            if (!data || data.success === false) throw new Error('invalid_payload');

            // Normalize API response: handle both nested (data.data.items) and flat (data.products) structures
            const payload = (data.data && typeof data.data === 'object') ? data.data : data;
            const items = Array.isArray(payload.items) ? payload.items
                        : Array.isArray(payload.products) ? payload.products
                        : [];

            // Extract metadata with proper fallbacks
            const meta = {
                page:           payload.page           || page || 1,
                total_pages:    payload.total_pages    || payload.totalPages    || 1,
                total_products: payload.total_products || payload.totalProducts || items.length,
                page_size:      payload.page_size      || payload.pageSize      || 12,
            };

            renderProducts(items);
            updateCount(meta, items.length);
            updatePagination(meta);

            section.dataset.currentPage = String(meta.page);
            section.dataset.totalPages = String(meta.total_pages);
            section.dataset.totalItems = String(meta.total_products);
            section.dataset.pageSize = String(meta.page_size);

            setStatus('');

            if (window.history && typeof window.history.replaceState === 'function') {
                const nextUrl = new URL(window.location.href);
                nextUrl.searchParams.set('page', meta.page);
                nextUrl.hash = 'featuredProducts';
                window.history.replaceState({}, '', nextUrl.toString());
            }
        } catch (err) {
            console.error('Failed to load featured products page', err);
            setStatus('Unable to load more products. Please try again.', true);
        } finally {
            section.classList.remove('is-loading');
            isLoading = false;
        }
    }

    section.addEventListener('click', function(evt){
        const link = evt.target.closest('.featured-pagination a');
        if (!link) return;
        const targetPage = Number(link.dataset.page || link.getAttribute('data-page'));
        if (!targetPage) return;
        if (link.classList.contains('disabled')) {
            evt.preventDefault();
            return;
        }
        const currentPage = Number(section.dataset.currentPage || 1);
        if (targetPage === currentPage) {
            evt.preventDefault();
            return;
        }
        evt.preventDefault();
        fetchPage(targetPage);
    });

    // Auto-load via AJAX if server-side rendering delivered no products
    const hasServerProducts = grid.querySelector('.product-card');
    if (!hasServerProducts) {
        const initialPage = parseInt(section.dataset.currentPage || '1', 10);
        fetchPage(initialPage || 1);
    }
})();

