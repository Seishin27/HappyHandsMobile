// Externalized rider dashboard JS
// This file was extracted from templates/rider/rider_dashboard.html

document.addEventListener('DOMContentLoaded', function() {
    const CHAT_READY_STATUSES = ['assigned_to_rider', 'on_the_way', 'delivered'];
    let currentRiderOrders = [];
    let messagesTabBootstrapped = false;
    const riderChatContacts = {
      sellers: new Map(),
      users: new Map()
    };

    function normalizeStatus(value){
      return String(value || '').toLowerCase().trim();
    }

    function shouldShowChatButtons(order){
      if (!order) return false;
      const status = normalizeStatus(order.status);
      if (status === 'assigned_to_rider'){
        return !!order.riderAccepted;
      }
      return CHAT_READY_STATUSES.includes(status);
    }

    function escapeAttr(val){
      return String(val || '').replace(/"/g, '&quot;');
    }

    function normalizeProductId(value){
      if (value === undefined || value === null) return null;
      const text = String(value).trim();
      if (!text) return null;
      return /^[0-9]+$/.test(text) ? text : null;
    }

    function getInitialForName(name, fallbackLetter){
      const source = (name || '').trim();
      if (source) return source.charAt(0).toUpperCase();
      return (fallbackLetter || '?').toUpperCase();
    }

    const pesoFormatter = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' });

    function formatCurrency(value){
      try {
        return pesoFormatter.format(typeof value === 'number' ? value : Number(value || 0));
      } catch (e){
        return '₱' + Number(value || 0).toFixed(2);
      }
    }

    function formatDateTime(value){
      if (!value) return '—';
      try{
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleString();
      }catch(e){
        return String(value);
      }
    }

    function setChartState(el, message){
      if (!el) return;
      if (!message){
        el.classList.add('hidden');
      } else {
        el.textContent = message;
        el.classList.remove('hidden');
      }
    }

    const dailyDeliveriesCanvas = document.getElementById('dailyDeliveriesChart');
    const dailyDeliveriesStateEl = document.getElementById('dailyDeliveriesState');
    let dailyDeliveriesChart = null;

    const acceptanceCanvas = document.getElementById('acceptanceOverviewChart');
    const acceptanceStateEl = document.getElementById('acceptanceOverviewState');
    let acceptanceOverviewChart = null;

    const recentDeliveriesBody = document.querySelector('#recentDeliveriesTable tbody');


    function setChatHeaderInfo(titleText, subtitleText){
      const titleEl = document.getElementById('riderChatHeaderTitle');
      const subEl = document.getElementById('riderChatHeaderSubtitle');
      if (titleEl) titleEl.textContent = titleText || 'Choose a conversation';
      if (subEl) subEl.textContent = subtitleText || 'Select a seller or user to start chatting';
    }

    function buildChatButtonsHTML({ userId, userName, orderId, sellerId, sellerName }){
      const buttons = [];
      if (sellerId){
        buttons.push(
          `<button type="button" class="btn btn-chat btn-chat-seller" data-seller-id="${sellerId}" data-seller-name="${escapeAttr(sellerName || '')}" data-product-id="${orderId || ''}">Chat Seller</button>`
        );
      }
      if (userId){
        buttons.push(
          `<button type="button" class="btn btn-chat btn-chat-user" data-user-id="${userId}" data-user-name="${escapeAttr(userName || '')}" data-product-id="${orderId || ''}">Chat Customer</button>`
        );
      }
      if (!buttons.length) return '';
      return `<div class="order-chat-actions">${buttons.join('')}</div>`;
    }

    function attachChatButtonHandlers(scope){
      const root = scope || document;
      root.querySelectorAll('.btn-chat-seller').forEach(btn => {
        if (btn.dataset.chatSellerBound === '1') return;
        btn.dataset.chatSellerBound = '1';
        btn.addEventListener('click', ()=>{
          const sellerId = btn.getAttribute('data-seller-id');
          if (!sellerId) return;
          const sellerName = btn.getAttribute('data-seller-name') || '';
          const productId = btn.getAttribute('data-product-id') || null;
          if (typeof window.openRiderSellerChatModal === 'function') {
            window.openRiderSellerChatModal(sellerId, sellerName || `Seller ${sellerId}`, productId);
          } else if (typeof window.openRiderChatWithSeller === 'function') {
            window.openRiderChatWithSeller(sellerId, sellerName || `Seller ${sellerId}`, productId);
          }
        });
      });
      root.querySelectorAll('.btn-chat-user').forEach(btn => {
        if (btn.dataset.chatBound === '1') return;
        btn.dataset.chatBound = '1';
        btn.addEventListener('click', ()=>{
          const userId = btn.getAttribute('data-user-id');
          if (!userId || typeof window.openRiderChatWithUser !== 'function') return;
          const userName = btn.getAttribute('data-user-name') || '';
          const productId = btn.getAttribute('data-product-id') || null;
          window.openRiderChatWithUser(userId, userName || `User ${userId}`, productId);
        });
      });
    }

    function bindChatTargetsDelegation(){
      const targetsEl = document.getElementById('riderChatTargets');
      if (!targetsEl || targetsEl.dataset.bound === '1') return;
      targetsEl.dataset.bound = '1';
      targetsEl.addEventListener('click', (event)=>{
        const btn = event.target.closest('.chat-target-icon');
        if (!btn) return;
        event.preventDefault();
        const type = btn.getAttribute('data-type');
        const id = btn.getAttribute('data-id');
        const name = btn.getAttribute('data-name') || '';
        const productId = btn.getAttribute('data-product-id') || null;
        if (type === 'seller' && typeof window.openRiderChatWithSeller === 'function'){
          window.openRiderChatWithSeller(id, name || `Seller ${id}`, productId);
        } else if (type === 'user' && typeof window.openRiderChatWithUser === 'function'){
          window.openRiderChatWithUser(id, name || `User ${id}`, productId);
        }
      });
    }

    function buildChatTargetIcon(contact, type){
      if (!contact || !contact.id) return '';
      const letter = getInitialForName(contact.name, type === 'seller' ? 'S' : 'U');
      const title = type === 'seller'
        ? `Chat with ${contact.name || `Seller ${contact.id}`}`
        : `Chat with ${contact.name || `User ${contact.id}`}`;
      return `
        <button type="button"
                class="chat-target-icon"
                data-type="${type}"
                data-id="${contact.id}"
                data-name="${escapeAttr(contact.name || '')}"
                data-product-id="${contact.productId || ''}"
                title="${escapeAttr(title)}"
                aria-label="${escapeAttr(title)}">
          <span class="icon-letter">${letter}</span>
        </button>
      `;
    }

    function contactAllowed(type, id){
      if (!type || !id) return false;
      if (type === 'seller') return riderChatContacts.sellers.has(String(id));
      if (type === 'user') return riderChatContacts.users.has(String(id));
      return false;
    }

    function renderChatTargetIcons(){
      const targetsEl = document.getElementById('riderChatTargets');
      if (!targetsEl) return;
      const fragments = [];
      riderChatContacts.sellers.forEach((contact)=>fragments.push(buildChatTargetIcon(contact, 'seller')));
      riderChatContacts.users.forEach((contact)=>fragments.push(buildChatTargetIcon(contact, 'user')));
      if (fragments.length){
        targetsEl.innerHTML = fragments.join('');
        targetsEl.classList.add('has-targets');
      } else {
        targetsEl.innerHTML = '';
        targetsEl.classList.remove('has-targets');
      }
    }

    function resetChatContacts(){
      riderChatContacts.sellers.clear();
      riderChatContacts.users.clear();
      renderChatTargetIcons();
    }

    function addChatTargetContact(contact){
      if (!contact || !contact.id) return;
      const normalized = {
        id: String(contact.id),
        name: contact.name || '',
        productId: contact.productId || ''
      };
      if (contact.type === 'seller'){
        riderChatContacts.sellers.set(normalized.id, normalized);
      } else if (contact.type === 'user'){
        riderChatContacts.users.set(normalized.id, normalized);
      }
      renderChatTargetIcons();
    }

    function updateChatContactsFromOrders(orders){
      riderChatContacts.sellers.clear();
      riderChatContacts.users.clear();
      (orders || []).forEach(order => {
        if (!shouldShowChatButtons(order)) return;
        const productId = order.sellerOrderID || order.sellerOrderId || order.id || order.order_number || '';
        if (order.sellerID){
          riderChatContacts.sellers.set(String(order.sellerID), {
            id: String(order.sellerID),
            name: order.seller_name || order.shop_name || '',
            productId
          });
        }
        if (order.userID){
          riderChatContacts.users.set(String(order.userID), {
            id: String(order.userID),
            name: order.user_name || '',
            productId
          });
        }
      });
      renderChatTargetIcons();
    }

    const overlay = document.getElementById('pendingOverlay');
    if (overlay && overlay.classList.contains('visible')) overlay.style.display = 'flex';
    const refreshBtn = document.getElementById('refreshStatusBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        try {
          const r = await fetch('/api/rider/status', { credentials:'include' });
          const j = await r.json();
          if (r.ok && j.status && ['approved','active'].includes(j.status.trim().toLowerCase())) { location.reload(); }
          else { alert('Your account is still pending admin approval.'); }
        } catch (e) { alert('Failed to check status'); }
        finally { refreshBtn.disabled = false; }
      });
    }

    // Profile / account dropdown behavior (supports both the simple profileBtn/menu and admin-style ActBtnRider/riderDropdown)
    (function(){
      const acctBtn = document.getElementById('ActBtnRider') || document.getElementById('ActBtn') || document.getElementById('profileBtn');
      const acctMenu = document.getElementById('riderDropdown') || document.getElementById('userDropdown') || document.getElementById('profileMenu');
      if (!acctBtn || !acctMenu) return;

      function closeAcct(){
        acctMenu.style.display = '';
        acctMenu.classList.remove('visible');
        acctMenu.setAttribute && acctMenu.setAttribute('aria-hidden','true');
        acctBtn.setAttribute && acctBtn.setAttribute('aria-expanded','false');
      }
      function openAcct(){
        acctMenu.style.display = 'block';
        acctMenu.classList.add('visible');
        acctMenu.setAttribute && acctMenu.setAttribute('aria-hidden','false');
        acctBtn.setAttribute && acctBtn.setAttribute('aria-expanded','true');
      }

      acctBtn.addEventListener('click', function(ev){ ev.stopPropagation(); if (acctMenu.classList.contains('visible')) closeAcct(); else openAcct(); });
      document.addEventListener('click', function(ev){ if (!acctMenu.contains(ev.target) && !acctBtn.contains(ev.target)) closeAcct(); });
      document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') closeAcct(); });

      // wire logout buttons if present (rider uses /rider-logout; generic buttons keep /logout)
      const logoutIds = ['riderLogoutBtn','logoutBtn','adminLogoutBtn'];
      for (const id of logoutIds){
        const b = document.getElementById(id);
        if (!b) continue;
        b.addEventListener('click', async function(){
          let endpoint = '/logout';
          if (id === 'riderLogoutBtn') endpoint = '/rider-logout';
          else if (id === 'adminLogoutBtn') endpoint = '/admin-logout';
          try { await fetch(endpoint, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'} }); } catch(e){}
          window.location = (id === 'adminLogoutBtn') ? '/login' : '/';
        });
      }
    })();

    // Load assigned orders
    async function loadOrders(){
      try {
        const r = await fetch('/api/rider/orders', { credentials:'include' });
        const j = await r.json();
        console.debug('loadOrders: api response', j);
        const root = document.getElementById('riderOrders');
        if (!root) return;
        // Handle common error/empty cases with clearer messaging and an on-page
        // debug dump so it's easier to see what the server returned without
        // opening DevTools.
        // Unauthorized
        if (r.status === 401){
          resetChatContacts();
          root.innerHTML = `<div class="empty-orders"><div class="empty-icon">🔒</div><h3>Not signed in as rider</h3><p>Please sign in as a rider to view assigned orders.</p></div>`;
          showOrdersDebug(root, r.status, j);
          return;
        }

        if (!r.ok){
          resetChatContacts();
          root.innerHTML = `<div class="empty-orders"><div class="empty-icon">⚠️</div><h3>Failed to load orders</h3><p>Server returned status ${r.status}.</p></div>`;
          showOrdersDebug(root, r.status, j);
          return;
        }

        if (!j || !j.success){
          resetChatContacts();
          root.innerHTML = `<div class="empty-orders"><div class="empty-icon">ℹ️</div><h3>No Assigned Orders</h3><p>Orders assigned to you will appear here.</p></div>`;
          showOrdersDebug(root, r.status, j);
          return;
        }

        if (!j.orders || !j.orders.length){
          resetChatContacts();
          root.innerHTML = `<div class="empty-orders"><div class="empty-icon"><i class="fas fa-shopping-bag"></i></div><h3>No Assigned Orders</h3><p>Orders assigned to you will appear here.</p></div>`;
          showOrdersDebug(root, r.status, j);
          return;
        }
        // Normalize property names and log statuses to help debug missing assignments
        const ordersRaw = (j.orders || []).map(o => Object.assign({}, o, {
          sellerOrderID: o.sellerOrderID || o.sellerOrderId || o.id,
          riderAccepted: !!o.riderAccepted
        }));
        currentRiderOrders = ordersRaw;
        updateChatContactsFromOrders(ordersRaw);
        console.debug('loadOrders: normalized orders count', ordersRaw.length);
        ordersRaw.forEach(o=> console.debug('order', o.sellerOrderID, (o.status||'').toLowerCase()));

        root.innerHTML = ordersRaw.map(o => {
          const sellerName = o.seller_name || o.shop_name || 'Seller';
          const userName = o.user_name || 'User';
          const orderId = o.sellerOrderID || '';
          const statusLower = normalizeStatus(o.status);
          const riderAccepted = !!o.riderAccepted;
          const showChats = shouldShowChatButtons(o);
          const showAcceptDecline = !riderAccepted && !['on_the_way','delivered'].includes(statusLower);
          const showStatusMenu = riderAccepted || ['on_the_way','delivered'].includes(statusLower);
          let displayStatus = (o.status||'pending').replace(/_/g,' ');
          if (statusLower === 'assigned_to_rider' && !riderAccepted) {
             displayStatus = 'Request Received';
          }
          return `
          <div class="order-card" data-seller-id="${o.sellerID||''}" data-seller-name="${escapeAttr(sellerName)}" data-user-id="${o.userID||''}" data-user-name="${escapeAttr(userName)}" data-product-id="${orderId}">
            <div class="order-head">
              <strong>#${o.order_number}</strong>
              <span class="badge">${displayStatus}</span>
            </div>
            <div class="order-shop">Shop: ${o.shop_name}</div>
            <div class="order-location">Pickup: ${o.pickup_location||'—'}</div>
            <div class="order-location">Delivery: ${o.delivery_location||'—'}</div>
            <div class="order-actions">
            ${showChats ? buildChatButtonsHTML({
              userId: o.userID || '',
              userName,
              orderId,
              sellerId: o.sellerID || '',
              sellerName
            }) : ''}
                ${showAcceptDecline ? `
                  <button class="btn btn-accept" data-id="${o.sellerOrderID}">Accept</button>
                  <button class="btn btn-decline" data-id="${o.sellerOrderID}">Decline</button>
                  <button class="btn btn-view" data-id="${o.sellerOrderID}">View Product</button>
                ` : ''}
                ${showStatusMenu ? `
                  <div class="status-dropdown" data-id="${o.sellerOrderID}">
                    <button type="button" class="status-btn" aria-haspopup="true" aria-expanded="false">
                      <span class="status-label"><span class="status-dot"></span><span class="status-text">Update status…</span></span>
                      <i class="fas fa-chevron-down"></i>
                    </button>
                    <div class="status-menu">
                      <div class="status-item on-the-way" data-value="on_the_way"><span class="status-dot"></span><span>On the way</span></div>
                      <div class="status-item delivered" data-value="delivered"><span class="status-dot"></span><span>Delivered</span></div>
                    </div>
                  </div>
                  <button class="btn btn-view" data-id="${o.sellerOrderID}">View Product</button>
                ` : ''}
              </div>
          </div>
        `;
        }).join('');

        // Accept/Decline wiring
        // wire accept/decline
        root.querySelectorAll('.btn-accept').forEach(b=>{ b.addEventListener('click', ()=>acceptAndReplace(b)); });
        root.querySelectorAll('.btn-decline').forEach(b=>b.addEventListener('click', ()=>declineFlow(b.dataset.id)));

        // wire custom dropdowns for status updates
        root.querySelectorAll('.status-dropdown').forEach(dd=>{
          const id = dd.dataset.id;
          const btn = dd.querySelector('.status-btn');
          const menu = dd.querySelector('.status-menu');
          if (!btn || !menu) return;

          // toggle dropdown
          btn.addEventListener('click', (ev)=>{
            ev.stopPropagation();
            // close other dropdowns
            document.querySelectorAll('.status-dropdown.visible').forEach(d=>{ if (d !== dd) d.classList.remove('visible'); });
            const isVisible = dd.classList.toggle('visible');
            btn.setAttribute('aria-expanded', isVisible ? 'true' : 'false');
          });

          // selection
          menu.querySelectorAll('.status-item').forEach(item=>{
            item.addEventListener('click', (ev)=>{
              const status = item.dataset.value;
              // update button label immediately for feedback
              const txt = item.textContent.trim();
              const label = dd.querySelector('.status-text');
              if (label) label.textContent = txt;
              dd.classList.remove('visible');
              btn.setAttribute('aria-expanded','false');
              // call updateStatus
              updateStatus(id, status);
            });
          });
        });

        // wire view buttons
        root.querySelectorAll('.btn-view').forEach(b=>{ 
          b.addEventListener('click', ()=>openDetails(b.dataset.id)); 
        });

        attachChatButtonHandlers(root);
      } catch(e){ console.error(e); }
    }

    async function loadDailyDeliveriesChart(){
      if (!dailyDeliveriesCanvas || typeof Chart === 'undefined') return;
      setChartState(dailyDeliveriesStateEl, 'Loading daily deliveries…');
      try{
        const res = await fetch('/api/rider/stats/daily-deliveries', { credentials:'include' });
        const payload = await res.json().catch(()=>null);
        if (!res.ok || !payload || !payload.success){
          throw new Error(payload && payload.msg ? payload.msg : 'server error');
        }
        const labels = payload.labels || [];
        const data = payload.data || [];
        if (!labels.length){
          if (dailyDeliveriesChart){ dailyDeliveriesChart.destroy(); dailyDeliveriesChart = null; }
          setChartState(dailyDeliveriesStateEl, 'No deliveries yet.');
          return;
        }
        setChartState(dailyDeliveriesStateEl, '');
        const ctx = dailyDeliveriesCanvas.getContext('2d');
        if (dailyDeliveriesChart){ dailyDeliveriesChart.destroy(); }
        dailyDeliveriesChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: 'Completed deliveries',
              data,
              borderColor: '#2563eb',
              backgroundColor: 'rgba(37,99,235,0.12)',
              tension: 0.35,
              fill: true,
              pointRadius: 3,
              pointBackgroundColor: '#2563eb'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: {
                beginAtZero: true,
                ticks: { precision: 0 }
              }
            }
          }
        });
      } catch(err){
        console.error('Failed to load daily deliveries', err);
        if (dailyDeliveriesChart){ dailyDeliveriesChart.destroy(); dailyDeliveriesChart = null; }
        setChartState(dailyDeliveriesStateEl, 'Unable to load daily deliveries.');
      }
    }

    async function loadAcceptanceOverviewChart(){
      if (!acceptanceCanvas || typeof Chart === 'undefined') return;
      setChartState(acceptanceStateEl, 'Loading acceptance data…');
      try{
        const res = await fetch('/api/rider/stats/acceptance-overview', { credentials:'include' });
        const payload = await res.json().catch(()=>null);
        if (!res.ok || !payload || !payload.success){
          throw new Error(payload && payload.msg ? payload.msg : 'server error');
        }
        const labels = payload.labels || [];
        const accepted = payload.accepted || [];
        const declined = payload.declined || [];
        if (!labels.length){
          if (acceptanceOverviewChart){ acceptanceOverviewChart.destroy(); acceptanceOverviewChart = null; }
          setChartState(acceptanceStateEl, 'No acceptance data yet.');
          return;
        }
        setChartState(acceptanceStateEl, '');
        const ctx = acceptanceCanvas.getContext('2d');
        if (acceptanceOverviewChart){ acceptanceOverviewChart.destroy(); }
        acceptanceOverviewChart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels,
            datasets: [
              {
                label: 'Accepted',
                data: accepted,
                backgroundColor: 'rgba(16,185,129,0.6)'
              },
              {
                label: 'Declined',
                data: declined,
                backgroundColor: 'rgba(248,113,113,0.6)'
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                ticks: { precision: 0 }
              }
            }
          }
        });
      } catch(err){
        console.error('Failed to load acceptance overview', err);
        if (acceptanceOverviewChart){ acceptanceOverviewChart.destroy(); acceptanceOverviewChart = null; }
        setChartState(acceptanceStateEl, 'Unable to load acceptance data.');
      }
    }

    async function loadRecentDeliveries(){
      if (!recentDeliveriesBody) return;
      recentDeliveriesBody.innerHTML = `<tr><td colspan="10" class="no-data">Loading recent deliveries…</td></tr>`;
      try{
        const res = await fetch('/api/rider/stats/recent-deliveries?limit=10', { credentials:'include' });
        const payload = await res.json().catch(()=>null);
        if (!res.ok || !payload || !payload.success){
          throw new Error(payload && payload.msg ? payload.msg : 'server error');
        }
        const rows = payload.data || [];
        if (!rows.length){
          recentDeliveriesBody.innerHTML = `<tr><td colspan="10" class="no-data">No recent deliveries</td></tr>`;
          return;
        }
        recentDeliveriesBody.innerHTML = rows.map(order => {
          const created = formatDateTime(order.created_at);
          const updated = formatDateTime(order.updated_at);
          return `
            <tr>
              <td>${escapeHtml(order.orderID ?? '—')}</td>
              <td>${escapeHtml(order.userID ?? '—')}</td>
              <td>${escapeHtml(order.order_number || '—')}</td>
              <td>${escapeHtml((order.status || '—').replace(/_/g,' '))}</td>
              <td>${escapeHtml(formatCurrency(order.total_amount || 0))}</td>
              <td>${escapeHtml(order.shipping_address || '—')}</td>
              <td>${escapeHtml(order.contact_number || '—')}</td>
              <td>${escapeHtml(order.payment_method || '—')}</td>
              <td>${escapeHtml(created)}</td>
              <td>${escapeHtml(updated)}</td>
            </tr>
          `;
        }).join('');
      } catch(err){
        console.error('Failed to load recent deliveries', err);
        recentDeliveriesBody.innerHTML = `<tr><td colspan="10" class="no-data">Unable to load recent deliveries.</td></tr>`;
      }
    }

    async function loadSummaryStats(){
      const totalDeliveriesEl = document.getElementById('riderTotalDeliveries');
      const totalEarningsEl = document.getElementById('riderTotalEarnings');
      const pendingOrdersEl = document.getElementById('riderPendingOrders');
      const completedTodayEl = document.getElementById('riderCompletedToday');
      const earningsWeekEl = document.getElementById('riderEarningsWeek');
      const earningsMonthEl = document.getElementById('riderEarningsMonth');
      if (!totalDeliveriesEl || !totalEarningsEl || !pendingOrdersEl || !completedTodayEl) return;
      try{
        const res = await fetch('/api/rider/stats/summary', { credentials:'include' });
        const payload = await res.json().catch(()=>null);
        if (!res.ok || !payload || !payload.success){
          throw new Error(payload && payload.msg ? payload.msg : 'server error');
        }
        const totalDeliveries = payload.total_deliveries ?? 0;
        const pendingOrders = payload.pending_orders ?? 0;
        const completedToday = payload.completed_today ?? 0;
        const totalEarnings = payload.total_earnings ?? 0;
        const earningsWeek = payload.earnings_week ?? 0;
        const earningsMonth = payload.earnings_month ?? 0;

        totalDeliveriesEl.textContent = String(totalDeliveries);
        pendingOrdersEl.textContent = String(pendingOrders);
        completedTodayEl.textContent = String(completedToday);
        totalEarningsEl.textContent = formatCurrency(totalEarnings);
        if (earningsWeekEl) earningsWeekEl.textContent = formatCurrency(earningsWeek);
        if (earningsMonthEl) earningsMonthEl.textContent = formatCurrency(earningsMonth);
      }catch(err){
        console.error('Failed to load rider summary stats', err);
      }
    }

    function refreshRiderStats(){
      loadSummaryStats();
      loadDailyDeliveriesChart();
      loadAcceptanceOverviewChart();
      loadRecentDeliveries();
    }


    // Debug helper intentionally disabled in the production UI.
    // Kept as a no-op so callers elsewhere in the script do not need changes.
    function showOrdersDebug(rootEl, status, body){
      try{
        const dbg = document.getElementById('riderOrdersDebug');
        if (dbg){
          dbg.style.display = 'none';
          dbg.textContent = '';
        }
      }catch(e){ /* intentionally silent */ }
    }

    async function respond(id, action, payload){
      try {
        await fetch(`/api/rider/orders/${encodeURIComponent(id)}/respond`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify(Object.assign({ action }, payload||{})) });
        loadOrders();
        refreshRiderStats();
      } catch(e){ alert('Failed'); }
    }

    // When rider accepts an order, update the UI immediately to replace accept/decline
    async function acceptAndReplace(button){
      const id = button.dataset.id;
      const actionsEl = button.closest('.order-actions');
      if (!actionsEl) return;

      // Save original HTML so we can revert on failure
      const origActions = actionsEl.innerHTML;
      const card = button.closest('.order-card');
      const origBadgeText = (card && card.querySelector('.badge')) ? card.querySelector('.badge').textContent : null;

      // Get seller and user info from card
      const sellerId = card ? (card.getAttribute('data-seller-id') || '') : '';
      const sellerName = card ? (card.getAttribute('data-seller-name') || 'Seller') : 'Seller';
      const userId = card ? (card.getAttribute('data-user-id') || '') : '';
      const userName = card ? (card.getAttribute('data-user-name') || 'User') : 'User';
      const orderId = card ? (card.getAttribute('data-product-id') || id) : id;
      
      // Optimistically replace Accept/Decline immediately with the custom dropdown
      actionsEl.innerHTML = `
        ${buildChatButtonsHTML({ userId, userName, orderId, sellerId, sellerName })}
        <div class="status-dropdown" data-id="${id}">
          <button type="button" class="status-btn" aria-haspopup="true" aria-expanded="false"><span class="status-label"><span class="status-dot"></span><span class="status-text">Update status…</span></span><i class="fas fa-chevron-down"></i></button>
          <div class="status-menu">
            <div class="status-item on-the-way" data-value="on_the_way"><span class="status-dot"></span><span>On the way</span></div>
            <div class="status-item delivered" data-value="delivered"><span class="status-dot"></span><span>Delivered</span></div>
          </div>
        </div>
        <button class="btn btn-view" data-id="${id}">View Product</button>
      `;
      const dd = actionsEl.querySelector('.status-dropdown');
      const viewBtn = actionsEl.querySelector('.btn-view');
      if (dd) {
        const btn = dd.querySelector('.status-btn');
        const menu = dd.querySelector('.status-menu');
        if (btn) btn.addEventListener('click', (ev)=>{ ev.stopPropagation(); dd.classList.toggle('visible'); btn.setAttribute('aria-expanded', dd.classList.contains('visible') ? 'true' : 'false'); });
        if (menu) menu.querySelectorAll('.status-item').forEach(item=>item.addEventListener('click', ()=>{ const s = item.dataset.value; const txt = item.textContent.trim(); const lab = dd.querySelector('.status-text'); if (lab) lab.textContent = txt; dd.classList.remove('visible'); if (btn) btn.setAttribute('aria-expanded','false'); updateStatus(id, s);}));
      }
      if (viewBtn) viewBtn.addEventListener('click', ()=>openDetails(id));
      attachChatButtonHandlers(actionsEl);

      // update badge/status label in card immediately
      if (card){
        const badge = card.querySelector('.badge');
        if (badge) badge.textContent = 'assigned_to_rider';
      }

      if (shouldShowChatButtons({ status: 'assigned_to_rider', riderAccepted: true })){
        if (sellerId){
          addChatTargetContact({ type: 'seller', id: sellerId, name: sellerName, productId: orderId });
        }
        if (userId){
          addChatTargetContact({ type: 'user', id: userId, name: userName, productId: orderId });
        }
      }

      // Send accept request in background; on failure revert and reload canonical state
      try {
        const payload = { action: 'accept' };
        if (sellerId) payload.sellerID = sellerId;
        if (userId) payload.userID = userId;
        if (id) payload.productID = id;
        const r = await fetch(`/api/rider/orders/${encodeURIComponent(id)}/respond`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if (!r.ok) {
          // server returned error — notify user and revert
          const txt = await r.text().catch(()=>null);
          alert('Accept request failed: ' + (txt || r.statusText || 'server error'));
          try {
            actionsEl.innerHTML = origActions;
            if (card && origBadgeText != null) {
              const badge = card.querySelector('.badge');
              if (badge) badge.textContent = origBadgeText;
            }
          } catch (err){ console.error('Failed to revert UI after accept failure', err); }
          // ensure canonical state
          try { loadOrders(); } catch(e){ console.error(e); }
        } else {
          // on success, refresh stats (including Acceptance Overview) without reloading orders
          if (typeof window.emitRiderChatMessage === 'function' && sellerId) {
            try {
              window.emitRiderChatMessage({
                message: 'The rider accepts the delivery of the product',
                sellerId,
                productId: orderId || id
              });
            } catch (err) {
              console.error('auto notify seller failed', err);
            }
          }
          try { refreshRiderStats(); } catch(e){ console.error(e); }
        }
      } catch(e){
        alert('Failed to accept order (network)');
        try { actionsEl.innerHTML = origActions; if (card && origBadgeText != null) { const badge = card.querySelector('.badge'); if (badge) badge.textContent = origBadgeText; } } catch(err){/*ignore*/}
        try { loadOrders(); } catch(e){/*ignore*/}
      }
    }

    // Close any open status dropdowns when clicking outside or pressing Escape
    document.addEventListener('click', function(ev){
      document.querySelectorAll('.status-dropdown.visible').forEach(d=>{ if (!d.contains(ev.target)) d.classList.remove('visible'); });
    });
    document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') document.querySelectorAll('.status-dropdown.visible').forEach(d=>d.classList.remove('visible')); });

    function declineFlow(id){
      const reason = prompt('Select a reason:\n- Not available\n- Too far\n- Vehicle issue', 'Not available');
      const details = reason ? prompt('Add details (optional):','') : '';
      respond(id, 'decline', { reason, details });
    }

    async function updateStatus(id, status){
      if (!status) return;
      try {
        const r = await fetch(`/api/rider/orders/${encodeURIComponent(id)}/status`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status }) });
        if (!r.ok) {
          const txt = await r.text().catch(()=>null);
          alert('Failed to update status: ' + (txt || r.statusText || 'server error'));
          return;
        }

        // If the order was marked delivered, move it from Available Orders to My Orders
        if ((status||'').toLowerCase() === 'delivered'){
          try{
            const dd = document.querySelector(`.status-dropdown[data-id="${CSS.escape(id)}"]`);
            const card = dd ? dd.closest('.order-card') : document.querySelector(`.order-card [data-id="${CSS.escape(id)}"]`)?.closest('.order-card');
            if (card){
              // update badge text
              const badge = card.querySelector('.badge');
              if (badge) badge.textContent = 'delivered';

              // remove any chat buttons if present (defensive)
              card.querySelectorAll('.btn-chat-user, .btn-chat-seller').forEach(b=>b.remove());

              // append to My Orders list (if exists)
              const myList = document.getElementById('myOrdersList');
              if (myList){
                // Ensure myOrdersList contains a container for items
                let container = myList.querySelector('.orders-list');
                if (!container){
                  container = document.createElement('div');
                  container.className = 'orders-list';
                  myList.appendChild(container);
                }
                // move the card node into My Orders
                container.appendChild(card);
              } else {
                // fallback: remove the card from Available Orders
                card.remove();
              }
            }
          }catch(e){ console.error('Failed to move delivered order to My Orders', e); }
        } else {
          // For other status changes, refresh available orders to reflect new state
          loadOrders();
        }
        refreshRiderStats();
      } catch(e){ alert('Failed to update status'); }
    }

    async function openDetails(id){
      try {
        const r = await fetch(`/api/rider/orders/${encodeURIComponent(id)}/details`, { credentials:'include' });
        const j = await r.json();
        if (!r.ok || !j.success) { alert(j.msg||'Failed to load details'); return; }
        showDetailsModal(j.order);
      } catch(e){ alert('Failed to load details'); }
    }

    function showDetailsModal(order){
      const modal = document.getElementById('orderDetailsModal');
      const content = document.getElementById('orderDetailsContent');
      if (!modal || !content) return;
      const addrParts = [order.exact_address, order.barangay, order.city, order.province, order.region].filter(Boolean).join(', ');
      const itemsHtml = (order.items||[]).map(it=>`
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px;">
              <img src="${it.image ? '/uploads/'+it.image.split(',')[0] : '/static/images/default.png'}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;">
              <span>${escapeHtml(it.name)}</span>
            </div>
          </td>
          <td>${it.quantity}</td>
          <td>₱${Number(it.price||0).toFixed(2)}</td>
        </tr>
      `).join('');
      // build payment display
      let paymentDisplay = '';
      if (order.payment_method) paymentDisplay = escapeHtml(order.payment_method);
      else if (order.payment_type) paymentDisplay = escapeHtml(order.payment_type);
      else if (order.payment_options && Array.isArray(order.payment_options)) paymentDisplay = escapeHtml(order.payment_options.join(', '));
      else paymentDisplay = '—';

      content.innerHTML = `
          <div class="order-details-header">
            <h3>Order #${order.order_number}</h3>
            <button id="closeOrderDetails" class="order-details-close">Close</button>
          </div>
          <div class="order-details-grid">
            <div><strong>Customer:</strong> ${escapeHtml(order.user_name||'Customer')}</div>
            <div><strong>Shop:</strong> ${escapeHtml(order.shop_name||'Shop')}</div>
            <div><strong>Contact:</strong> ${escapeHtml(order.contact_number||'—')}</div>
            <div><strong>Total Amount:</strong> ₱${Number(order.total_amount||0).toFixed(2)}</div>
            <div><strong>Region:</strong> ${escapeHtml(order.region||'—')}</div>
            <div><strong>Province:</strong> ${escapeHtml(order.province||'—')}</div>
            <div><strong>City:</strong> ${escapeHtml(order.city||'—')}</div>
            <div><strong>Barangay:</strong> ${escapeHtml(order.barangay||'—')}</div>
            <div class="order-details-address"><strong>Address:</strong> ${escapeHtml(order.address||'')}<br>${escapeHtml(addrParts)}</div>
            <div><strong>Payment:</strong> ${paymentDisplay}</div>
          </div>
          <div>
            <table class="order-details-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Qty</th>
                  <th>Price</th>
                </tr>
              </thead>
              <tbody>
                ${itemsHtml || '<tr><td colspan="3" class="empty-items">No items</td></tr>'}
              </tbody>
            </table>
          </div>
        `;
      modal.style.display = 'flex';
      const closeBtn = document.getElementById('closeOrderDetails');
      if (closeBtn) closeBtn.addEventListener('click', ()=>{ modal.style.display='none'; });
      modal.addEventListener('click', (ev)=>{ if (ev.target === modal) modal.style.display='none'; }, { once:true });
    }

    function escapeHtml(s){
      return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] || c));
    }

    loadOrders();
    refreshRiderStats();
    bindChatTargetsDelegation();

    // Rider notifications / polling
    (function(){
      const root = document.getElementById('riderOrders');
      if (!root) return;

      // Periodically refresh the orders list
      setInterval(loadOrders, 15000);

      // Notification bell UI elements
      const notifBtn = document.getElementById('riderNotifBtn');
      const notifMenu = document.getElementById('riderNotifMenu');
      const notifList = document.getElementById('riderNotifList');
      const notifCount = document.getElementById('riderNotifCount');
      const markAllBtn = document.getElementById('riderNotifMarkAll');

      function toggleNotif(show){
        if (!notifMenu) return;
        const visible = (show === undefined) ? (notifMenu.style.display === 'block') : !!show;
        notifMenu.style.display = visible ? 'block' : 'none';
      }

      function escapeHtml(value){
        const str = value == null ? '' : String(value);
        return str.replace(/[&<>"']/g, function(match){
          switch(match){
            case '&': return '&amp;';
            case '<': return '&lt;';
            case '>': return '&gt;';
            case '"': return '&quot;';
            case "'": return '&#39;';
            default: return match;
          }
        });
      }

      function formatStamp(value){
        if (!value) return '';
        try{
          const date = new Date(value);
          if (!Number.isNaN(date.valueOf())){
            return date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
          }
        }catch(e){}
        const raw = String(value);
        return raw.length > 19 ? raw.slice(0, 19) : raw;
      }

      function isUnreadFlag(value){
        if (value === undefined || value === null) return true;
        if (typeof value === 'boolean') return value === false;
        const str = String(value).trim().toLowerCase();
        if (str === '1' || str === 'true' || str === 'yes') return false;
        if (str === '0' || str === 'false' || str === 'no') return true;
        const num = Number(str);
        if (!Number.isNaN(num)) return num < 1;
        return true;
      }

      function renderRiderNotifs(list){
        if (!notifList) return;
        if (!list || !list.length){
          notifList.innerHTML = '<div class="notif-empty">No notifications</div>';
          if (notifCount){ notifCount.style.display = 'none'; notifCount.textContent = '0'; }
          if (markAllBtn){ markAllBtn.disabled = true; }
          return;
        }
        let unreadCounter = 0;
        const parts = list.map(n => {
          const unread = isUnreadFlag(n.is_read);
          if (unread) unreadCounter += 1;
          const cardClasses = ['notif-card'];
          if (unread) cardClasses.push('unread');
          const rows = ['<div class="' + cardClasses.join(' ') + '">'];
          rows.push('<div class="notif-card-title">' + escapeHtml(n.title || 'Notification') + '</div>');
          if (n.body) rows.push('<div class="notif-card-body">' + escapeHtml(n.body) + '</div>');
          const ts = formatStamp(n.created_at);
          if (ts) rows.push('<div class="notif-card-meta">' + escapeHtml(ts) + '</div>');
          rows.push('</div>');
          return rows.join('');
        });
        notifList.innerHTML = parts.join('');
        if (notifCount){
          notifCount.textContent = String(unreadCounter);
          notifCount.style.display = unreadCounter ? 'inline-flex' : 'none';
        }
        if (markAllBtn){ markAllBtn.disabled = unreadCounter === 0; }
      }

      async function loadRiderNotifications(){
        try{
          const r = await fetch('/api/rider/notifications', { credentials: 'include' });
          const j = await r.json().catch(()=>null);
          if (r.ok && j && j.success){ renderRiderNotifs(j.notifications || []); }
        }catch(e){ console.error('Failed to load rider notifications', e); }
      }

      async function markAllRiderNotifications(){
        if (!markAllBtn) return;
        markAllBtn.disabled = true;
        try{
          const res = await fetch('/api/rider/notifications/mark_read', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          });
          if (!res.ok){
            console.error('Failed to mark rider notifications read', res.status);
          }
        }catch(err){
          console.error('Failed to mark rider notifications read', err);
        }
        loadRiderNotifications();
      }

      if (notifBtn){
        notifBtn.addEventListener('click', function(ev){
          ev.preventDefault(); ev.stopPropagation();
          const isOpen = notifMenu && notifMenu.style.display === 'block';
          toggleNotif(!isOpen);
          if (!isOpen) {
            markAllRiderNotifications();
          }
        });
      }

      markAllBtn?.addEventListener('click', function(ev){
        ev.preventDefault();
        markAllRiderNotifications();
      });

      document.addEventListener('click', function(ev){
        if (!notifMenu || !notifBtn) return;
        if (!notifMenu.contains(ev.target) && !notifBtn.contains(ev.target)) toggleNotif(false);
      });

      // Initial load of rider notifications
      loadRiderNotifications();
      setInterval(loadRiderNotifications, 15000);

      // Also listen for server push events and refresh when notified
      if (typeof io !== 'undefined') {
        const RIDER_ID = (document.getElementById('riderData') && document.getElementById('riderData').dataset) ? (document.getElementById('riderData').dataset.riderId || null) : null;
        if (RIDER_ID) {
          try{
            const notifSocket = io(riderAuthOptions({ transports:['polling'] }));
            notifSocket.on('connect', ()=>{ notifSocket.emit('join', { room: `rider_${RIDER_ID}` }); });
            notifSocket.on('notification', (data)=>{
              try{
                if (!data || data.recipient_type !== 'rider') return;
                loadRiderNotifications();
                loadOrders();
                refreshRiderStats();
              }catch(e){ console.debug('rider notification handler error', e); }
            });
          }catch(e){ console.debug('Socket.IO rider notification unavailable', e); }
        }
      }
    })();

    // Rider chat client (comprehensive implementation matching seller dashboard)
    (function(){
      const RIDER_ID = (document.getElementById('riderData') && document.getElementById('riderData').dataset) ? (document.getElementById('riderData').dataset.riderId || null) : null;
      let riderSocket = null;
      let activeContactID = null;
      let activeContactType = null; // 'seller' or 'user'
      let activeMode = 'all';
      let activeProductID = null;

      function readCookie(name){
        const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : null;
      }

      function riderAuthOptions(base){
        const opts = base ? Object.assign({}, base) : {};
        opts.withCredentials = true;
        const token = readCookie('rider_session');
        opts.auth = { role: 'rider' };
        if (token) opts.auth.session = token;
        return opts;
      }

      const sellerModalState = {
        overlay: null,
        messagesEl: null,
        sellerId: null,
        productId: null,
        socketHandler: null,
        keydownHandler: null,
        inputEl: null,
        inputHandler: null
      };

      function findMessageByAttribute(root, attr, value){
        if (!root || value === undefined || value === null) return null;
        const target = String(value);
        return Array.from(root.querySelectorAll(`[${attr}]`)).find(el => el.getAttribute(attr) === target) || null;
      }

      function emitRiderChat({ message, sellerId, productId, localId }){
        if (!message || !sellerId || !RIDER_ID) return false;
        const socket = ensureSocket();
        if (!socket || typeof socket.emit !== 'function') return false;
        const payload = {
          message,
          sellerID: sellerId,
          riderID: RIDER_ID
        };
        const normalizedProductId = normalizeProductId(productId);
        if (normalizedProductId !== null) payload.productID = normalizedProductId;
        if (localId) payload.localId = localId;
        try {
          socket.emit('chat_message', payload);
          return true;
        } catch (err) {
          console.error('emitRiderChat failed', err);
          return false;
        }
      }

      function closeSellerChatModal(){
        const socket = riderSocket;
        try {
          if (socket && sellerModalState.socketHandler && typeof socket.off === 'function') {
            socket.off('chat_message', sellerModalState.socketHandler);
          }
        } catch (err) {
          console.error('rider seller chat detach failed', err);
        }
        if (sellerModalState.overlay && sellerModalState.overlay.parentNode) {
          sellerModalState.overlay.parentNode.removeChild(sellerModalState.overlay);
        }
        if (sellerModalState.keydownHandler) {
          document.removeEventListener('keydown', sellerModalState.keydownHandler);
        }
        if (sellerModalState.inputEl && sellerModalState.inputHandler) {
          try { sellerModalState.inputEl.removeEventListener('keydown', sellerModalState.inputHandler); }
          catch (e) { /* ignore */ }
        }
        sellerModalState.overlay = null;
        sellerModalState.messagesEl = null;
        sellerModalState.sellerId = null;
        sellerModalState.productId = null;
        sellerModalState.socketHandler = null;
        sellerModalState.keydownHandler = null;
        sellerModalState.inputEl = null;
        sellerModalState.inputHandler = null;
      }

      function appendSellerModalMessage(text, isRider, msgId, ts, localId){
        const messagesEl = sellerModalState.messagesEl;
        if (!messagesEl || !text) return null;
        if (messagesEl.dataset.placeholder === '1') {
          messagesEl.innerHTML = '';
          delete messagesEl.dataset.placeholder;
        }

        if (msgId){
          const existing = findMessageByAttribute(messagesEl, 'data-message-id', msgId);
          if (existing){
            existing.removeAttribute('data-local');
            existing.setAttribute('data-sender', isRider ? 'rider' : 'seller');
            existing.classList.toggle('rider-bubble', !!isRider);
            existing.classList.toggle('seller-bubble', !isRider);
            if (ts){
              let meta = existing.querySelector('.meta-ts');
              if (!meta){
                meta = document.createElement('div');
                meta.className = 'meta-ts';
                meta.style.cssText = 'font-size:12px;color:#94a3b8;margin-top:4px;';
                existing.appendChild(meta);
              }
              meta.textContent = formatDateTime(ts);
            }
            return existing;
          }
        }

        if (msgId){
          const optimistic = Array.from(messagesEl.querySelectorAll('[data-local="1"]')).find(el => {
            if (el.getAttribute('data-sender') !== (isRider ? 'rider' : 'seller')) return false;
            const textEl = el.querySelector('.bubble-text');
            return textEl && textEl.textContent === text;
          });
          if (optimistic){
            optimistic.removeAttribute('data-local');
            optimistic.setAttribute('data-sender', isRider ? 'rider' : 'seller');
            if (msgId) optimistic.setAttribute('data-message-id', String(msgId));
            optimistic.classList.toggle('rider-bubble', !!isRider);
            optimistic.classList.toggle('seller-bubble', !isRider);
            if (ts){
              let meta = optimistic.querySelector('.meta-ts');
              if (!meta){
                meta = document.createElement('div');
                meta.className = 'meta-ts';
                meta.style.cssText = 'font-size:12px;color:#94a3b8;margin-top:4px;';
                optimistic.appendChild(meta);
              }
              meta.textContent = formatDateTime(ts);
            }
            return optimistic;
          }
        }

        if (localId){
          const existingLocal = findMessageByAttribute(messagesEl, 'data-message-local-id', localId);
          if (existingLocal) return existingLocal;
        }

        const wrapper = document.createElement('div');
        if (msgId) wrapper.setAttribute('data-message-id', String(msgId));
        if (localId) {
          wrapper.setAttribute('data-message-local-id', String(localId));
          wrapper.setAttribute('data-local', '1');
        }
        wrapper.setAttribute('data-sender', isRider ? 'rider' : 'seller');
        wrapper.className = isRider ? 'rider-bubble' : 'seller-bubble';
        wrapper.style.cssText = 'max-width:78%;padding:8px 12px;border-radius:12px;font-size:14px;line-height:1.3;' + (isRider ? 'align-self:flex-end;background:#0b73ff;color:#fff;' : 'align-self:flex-start;background:#f1f5f9;color:#0f1724;');

        const content = document.createElement('div');
        content.className = 'bubble-text';
        content.textContent = text;
        wrapper.appendChild(content);

        if (ts){
          const meta = document.createElement('div');
          meta.className = 'meta-ts';
          meta.style.cssText = 'font-size:12px;color:#94a3b8;margin-top:4px;';
          meta.textContent = formatDateTime(ts);
          wrapper.appendChild(meta);
        }

        messagesEl.appendChild(wrapper);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return wrapper;
      }

      async function loadSellerModalHistory(sellerId, productId){
        const messagesEl = sellerModalState.messagesEl;
        if (!messagesEl) return;
        messagesEl.innerHTML = '<div style="padding:12px;color:#64748b;">Loading conversation…</div>';
        messagesEl.dataset.placeholder = '1';
        const normalizedProductId = normalizeProductId(productId);
        const q = [];
        if (RIDER_ID) q.push(`riderID=${encodeURIComponent(RIDER_ID)}`);
        if (sellerId) q.push(`sellerID=${encodeURIComponent(sellerId)}`);
        if (normalizedProductId) q.push(`productID=${encodeURIComponent(normalizedProductId)}`);
        const url = '/api/chat/history' + (q.length ? '?' + q.join('&') : '');
        try {
          const res = await fetch(url, { credentials: 'include' });
          const body = await res.json().catch(()=>null);
          if (!res.ok || !body || !body.success){
            throw new Error((body && body.msg) || 'history_failed');
          }
          const rows = body.messages || [];
          if (!rows.length){
            messagesEl.innerHTML = '<div style="padding:12px;color:#64748b;">No messages yet. Start the conversation.</div>';
            messagesEl.dataset.placeholder = '1';
            return;
          }
          messagesEl.innerHTML = '';
          delete messagesEl.dataset.placeholder;
          rows.forEach(m => {
            const text = m.messages || m.message || '';
            if (!text) return;
            const senderRole = (m.sender_role || m.sender || '').toLowerCase();
            const senderId = m.senderID || m.senderId || m.userID || m.userId || null;
            const isRider = senderRole === 'rider' || (senderId && String(senderId) === String(RIDER_ID));
            const msgId = m.chatID || m.chatId || m.id || null;
            const ts = m.created_at || m.ts || null;
            appendSellerModalMessage(text, isRider, msgId, ts || null);
          });
        } catch (err) {
          console.error('seller chat modal history failed', err);
          messagesEl.innerHTML = '<div style="padding:12px;color:#ef4444;">Failed to load conversation.</div>';
          messagesEl.dataset.placeholder = '1';
        }
      }

      function handleSellerModalIncoming(payload){
        if (!payload || !sellerModalState.overlay || !sellerModalState.messagesEl) return;
        const sellerId = sellerModalState.sellerId;
        if (!sellerId) return;
        const payloadSeller = payload.sellerID || payload.sellerId || payload.seller_id;
        if (String(payloadSeller || '') !== String(sellerId)) return;
        if (RIDER_ID && String(payload.riderID || payload.riderId || payload.rider_id || '') !== String(RIDER_ID)) return;
        const text = payload.message || payload.messages || '';
        if (!text) return;
        const senderRole = (payload.sender_role || payload.sender || '').toLowerCase();
        const senderId = payload.senderID || payload.senderId || payload.userID || payload.userId || null;
        const isRider = senderRole === 'rider' || (senderId && String(senderId) === String(RIDER_ID));
        const msgId = payload.messageID || payload.chatID || payload.chatId || null;
        const ts = payload.created_at || payload.ts || null;
        const localId = payload.localId || payload.local_id || null;

        appendSellerModalMessage(text, isRider, msgId, ts || null, localId);
      }

      function attachSellerModalSocketHandler(){
        const socket = ensureSocket();
        if (!socket || typeof socket.on !== 'function') return;
        if (sellerModalState.socketHandler && typeof socket.off === 'function') {
          try { socket.off('chat_message', sellerModalState.socketHandler); }
          catch (err) { console.error('rider seller chat handler cleanup failed', err); }
        }
        const handler = (payload)=>{
          try { handleSellerModalIncoming(payload); }
          catch (err) { console.error('seller modal socket handler error', err); }
        };
        sellerModalState.socketHandler = handler;
        socket.on('chat_message', handler);
      }

      function openSellerChatModal(sellerId, sellerName, productId){
        if (!sellerId) return;
        closeSellerChatModal();
        const normalizedSellerId = String(sellerId);
        const overlay = document.createElement('div');
        overlay.id = 'riderSellerChatOverlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,42,0.45);display:flex;align-items:center;justify-content:center;z-index:10000;padding:16px;';

        const modal = document.createElement('div');
        modal.id = 'riderSellerChatModal';
        modal.style.cssText = 'width:360px;max-width:100%;background:#ffffff;border-radius:12px;box-shadow:0 18px 40px rgba(15,23,42,0.2);display:flex;flex-direction:column;overflow:hidden;font-family:Inter,Arial,sans-serif;';

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:#f8fafc;border-bottom:1px solid #e2e8f0;gap:12px;';
        const title = document.createElement('div');
        title.textContent = sellerName || `Seller ${normalizedSellerId}`;
        title.style.cssText = 'font-weight:600;color:#0f172a;font-size:15px;flex:1;min-width:0;';
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.innerHTML = '&times;';
        closeBtn.setAttribute('aria-label', 'Close chat');
        closeBtn.style.cssText = 'border:none;background:transparent;color:#475569;font-size:22px;line-height:1;cursor:pointer;padding:4px;';
        header.appendChild(title);
        header.appendChild(closeBtn);

        const messages = document.createElement('div');
        messages.className = 'rider-seller-chat-messages';
        messages.style.cssText = 'flex:1;min-height:260px;padding:14px;background:#ffffff;display:flex;flex-direction:column;gap:8px;overflow:auto;';

        const footer = document.createElement('div');
        footer.style.cssText = 'display:flex;gap:10px;padding:12px;border-top:1px solid #e2e8f0;background:#f9fafb;';
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Type a message...';
        input.style.cssText = 'flex:1;padding:10px;border-radius:8px;border:1px solid #cbd5f5;font-size:14px;';
        const sendBtn = document.createElement('button');
        sendBtn.type = 'button';
        sendBtn.textContent = 'Send';
        sendBtn.style.cssText = 'padding:10px 14px;background:#2563eb;color:#ffffff;border:none;border-radius:8px;font-weight:600;cursor:pointer;';
        footer.appendChild(input);
        footer.appendChild(sendBtn);

        modal.appendChild(header);
        modal.appendChild(messages);
        modal.appendChild(footer);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        sellerModalState.overlay = overlay;
        sellerModalState.messagesEl = messages;
        sellerModalState.sellerId = normalizedSellerId;
        sellerModalState.productId = normalizeProductId(productId);
        sellerModalState.inputEl = input;

        sellerModalState.keydownHandler = function(ev){
          if (ev.key === 'Escape') closeSellerChatModal();
        };
        document.addEventListener('keydown', sellerModalState.keydownHandler);

        overlay.addEventListener('click', (ev)=>{
          if (ev.target === overlay) closeSellerChatModal();
        });
        modal.addEventListener('click', (ev)=>ev.stopPropagation());
        closeBtn.addEventListener('click', closeSellerChatModal);

        const sendCurrentMessage = ()=>{
          const value = input.value.trim();
          if (!value) return;
          input.value = '';
          const localId = `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
          appendSellerModalMessage(value, true, null, new Date().toISOString(), localId);
          const ok = emitRiderChat({ message: value, sellerId: normalizedSellerId, productId: sellerModalState.productId, localId });
          if (!ok){
            const warn = document.createElement('div');
            warn.style.cssText = 'align-self:center;background:#fee2e2;color:#991b1b;padding:6px 10px;border-radius:8px;font-size:13px;';
            warn.textContent = 'Message failed to send. Check your connection.';
            messages.appendChild(warn);
            messages.scrollTop = messages.scrollHeight;
          }
        };

        sellerModalState.inputHandler = function(ev){
          if (ev.key === 'Enter' && !ev.shiftKey){
            ev.preventDefault();
            sendCurrentMessage();
          }
        };
        input.addEventListener('keydown', sellerModalState.inputHandler);
        sendBtn.addEventListener('click', sendCurrentMessage);

        loadSellerModalHistory(normalizedSellerId, productId || null);
        attachSellerModalSocketHandler();

        setTimeout(()=>input.focus(), 60);
      }

      function ensureSocket(){
        if (typeof io === 'undefined') return null;
        if (!riderSocket) {
          try {
            // Use polling transport to avoid noisy WebSocket upgrade errors in environments
            // where native websockets are not available. Socket.IO will still provide
            // realtime behavior over HTTP long-polling.
            riderSocket = io(riderAuthOptions({ transports:['polling'] }));
          } catch (e) {
            console.warn('rider socket.io init failed', e);
            return null;
          }
          riderSocket.on('connect', ()=>console.log('rider socket connected'));
          riderSocket.on('chat_message', (p)=>{
            try{
              if (!p) return;
              const sid = String(p.senderID||'');
              const rid = String(p.recipientID||'');
              const recRole = p.recipient_role||'';
              const rId = String(p.riderID||'');
              const sRole = p.sender_role||'';
              
              // Check if message is for this rider
              if (recRole === 'rider' || rId === String(RIDER_ID) || rid === String(RIDER_ID)){
                // Increment main sidebar badge if not on messages tab
                const messagesTab = document.getElementById('messages');
                if (!messagesTab || messagesTab.style.display === 'none') {
                    const mainBadge = document.getElementById('riderMsgBadge');
                    if (mainBadge) {
                        const cur = parseInt(mainBadge.textContent || '0') || 0;
                        mainBadge.textContent = String(cur + 1);
                        mainBadge.style.display = 'inline-block';
                    }
                }

                // If we have an active conversation, append if it matches
                if (activeContactID && activeContactType){
                  if ((activeContactType === 'seller' && sid === String(activeContactID)) || 
                      (activeContactType === 'user' && sid === String(activeContactID))){
                    appendRiderMessage(p);
                    // Mark as read immediately since we are viewing it
                    const peerRole = activeContactType;
                    const peerId = activeContactID;
                    const body = { peer_role: peerRole, peer_id: peerId };
                    // Also include productID if active
                    if (activeProductID) body.productID = activeProductID;
                    
                    fetch('/api/chat2/mark_read', { 
                        credentials: 'include', 
                        method: 'POST', 
                        headers: {'Content-Type':'application/json'}, 
                        body: JSON.stringify(body) 
                    }).catch(e => console.error('Failed to mark read on live message', e));

                  } else {
                    // Update unread badge for the sender
                    const senderType = sRole === 'seller' ? 'seller' : 'user';
                    if (!updateUnreadBadge(senderType, sid)) {
                        loadConversations();
                    }
                  }
                } else {
                  // No active conversation, update conversation list
                  loadConversations();
                }
              }
            }catch(e){ console.error('rider chat_message handler', e); }
          });
        }
        return riderSocket;
      }

      function messageBelongsToRider(message){
        if (!message) return false;
        const riderIdValue = message.riderID || message.riderId || message.rider_id || (message.rider && (message.rider.id || message.rider.riderID));
        if (riderIdValue && String(riderIdValue) === String(RIDER_ID)) return true;
        const senderRole = (message.sender_role || message.sender || '').toLowerCase();
        const recipientRole = (message.recipient_role || message.recipient || '').toLowerCase();
        const senderId = message.senderID || message.senderId || message.userID || message.userId;
        const recipientId = message.recipientID || message.recipientId;
        if (senderRole === 'rider' && senderId && String(senderId) === String(RIDER_ID)) return true;
        if (recipientRole === 'rider' && recipientId && String(recipientId) === String(RIDER_ID)) return true;
        return false;
      }

      async function loadConversations(){
        const listEl = document.getElementById('riderConvoItems');
        if (!listEl) return;
        listEl.innerHTML = '<div style="padding:12px;color:#64748b;">Loading…</div>';
        try{
          const r = await fetch('/api/rider/chat/conversations', { credentials: 'include' });
          const j = await r.json();
          if (!r.ok || !j.success){ 
            listEl.innerHTML = '<div style="padding:12px;color:#64748b;">No conversations</div>'; 
            return; 
          }
          const allConvos = (j.conversations || []).filter(c => contactAllowed(c.type, c.id));
          const convos = allConvos.filter(c => {
            if (activeMode === 'seller') return c.type === 'seller';
            if (activeMode === 'user') return c.type === 'user';
            return true;
          });
          if (!convos.length){ 
            listEl.innerHTML = '<div style="padding:12px;color:#64748b;">No conversations</div>'; 
            return; 
          }
          
          listEl.innerHTML = convos.map(c => {
            const name = c.name || c.username || c.sellername || (c.type === 'seller' ? 'Seller ' + c.id : 'User ' + c.id);
            const last = (c.lastMessage||'').slice(0,60);
            const unread = (c.unreadCount && c.unreadCount > 0) ? c.unreadCount : 0;
            const avatarClass = c.type === 'seller' ? 'seller' : 'user';
            const avatarIcon = c.type === 'seller'
              ? '<i class="fas fa-store"></i>'
              : '<i class="fas fa-user"></i>';
            return `<button class="convoItem" data-type="${c.type}" data-id="${c.id}" data-lastchatid="${c.lastChatID||''}" data-productid="${c.lastProductID||''}">
              <div class="avatar-wrapper" style="position:relative;">
                <div class="avatar ${avatarClass}">${avatarIcon}</div>
                <span class="unread-badge" style="${unread > 0 ? '' : 'display:none;'}">${unread}</span>
              </div>
              <div class="convo-copy"><div class="convo-name">${name}</div><div class="convo-meta">${last}</div></div>
            </button>`;
          }).join('');

          listEl.querySelectorAll('.convoItem').forEach(btn => {
            const type = btn.getAttribute('data-type');
            const id = btn.getAttribute('data-id');
            const name = btn.querySelector('div > div').textContent;
            btn.addEventListener('click', (e)=>{
              const prod = btn.getAttribute('data-productid') || null;
              if (type === 'seller') {
                openChatWithSeller(id, name, prod);
              } else if (type === 'user') {
                openChatWithUser(id, name, prod);
              }
            });
          });
        }catch(err){ 
          listEl.innerHTML = '<div style="padding:12px;color:#64748b;">Failed to load</div>'; 
        }
      }

      async function openChatWithSeller(sellerID, sellerName, productID){
        activeContactID = sellerID;
        activeContactType = 'seller';
        const msgEl = document.getElementById('riderChatMessages');
        const normalizedProductId = normalizeProductId(productID);
        activeProductID = normalizedProductId;
        setChatHeaderInfo(sellerName || (`Seller ${sellerID}`), `Seller ${sellerID}`);
        if (msgEl) msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">Loading conversation…</div>';
        ensureSocket();

        try{
          const q = [];
          if (RIDER_ID) q.push(`riderID=${encodeURIComponent(RIDER_ID)}`);
          if (sellerID) q.push(`sellerID=${encodeURIComponent(sellerID)}`);
          if (normalizedProductId) q.push(`productID=${encodeURIComponent(normalizedProductId)}`);
          const url = '/api/chat/history' + (q.length ? '?' + q.join('&') : '');
          const r = await fetch(url, { credentials:'include' });
          const j = await r.json();
          if (r.ok && j && j.success){
            msgEl.innerHTML = '';
            j.messages.forEach(m => {
              const payload = {
                message: m.messages || m.message || '',
                sender: m.sender || null,
                sender_role: m.sender_role || null,
                senderID: m.senderID || m.senderId || null,
                riderID: m.riderID || m.riderId || null,
                sellerID: m.sellerID || m.sellerId || null,
                messageID: m.chatID || m.chatId || m.id || null,
                created_at: m.created_at || null
              };
              if (messageBelongsToRider(payload)) appendRiderMessage(payload);
            });
          } else {
            msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">No messages</div>';
          }
        }catch(err){ 
          msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">Failed to load conversation</div>'; 
        }

        // Mark messages read (include productID if available)
        try{
          const body = { peer_role: 'seller', peer_id: sellerID };
          if (normalizedProductId) body.productID = normalizedProductId;
          fetch('/api/chat2/mark_read', { credentials: 'include', method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
        }catch(e){}
        
        // Hide unread badge
        try{
          const btn = document.querySelector(`#riderConvoItems .convoItem[data-type='seller'][data-id='${sellerID}']`);
          if (btn){ const b = btn.querySelector('.unread-badge'); if (b) b.style.display='none'; }
        }catch(e){}
      }

      async function openChatWithUser(userID, userName, productID){
        activeContactID = userID;
        activeContactType = 'user';
        const msgEl = document.getElementById('riderChatMessages');
        const normalizedProductId = normalizeProductId(productID);
        activeProductID = normalizedProductId;
        setChatHeaderInfo(userName || (`User ${userID}`), `User ${userID}`);
        if (msgEl) msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">Loading conversation…</div>';
        ensureSocket();

        try{
          const q = [];
          if (RIDER_ID) q.push(`riderID=${encodeURIComponent(RIDER_ID)}`);
          if (userID) q.push(`userID=${encodeURIComponent(userID)}`);
          if (normalizedProductId) q.push(`productID=${encodeURIComponent(normalizedProductId)}`);
          const url = '/api/chat/history' + (q.length ? '?' + q.join('&') : '');
          const r = await fetch(url, { credentials:'include' });
          const j = await r.json();
          if (r.ok && j && j.success){
            msgEl.innerHTML = '';
            j.messages.forEach(m => {
              const payload = {
                message: m.messages || m.message || '',
                sender: m.sender || null,
                sender_role: m.sender_role || null,
                senderID: m.senderID || m.senderId || null,
                riderID: m.riderID || m.riderId || null,
                userID: m.userID || m.userId || null,
                messageID: m.chatID || m.chatId || m.id || null,
                created_at: m.created_at || null
              };
              if (messageBelongsToRider(payload)) appendRiderMessage(payload);
            });
          } else {
            msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">No messages</div>';
          }
        }catch(err){ 
          msgEl.innerHTML = '<div style="padding:12px;color:#64748b;">Failed to load conversation</div>'; 
        }

        // Mark messages read (include productID if available)
        try{
          const body = { peer_role: 'user', peer_id: userID };
          if (normalizedProductId) body.productID = normalizedProductId;
          fetch('/api/chat2/mark_read', { credentials: 'include', method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
        }catch(e){}
        
        // Hide unread badge
        try{
          const btn = document.querySelector(`#riderConvoItems .convoItem[data-type='user'][data-id='${userID}']`);
          if (btn){ const b = btn.querySelector('.unread-badge'); if (b) b.style.display='none'; }
        }catch(e){}
      }

      function appendRiderMessage(m){
        const messagesEl = document.getElementById('riderChatMessages');
        if (!messagesEl) return;

        const text = m.messages || m.message || '';
        const msgId = m.messageID || m.chatID || m.chatId || m.id || null;
        const localId = m.localId || null; // client-provided optimistic id

        // Determine if message came from this rider
        let isRider = false;
        try{
          const senderRole = m.sender_role || m.sender || '';
          const senderId = m.senderID || m.senderId || m.userID || m.userId || null;
          if (senderRole === 'rider' || (senderId && String(senderId) === String(RIDER_ID))){
            isRider = true;
          }
        }catch(e){ isRider = false; }

        // Dedup / reconcile logic:
        // 1) If server provided msgId and an element with that id exists -> skip
        try{
          if (msgId && messagesEl.querySelector(`[data-message-id="${msgId}"]`)) return;
        }catch(e){}

        // 2) If server echo provides a msgId but an optimistic local element exists with same localId -> convert it
        try{
          if (msgId && localId){
            const localEl = messagesEl.querySelector(`[data-message-local-id="${localId}"]`);
            if (localEl){
              localEl.setAttribute('data-message-id', String(msgId));
              localEl.removeAttribute('data-message-local-id');
              localEl.removeAttribute('data-local');
              // ensure classes
              localEl.classList.toggle('rider-bubble', !!isRider);
              localEl.classList.toggle('seller-bubble', !isRider && (m.sender_role === 'seller'));
              localEl.classList.toggle('user-bubble', !isRider && (m.sender_role === 'user'));
              // update timestamp if present
              if (m.created_at){
                const meta = localEl.querySelector('.meta-ts');
                if (meta) meta.textContent = String(m.created_at).slice(0,19);
                else { const md = document.createElement('div'); md.className='meta-ts'; md.style.cssText='font-size:12px;color:#94a3b8;margin-top:4px;'; md.textContent=String(m.created_at).slice(0,19); localEl.appendChild(md); }
              }
              messagesEl.scrollTop = messagesEl.scrollHeight;
              return;
            }
          }
        }catch(e){}

        // 3) If server echo has no msgId, try to find a local optimistic element with same text+sender and confirm it
        try{
          if (!msgId){
            const candidate = Array.from(messagesEl.querySelectorAll('[data-local="1"]')).find(el => el.textContent === String(text) && el.getAttribute('data-sender') === (isRider ? 'rider' : (m.sender_role || 'other')));
            if (candidate){
              candidate.removeAttribute('data-local');
              candidate.classList.toggle('rider-bubble', !!isRider);
              candidate.classList.toggle('seller-bubble', !isRider && (m.sender_role === 'seller'));
              candidate.classList.toggle('user-bubble', !isRider && (m.sender_role === 'user'));
              // set timestamp if present
              if (m.created_at){ const md = document.createElement('div'); md.className='meta-ts'; md.style.cssText='font-size:12px;color:#94a3b8;margin-top:4px;'; md.textContent=String(m.created_at).slice(0,19); candidate.appendChild(md); }
              messagesEl.scrollTop = messagesEl.scrollHeight;
              return;
            }
          }
        }catch(e){}

        // Otherwise append a fresh element
        const div = document.createElement('div');
        if (msgId) div.setAttribute('data-message-id', String(msgId));
        if (localId) { div.setAttribute('data-message-local-id', String(localId)); div.setAttribute('data-local','1'); }
        const content = document.createElement('div');
        content.textContent = text;
        const ts = m.created_at || m.ts || null;
        const messageProductId = normalizeProductId(m.productID || m.productId || m.product_id);
        if (messageProductId) {
          activeProductID = messageProductId;
        }
        const meta = document.createElement('div');
        meta.className = 'meta-ts';
        meta.style.cssText = 'font-size:12px;color:#94a3b8;margin-top:4px;';
        if (ts){ meta.textContent = String(ts).toString().slice(0,19); }
        div.appendChild(content);
        if (ts) div.appendChild(meta);

        if (isRider) {
          div.setAttribute('data-sender', 'rider');
          div.classList.add('rider-bubble');
        } else {
          div.setAttribute('data-sender', m.sender_role || 'other');
          if (m.sender_role === 'seller') div.classList.add('seller-bubble');
          else if (m.sender_role === 'user') div.classList.add('user-bubble');
        }

        const baseStyle = 'max-width:78%;padding:8px 12px;border-radius:12px;font-size:14px;line-height:1.3;';
        div.style.cssText = isRider ? (baseStyle + 'align-self:flex-end;background:#0b73ff;color:#ffffff;') : (baseStyle + 'align-self:flex-start;background:#f1f5f9;color:#0f1724;');
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }

      function updateUnreadBadge(type, id){
        try{
          const btn = document.querySelector(`#riderConvoItems .convoItem[data-type='${type}'][data-id='${id}']`);
          if (btn){
            const badge = btn.querySelector('.unread-badge');
            if (badge){
              const cur = parseInt(badge.textContent||'0')||0;
              badge.textContent = String(cur + 1);
              badge.style.display = '';
            }
            return true;
          }
          return false;
        }catch(e){ return false; }
      }

      function bindModeButtons(){
        const modesRoot = document.getElementById('riderChatModes');
        if (!modesRoot) return;
        const buttons = Array.from(modesRoot.querySelectorAll('.rider-chat-mode-btn'));
        buttons.forEach(btn => {
          btn.addEventListener('click', ()=>{
            const mode = (btn.getAttribute('data-mode') || 'all').toLowerCase();
            if (mode === activeMode) return;
            activeMode = (mode === 'seller' || mode === 'user') ? mode : 'all';
            buttons.forEach(b => b.classList.toggle('active', b === btn));
            try{
              if (!activeContactID){
                const titleEl = document.getElementById('riderChatHeaderTitle');
                const subEl = document.getElementById('riderChatHeaderSubtitle');
                if (titleEl && subEl){
                  if (activeMode === 'seller'){
                    titleEl.textContent = 'Seller conversations';
                    subEl.textContent = 'View and chat with sellers for your orders';
                  } else if (activeMode === 'user'){
                    titleEl.textContent = 'Customer conversations';
                    subEl.textContent = 'View and chat with customers assigned to you';
                  } else {
                    titleEl.textContent = 'Choose a conversation';
                    subEl.textContent = 'Select a seller or user to start chatting';
                  }
                }
              }
            }catch(e){}
            loadConversations();
          });
        });
      }

      // Expose functions globally for order card buttons and chat popups
      window.openRiderChatWithSeller = openChatWithSeller;
      window.openRiderChatWithUser = openChatWithUser;
      window.openRiderSellerChatModal = openSellerChatModal;
      window.closeRiderSellerChatModal = closeSellerChatModal;
      window.emitRiderChatMessage = emitRiderChat;

      // Event listeners - attach immediately since this script runs inside the
      // outer DOMContentLoaded handler. Avoid registering a nested DOMContentLoaded
      // listener which would not fire if added after the event.
      (function(){
         const btn = document.getElementById('riderChatsBtn');
         if (btn) btn.addEventListener('click', (e)=>{ 
           e.preventDefault(); 
           if (typeof window.showRiderTab === 'function') window.showRiderTab('messages');
           else location.hash = '#messages';
           try{ 
             const b=document.getElementById('riderChatsBadge'); 
             if (b){ b.textContent='0'; b.style.display='none'; } 
           }catch(err){} 
         });

        async function sendRiderMessage(text){
          const v = String(text || '').trim();
          if (!v || !activeContactID || !activeContactType) return;
          
          const inputEl = document.getElementById('riderChatInput');
          if (inputEl) inputEl.value = '';

          const localId = `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;

          appendRiderMessage({ 
            sender_role:'rider', 
            message:v, 
            messages:v, 
            recipient_role:activeContactType, 
            recipientID:String(activeContactID), 
            created_at:new Date().toISOString(),
            localId
          });

          const s = ensureSocket();
          if (!s) return;
          try{ 
            const normalizedProductId = normalizeProductId(activeProductID);
            const payload = activeContactType === 'seller' 
              ? { message: v, sellerID: activeContactID, riderID: RIDER_ID, localId }
              : { message: v, userID: activeContactID, riderID: RIDER_ID, localId };
            if (normalizedProductId) payload.productID = normalizedProductId;
            s.emit('chat_message', payload); 
          }
          catch(e){
            console.error(e);
            const el = document.getElementById('riderChatMessages');
            if (el){ 
              const err = document.createElement('div'); 
              err.style.cssText='max-width:68%;padding:6px 10px;border-radius:8px;margin:6px 0;font-size:0.9rem;align-self:center;background:#fee2e2;color:#7f1d1d;'; 
              err.textContent='Failed to send'; 
              el.appendChild(err); 
            }
          }
        }

        document.getElementById('riderChatSend')?.addEventListener('click', async ()=>{
          const inputEl = document.getElementById('riderChatInput');
          const v = inputEl ? inputEl.value : '';
          await sendRiderMessage(v);
        });

        document.getElementById('riderChatInput')?.addEventListener('keydown', async function(e){
          try{
            if (e.key === 'Enter' && !e.shiftKey){
              e.preventDefault();
              const v = this.value;
              await sendRiderMessage(v);
            }
          }catch(err){ console.error('enter key send error', err); }
        });
        bindModeButtons();
      })();

      async function ensureMessagesTabReady(){
        await loadConversations();
        messagesTabBootstrapped = true;
      }

      document.addEventListener('riderTabChange', (event)=>{
        if (event.detail && event.detail.tab === 'messages'){
          // Clear main badge
          const mainBadge = document.getElementById('riderMsgBadge');
          if (mainBadge) {
              mainBadge.style.display = 'none';
              mainBadge.textContent = '0';
          }

          if (!messagesTabBootstrapped){
            ensureMessagesTabReady();
          } else {
            loadConversations();
          }
          try{ const b=document.getElementById('riderChatsBadge'); if (b){ b.textContent='0'; b.style.display='none'; } }catch(e){}
        }
      });

      if (document.getElementById('messages')?.classList.contains('active')){
        ensureMessagesTabReady();
      }
    })();

    // Safety check: ensure sidebar-open class is removed on desktop to prevent unwanted backdrop
    function checkSidebarState(){
      if (window.innerWidth > 900 && document.body.classList.contains('sidebar-open')){
        document.body.classList.remove('sidebar-open');
        const bd = document.getElementById('sidebarBackdrop');
        if (bd) bd.classList.remove('visible');
      }
    }
    checkSidebarState();
    window.addEventListener('resize', checkSidebarState);

  });

