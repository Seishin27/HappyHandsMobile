let ordersChartInstance = null;
let deliveredChartInstance = null;
const adminNotifState = {
  timer: null,
  socket: null,
  payload: null,
  unreadIds: [],
  markInFlight: false,
  elements: {},
};

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, function (ch) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return map[ch] || ch;
  });
}

function formatDateTime(value) {
  if (!value) return '';
  try {
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleString();
    }
  } catch (err) {
    console.debug('formatDateTime error', err);
  }
  return String(value).replace('T', ' ').slice(0, 19);
}

function adminSocketOptions(base) {
  const opts = base ? Object.assign({}, base) : {};
  opts.withCredentials = true;
  const auth = Object.assign({}, opts.auth || {});
  auth.role = 'admin';
  opts.auth = auth;
  return opts;
}

function destroyChart(instance) {
  if (instance && typeof instance.destroy === 'function') {
    instance.destroy();
  }
}

function setAdminChartState(elOrId, message) {
  var el = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
  if (!el) return;
  if (typeof message === 'string') {
    el.textContent = message;
  }
  el.classList.toggle('hidden', !message);
}

function renderOrdersChart(ctx, labels, sales, commissions, orders, delivered) {
  if (!ctx) return;
  destroyChart(ordersChartInstance);
  ordersChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Total Sales (₱)',
          data: sales,
          borderColor: '#7c3aed',
          backgroundColor: 'rgba(124,58,237,0.08)',
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'Admin Commissions (₱)',
          data: commissions,
          borderColor: '#0b73ff',
          backgroundColor: 'rgba(11,115,255,0.06)',
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'Total Orders',
          data: orders,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          tension: 0.3,
          yAxisID: 'y1',
          borderDash: [5, 5]
        },
        {
          label: 'Delivered Parcels',
          data: delivered,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.3,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || '';
              if (label) label += ': ';
              if (context.parsed.y !== null) {
                if (context.dataset.yAxisID === 'y') {
                  label += '₱' + context.parsed.y.toFixed(2);
                } else {
                  label += context.parsed.y;
                }
              }
              return label;
            }
          }
        }
      },
      scales: {
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: { display: true, text: 'Amount (₱)' }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: { display: true, text: 'Count' },
          grid: { drawOnChartArea: false }
        }
      }
    }
  });
}

function renderDeliveredChart(ctx, labels, delivered) {
  if (!ctx) return;
  destroyChart(deliveredChartInstance);
  deliveredChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Delivered Parcels',
        data: delivered,
        backgroundColor: '#10b981',
        borderRadius: 4,
        barPercentage: 0.6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: { display: true, text: 'Successful Deliveries per Day (Last 30 Days)' }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: 'Count' }
        }
      }
    }
  });
}

async function fetchAdminNotifications() {
  try {
    const res = await fetch('/api/admin/notifications', { credentials: 'same-origin' });
    if (!res.ok) return null;
    const data = await res.json().catch(() => null);
    if (!data || data.success !== true) return null;
    return data;
  } catch (err) {
    console.error('Failed to fetch admin notifications', err);
    return null;
  }
}

function renderAdminNotifications(payload) {
  const elements = adminNotifState.elements || {};
  const listEl = elements.list;
  const badgeEl = elements.badge;
  const markBtn = elements.markAll;

  adminNotifState.payload = payload || null;

  if (!listEl) {
    return;
  }

  if (!payload) {
    listEl.innerHTML = '<div class="notif-empty">Unable to load notifications</div>';
    if (badgeEl) badgeEl.style.display = 'none';
    if (markBtn) markBtn.disabled = true;
    return;
  }

  const notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
  const reportAlerts = Array.isArray(payload.report_alerts) ? payload.report_alerts : [];
  const unresolvedCount = Number(payload.unresolved_reports_count || 0);
  const unreadCount = Number(payload.unread_count || 0);
  const unreadIds = Array.isArray(payload.unread_ids) ? payload.unread_ids.map(String) : [];
  adminNotifState.unreadIds = unreadIds;

  const vatItems = notifications.filter(function (item) {
    return String(item && item.type ? item.type : '').toLowerCase() === 'vat';
  });
  const otherItems = notifications.filter(function (item) {
    return String(item && item.type ? item.type : '').toLowerCase() !== 'vat';
  });

  const parts = [];

  if (unresolvedCount > 0) {
    parts.push('<div class="notif-pill alert"><span>Unresolved reports</span><span>' + unresolvedCount + '</span></div>');
  }

  if (reportAlerts.length) {
    parts.push('<div class="notif-section-title">Latest Reports</div>');
    reportAlerts.forEach(function (item) {
      const idLabel = item && item.id != null ? String(item.id) : '';
      const title = 'Report #' + escapeHtml(idLabel);
      const complaint = escapeHtml(item && item.complaint_type ? item.complaint_type : 'General report');
      const reporter = item && item.reporter_name ? escapeHtml(item.reporter_name) : '';
      const status = escapeHtml(item && item.status ? item.status : 'Open');
      const offense = item && item.offense_level ? ('Level ' + escapeHtml(String(item.offense_level))) : '';
      const targetParts = [];
      if (item && item.reported_shop_id) {
        targetParts.push('Seller #' + escapeHtml(String(item.reported_shop_id)));
      }
      if (item && item.reported_product_id) {
        targetParts.push('Product #' + escapeHtml(String(item.reported_product_id)));
      }
      const target = targetParts.join(' &bull; ');
      const metaPieces = [status, target, offense].filter(function (str) { return !!str; });
      const metaLine = metaPieces.join(' &bull; ');
      const timestamp = formatDateTime(item && item.created_at ? item.created_at : '');

      const rows = ['<div class="notif-card">'];
      rows.push('<div class="notif-card-title">' + title + '</div>');
      const bodyDetail = reporter ? (complaint + ' &middot; ' + reporter) : complaint;
      rows.push('<div class="notif-card-body">' + bodyDetail + '</div>');
      if (metaLine) {
        rows.push('<div class="notif-card-meta">' + metaLine + '</div>');
      }
      if (timestamp) {
        rows.push('<div class="notif-card-meta">' + escapeHtml(timestamp) + '</div>');
      }
      rows.push('</div>');
      parts.push(rows.join(''));
    });
  }

  if (vatItems.length) {
    parts.push('<div class="notif-section-title">Platform Fee Updates</div>');
    vatItems.forEach(function (item) {
      const title = escapeHtml(item && item.title ? item.title : 'Platform Fee');
      const body = escapeHtml(item && item.body ? item.body : '');
      const timestamp = formatDateTime(item && item.created_at ? item.created_at : '');
      const rows = ['<div class="notif-card">'];
      rows.push('<div class="notif-card-title">' + title + '</div>');
      if (body) {
        rows.push('<div class="notif-card-body">' + body + '</div>');
      }
      if (timestamp) {
        rows.push('<div class="notif-card-meta">' + escapeHtml(timestamp) + '</div>');
      }
      rows.push('</div>');
      parts.push(rows.join(''));
    });
  }

  if (otherItems.length) {
    parts.push('<div class="notif-section-title">Updates</div>');
    otherItems.forEach(function (item) {
      const title = escapeHtml(item && item.title ? item.title : 'Notification');
      const body = escapeHtml(item && item.body ? item.body : '');
      const timestamp = formatDateTime(item && item.created_at ? item.created_at : '');
      const rows = ['<div class="notif-card">'];
      rows.push('<div class="notif-card-title">' + title + '</div>');
      if (body) {
        rows.push('<div class="notif-card-body">' + body + '</div>');
      }
      if (timestamp) {
        rows.push('<div class="notif-card-meta">' + escapeHtml(timestamp) + '</div>');
      }
      rows.push('</div>');
      parts.push(rows.join(''));
    });
  }

  if (!parts.length) {
    listEl.innerHTML = '<div class="notif-empty">No notifications</div>';
  } else {
    listEl.innerHTML = parts.join('');
  }

  const badgeTotal = unreadCount + (unresolvedCount > 0 ? unresolvedCount : 0);
  if (badgeEl) {
    if (badgeTotal > 0) {
      badgeEl.textContent = badgeTotal > 99 ? '99+' : String(badgeTotal);
      badgeEl.style.display = 'inline-flex';
    } else {
      badgeEl.style.display = 'none';
    }
  }

  if (markBtn) {
    // Enable button if there are any notifications, regardless of read status
    markBtn.disabled = notifications.length === 0;
  }
}

async function markAdminNotificationsRead(options) {
  const payload = {};
  if (options && options.markAll) {
    payload.mark = 'all';
  } else if (options && Array.isArray(options.ids) && options.ids.length) {
    payload.ids = options.ids;
  } else {
    return false;
  }

  try {
    const res = await fetch('/api/admin/notifications/mark_read', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok || !data || data.success !== true) {
      return false;
    }
    return true;
  } catch (err) {
    console.error('Failed to mark admin notifications as read', err);
    return false;
  }
}

function initAdminNotificationSocket(onNotification) {
  if (typeof io === 'undefined') {
    return;
  }
  const body = document.body;
  if (!body || !body.classList.contains('admin-body')) {
    return;
  }
  const adminId = body.dataset ? body.dataset.adminId : null;
  if (adminId === undefined || adminId === null || adminId === '') {
    return;
  }

  try {
    const socket = io(adminSocketOptions({ transports: ['polling'] }));
    adminNotifState.socket = socket;
    socket.on('connect', function () {
      try {
        socket.emit('join', { room: 'admin_' + adminId });
      } catch (err) {
        console.debug('admin notification join error', err);
      }
    });
    socket.on('notification', function (payload) {
      try {
        if (!payload || payload.recipient_type !== 'admin') {
          return;
        }
        if (typeof onNotification === 'function') {
          onNotification(payload);
        }
      } catch (err) {
        console.debug('admin notification handler error', err);
      }
    });
  } catch (err) {
    console.debug('Socket.IO admin notifications unavailable', err);
  }
}

function initAdminNotifications() {
  const btn = document.getElementById('adminNotifBtn');
  const menu = document.getElementById('adminNotifMenu');
  const list = document.getElementById('adminNotifList');
  const badge = document.getElementById('adminNotifBadge');
  const markAll = document.getElementById('adminNotifMarkAll');

  if (!btn || !menu || !list || !badge) {
    return;
  }

  adminNotifState.elements = { btn, menu, list, badge, markAll };

  let pollDelay = 15000;

  async function loadAndRender(reason) {
    const data = await fetchAdminNotifications();
    if (data) {
      renderAdminNotifications(data);
    } else if (!adminNotifState.payload) {
      list.innerHTML = '<div class="notif-empty">Unable to load notifications</div>';
    }
    schedule(pollDelay);
  }

  function schedule(delay) {
    if (adminNotifState.timer) {
      clearTimeout(adminNotifState.timer);
    }
    adminNotifState.timer = setTimeout(function () {
      loadAndRender('poll');
    }, delay);
  }

  function closeMenu() {
    menu.style.display = 'none';
  }

  async function markUnreadIfNeeded() {
    if (adminNotifState.markInFlight) {
      return;
    }
    const ids = Array.isArray(adminNotifState.unreadIds) ? adminNotifState.unreadIds.slice() : [];
    if (!ids.length) {
      return;
    }
    adminNotifState.markInFlight = true;
    try {
      const ok = await markAdminNotificationsRead({ ids });
      if (ok && adminNotifState.payload) {
        adminNotifState.payload.unread_count = 0;
        adminNotifState.payload.unread_ids = [];
        if (Array.isArray(adminNotifState.payload.notifications)) {
          adminNotifState.payload.notifications = adminNotifState.payload.notifications.map(function (item) {
            if (!item) return item;
            const itemId = item.id != null ? String(item.id) : null;
            if (itemId && ids.includes(itemId)) {
              return Object.assign({}, item, { is_read: 1 });
            }
            return item;
          });
        }
        renderAdminNotifications(adminNotifState.payload);
      }
    } finally {
      adminNotifState.markInFlight = false;
    }
  }

  function toggleMenu(force) {
    const shouldShow = force === undefined ? menu.style.display !== 'block' : !!force;
    menu.style.display = shouldShow ? 'block' : 'none';
    if (shouldShow) {
      // Mark all as read immediately when opening
      markAdminNotificationsRead({ markAll: true }).then(function(ok) {
        if (ok && adminNotifState.payload) {
          adminNotifState.payload.unread_count = 0;
          adminNotifState.payload.unread_ids = [];
          adminNotifState.unreadIds = [];
          if (Array.isArray(adminNotifState.payload.notifications)) {
            adminNotifState.payload.notifications = adminNotifState.payload.notifications.map(function (item) {
              return item ? Object.assign({}, item, { is_read: 1 }) : item;
            });
          }
          renderAdminNotifications(adminNotifState.payload);
        }
      });
    }
  }

  btn.addEventListener('click', function (ev) {
    ev.preventDefault();
    ev.stopPropagation();
    toggleMenu();
  });

  document.addEventListener('click', function (ev) {
    if (!menu.contains(ev.target) && !btn.contains(ev.target)) {
      closeMenu();
    }
  });

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      closeMenu();
    }
  });

  if (markAll) {
    markAll.addEventListener('click', async function (ev) {
      ev.preventDefault();
      if (markAll.disabled) {
        return;
      }
      markAll.disabled = true;
      const ok = await markAdminNotificationsRead({ markAll: true });
      if (!ok) {
        alert('Failed to mark notifications as read.');
        markAll.disabled = false;
        return;
      }
      if (adminNotifState.payload) {
        adminNotifState.payload.unread_count = 0;
        adminNotifState.payload.unread_ids = [];
        adminNotifState.unreadIds = [];
        if (Array.isArray(adminNotifState.payload.notifications)) {
          adminNotifState.payload.notifications = adminNotifState.payload.notifications.map(function (item) {
            return item ? Object.assign({}, item, { is_read: 1 }) : item;
          });
        }
        renderAdminNotifications(adminNotifState.payload);
      }
    });
  }

  loadAndRender('init');

  initAdminNotificationSocket(function () {
    loadAndRender('socket');
  });
}

async function loadAdminCharts() {
  const ordersCtx = document.getElementById('ordersChart')?.getContext('2d');
  const deliveredCtx = document.getElementById('deliveredChart')?.getContext('2d');
  if (!ordersCtx && !deliveredCtx) return;

  try {
    setAdminChartState('ordersChartState', 'Loading orders & revenue…');
    setAdminChartState('deliveredChartState', 'Loading delivered parcels…');
    const res = await fetch('/api/admin/stats_chart', { credentials: 'same-origin' });
    if (!res.ok) {
      console.error('Failed to fetch admin stats chart', res.status);
      setAdminChartState('ordersChartState', 'Unable to load chart data.');
      setAdminChartState('deliveredChartState', 'Unable to load chart data.');
      return;
    }
    const j = await res.json();
    const labels = Array.isArray(j.labels) ? j.labels : [];
    const sales = Array.isArray(j.sales) ? j.sales : [];
    const commissions = Array.isArray(j.commissions) ? j.commissions : [];
    const orders = Array.isArray(j.orders) ? j.orders : [];
    const delivered = Array.isArray(j.delivered) ? j.delivered : [];

    if (!labels.length) {
      setAdminChartState('ordersChartState', 'No chart data yet.');
      setAdminChartState('deliveredChartState', 'No chart data yet.');
      destroyChart(ordersChartInstance);
      destroyChart(deliveredChartInstance);
      ordersChartInstance = null;
      deliveredChartInstance = null;
      return;
    }

    setAdminChartState('ordersChartState', '');
    setAdminChartState('deliveredChartState', '');

    if (ordersCtx) renderOrdersChart(ordersCtx, labels, sales, commissions, orders, delivered);
    if (deliveredCtx) renderDeliveredChart(deliveredCtx, labels, delivered);
  } catch (err) {
    console.error('Error loading admin charts', err);
    setAdminChartState('ordersChartState', 'Unable to load chart data.');
    setAdminChartState('deliveredChartState', 'Unable to load chart data.');
  }
}

    document.addEventListener('DOMContentLoaded', loadAdminCharts);
    document.addEventListener('DOMContentLoaded', initAdminNotifications);

        // Sidebar navigation - client-side tab switching
        (function(){
            const links = document.querySelectorAll('.sidebar-nav .nav-link');
            const sections = document.querySelectorAll('.tab-content');

            function show(id) {
                // toggle nav active
                links.forEach(a => {
                    const li = a.parentElement;
                    if (a.dataset.target === id) li.classList.add('active'); else li.classList.remove('active');
                });
                // show section
                sections.forEach(s => s.classList.toggle('active', s.id === id));
                // update URL hash without scrolling
                history.replaceState(null, '', `#${id}`);
            }

            // click handlers
            links.forEach(a => {
                a.addEventListener('click', function(e){
                    e.preventDefault();
                    const target = this.dataset.target;
                    show(target);
                });
            });

            // initial: respect hash if present
            const initial = location.hash ? location.hash.replace('#','') : 'dashboard';
            const valid = Array.from(sections).some(s => s.id === initial) ? initial : 'dashboard';
            show(valid);
        })();

        // Profile dropdown (unchanged)
        (function(){
            const btn = document.getElementById('profileBtn');
            const menu = document.getElementById('profileMenu');

            if (btn && menu) {
                function toggle(show) {
                    const visible = (show === undefined) ? (menu.style.display !== 'none') : show;
                    menu.style.display = visible ? 'block' : 'none';
                    btn.setAttribute('aria-expanded', visible ? 'true' : 'false');
                    menu.setAttribute('aria-hidden', visible ? 'false' : 'true');
                }

                btn.addEventListener('click', function(e){
                    e.preventDefault();
                    toggle(!(menu.style.display !== 'none'));
                });
                document.addEventListener('click', function(e){
                    if (!btn.contains(e.target) && !menu.contains(e.target)) toggle(false);
                });
                document.addEventListener('keydown', function(e){
                    if (e.key === 'Escape') toggle(false);
                });
            }
        })();

        // replace demo handlers with real fetch calls (legacy rows only)
        document.addEventListener('click', async function(e){
          if (e.target.matches('.btn-approve') || e.target.matches('.btn-reject')) {
            const btn = e.target;
            const legacyRow = btn.closest('.approve-row');
            if (!legacyRow) return; // modern tables handled elsewhere
            const id = btn.dataset.id;
            const action = btn.matches('.btn-approve') ? 'approve' : 'reject';
            if (action === 'reject'){
              var ok = false;
              try{ ok = window.confirmAction ? await window.confirmAction({ title: 'Reject this seller application?', icon: 'warning', confirmButtonText: 'Reject', cancelButtonText: 'Cancel' }) : window.confirm('Reject this seller application?'); }catch(e){ ok = window.confirm('Reject this seller application?'); }
              if (!ok) return;
            }
            btn.disabled = true;
            fetch(`/admin/sellers/${encodeURIComponent(id)}/update`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest' },
              body: new URLSearchParams({ action })
            }).then(r => r.json()).then(j => {
              if (j.success) {
                const row = legacyRow;
                if (row) row.querySelector('.status-label').textContent = j.status;
              } else {
                alert(j.msg || 'Action failed');
              }
            }).catch(err => {
              console.error(err);
              alert('Network error');
            }).finally(()=> btn.disabled = false);
          }
        });

    // Add logout handler (same behaviour as index.html.handleLogout)
    async function handleLogoutAdmin() {
        try {
        const response = await fetch('/admin-logout', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' }
            });

            let data = null;
            try { data = await response.json(); } catch (e) { /* no JSON */ }

            if (!response.ok) {
                console.error('Logout failed:', response.status, data);
                const serverMsg = data && (data.msg || data.message || data.error) ? (data.msg || data.message || data.error) : `Status ${response.status}`;
                alert('Logout failed: ' + serverMsg);
                return;
            }

            // Redirect to login (server-side login route)
          window.location.href = "/login";
        } catch (err) {
            console.error('Logout network error:', err);
            alert('Logout failed: network error. See console for details.');
        }
    }

    // wire the button (safe check)
    document.addEventListener('DOMContentLoaded', function () {
        const lb = document.getElementById('logoutBtn');
        if (lb) lb.addEventListener('click', function (e) {
            e.preventDefault();
            handleLogoutAdmin();
        });
    });

  // replicate index.html dropdown behavior on admin dashboard
  document.addEventListener('DOMContentLoaded', function () {
    const ActBtn = document.getElementById('ActBtn');
    const userDropdown = document.getElementById('userDropdown');

    if (ActBtn && userDropdown) {
      ActBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        userDropdown.classList.toggle('show');
        userDropdown.style.display = userDropdown.style.display === 'block' ? 'none' : 'block';
      });

      // close dropdown when clicking outside
      document.addEventListener('click', function (e) {
        if (!ActBtn.contains(e.target) && !userDropdown.contains(e.target)) {
          userDropdown.style.display = 'none';
          userDropdown.classList.remove('show');
        }
      });
    }

    // hook logout button to existing admin logout handler
    const adminLogoutBtn = document.getElementById('adminLogoutBtn');
    if (adminLogoutBtn) {
      adminLogoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        // use your existing handleLogoutAdmin() defined in this template
        if (typeof handleLogoutAdmin === 'function') {
          handleLogoutAdmin();
        } else {
          // fallback to POST /logout then redirect to login
          fetch('/admin-logout', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } })
            .then(res => { if (res.ok) window.location.href = "/login"; else alert('Logout failed'); })
            .catch(() => alert('Logout network error'));
        }
      });
    }
  });

  // VAT widgets removed; no extra handlers required

async function confirmAdminDecision(options) {
  const fallbackTitle = (options && options.title) || 'Are you sure?';
  const opts = Object.assign({
    title: fallbackTitle,
    text: options && options.text ? options.text : '',
    icon: options && options.icon ? options.icon : 'warning',
    confirmButtonText: (options && options.confirmButtonText) || 'Yes',
    cancelButtonText: (options && options.cancelButtonText) || 'Cancel'
  }, options || {});

  try {
    if (window.confirmAction) {
      return await window.confirmAction(opts);
    }
    if (window.Swal && typeof window.Swal.fire === 'function') {
      const res = await window.Swal.fire({
        title: opts.title,
        text: opts.text,
        icon: opts.icon,
        showCancelButton: true,
        confirmButtonText: opts.confirmButtonText,
        cancelButtonText: opts.cancelButtonText,
        reverseButtons: true
      });
      return !!res.isConfirmed;
    }
  } catch (err) {
    console.warn('Confirmation prompt failed, falling back to native confirm.', err);
  }
  return window.confirm(opts.title + (opts.text ? '\n\n' + opts.text : ''));
}

async function postAction(id, action, btn) {
  if (!id) { alert('Missing seller id'); return; }
  btn.disabled = true;
  const origText = btn.textContent;
  btn.textContent = action === 'approve' ? 'Approving…' : 'Rejecting…';

  try {
    const res = await fetch(`/admin/sellers/${encodeURIComponent(id)}/update`, {
      method: 'POST',
      credentials: 'same-origin',            // important to send session cookie
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });

    // parse safe
    const json = await res.json().catch(() => null);

    if (!res.ok) {
      const msg = json && json.msg ? json.msg : `Server error: ${res.status}`;
      alert(msg);
      btn.textContent = origText;
      btn.disabled = false;
      return;
    }

    if (json && json.success) {
      const row = document.querySelector(`tr[data-id="${id}"]`);
      if (row) {
        row.remove();
        const tbody = document.querySelector('#approveList tbody');
        if (tbody && !tbody.children.length) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">No pending store approvals</td></tr>';
        }
      }
      const swalPayload = {
        icon: 'success',
        title: action === 'approve' ? 'Store Approved' : 'Store Rejected',
        text: action === 'approve' ? 'The store can now start selling.' : 'The store application was rejected.',
        confirmButtonText: 'OK'
      };
      if (window.Swal) {
        await Swal.fire(swalPayload);
      } else {
        alert(swalPayload.text);
      }
      if (action === 'approve') {
        setTimeout(() => window.location.reload(), 300);
      }
      btn.textContent = action === 'approve' ? 'Approved' : 'Rejected';
    } else {
      alert((json && json.msg) || 'Unknown response');
      btn.textContent = origText;
      btn.disabled = false;
    }
  } catch (err) {
    console.error('Network or fetch error', err);
    alert('Network error');
    btn.textContent = origText;
    btn.disabled = false;
  }
}

document.addEventListener('click', async function(e){
  if (!(e.target.matches('.btn-approve') || e.target.matches('.btn-reject'))) return;
  const btn = e.target;
  const id = btn.dataset.id;
  const action = btn.matches('.btn-approve') ? 'approve' : 'reject';
  if (!id) return;

  const approveTexts = {
    title: 'Approve this store?',
    text: 'The store owner will be able to list products and receive orders.',
    icon: 'question',
    confirmButtonText: 'Yes, approve'
  };
  const rejectTexts = {
    title: 'Reject this store?',
    text: 'The store application will be removed from the pending list.',
    icon: 'warning',
    confirmButtonText: 'Yes, reject'
  };

  const confirmed = await confirmAdminDecision(action === 'approve' ? approveTexts : rejectTexts);
  if (!confirmed) return;

  postAction(id, action, btn);
});

// Featured approve/reject actions
document.addEventListener('click', async function(e){
  if (e.target.matches('.btn-approve-featured') || e.target.matches('.btn-reject-featured')) {
    const btn = e.target;
    const id = btn.dataset.id;
    const action = btn.matches('.btn-approve-featured') ? 'approve' : 'reject';
    btn.disabled = true;
    try {
      const res = await fetch(`/admin/featured/${encodeURIComponent(id)}/update`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      });
      const j = await res.json().catch(()=>null);
      if (!res.ok || !j || !j.success) {
        alert((j && j.msg) || 'Action failed');
        return;
      }
      const row = btn.closest('tr');
      if (row) row.remove();
      alert(action === 'approve' ? 'Approved for homepage' : 'Rejected');
    } catch (err) {
      console.error(err);
      alert('Network error');
    } finally {
      btn.disabled = false;
    }
  }
});

// Remove featured
document.addEventListener('click', async function(e){
  if (!e.target.matches('.btn-remove-featured')) return;
  const btn = e.target;
  const id = btn.dataset.id;
  if (!id) return;
  var ok = false;
  try{ ok = window.confirmAction ? await window.confirmAction({ title: 'Remove this product from homepage featured?', icon: 'warning', confirmButtonText: 'Remove', cancelButtonText: 'Cancel' }) : window.confirm('Remove this product from homepage featured?'); }catch(e){ ok = window.confirm('Remove this product from homepage featured?'); }
  if (!ok) return;
  btn.disabled = true;
  try {
    const res = await fetch(`/admin/featured/${encodeURIComponent(id)}/update`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'remove' })
    });
    const j = await res.json().catch(()=>null);
    if (!res.ok || !j || !j.success) {
      alert((j && j.msg) || 'Failed to remove');
      return;
    }
    const row = btn.closest('tr');
    if (row) row.remove();
    alert('Removed from homepage');
  } catch (err) {
    console.error(err);
    alert('Network error');
  } finally {
    btn.disabled = false;
  }
});

// Approve/Reject Riders
document.addEventListener('click', async function(e){
  if (!(e.target.matches('.btn-approve-rider') || e.target.matches('.btn-reject-rider'))) return;
  const btn = e.target;
  const id = btn.dataset.id;
  const action = btn.matches('.btn-approve-rider') ? 'approve' : 'reject';
  if (!id) return;
  const confirmed = await confirmAdminDecision(action === 'approve'
    ? {
        title: 'Approve this rider?',
        text: 'The rider will be granted access to accept delivery assignments.',
        icon: 'question',
        confirmButtonText: 'Yes, approve'
      }
    : {
        title: 'Reject this rider?',
        text: 'The rider application will be removed from the pending list.',
        icon: 'warning',
        confirmButtonText: 'Yes, reject'
      });
  if (!confirmed) return;
  btn.disabled = true;
  try {
    const res = await fetch(`/admin/riders/${encodeURIComponent(id)}/update`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const j = await res.json().catch(()=>null);
    if (!res.ok || !j || !j.success) {
      alert((j && j.msg) || 'Action failed');
      return;
    }
    const row = btn.closest('tr');
    if (row) row.remove();
    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: action === 'approve' ? 'Rider Approved' : 'Rider Rejected',
        text: action === 'approve' ? 'This rider can now take delivery assignments.' : 'The rider application was rejected.',
        timer: 1600,
        showConfirmButton: false
      });
    } else {
      alert(action === 'approve' ? 'Rider approved' : 'Rider rejected');
    }
  } catch (err) {
    console.error(err);
    alert('Network error');
  } finally {
    btn.disabled = false;
  }
});
// extend bottom JS: add ha
document.addEventListener('DOMContentLoaded', function () {
  const input = document.getElementById('newCategoryName');
  const btn = document.getElementById('createCategoryBtn');
  const list = document.getElementById('adminCategoriesList');

  async function createCategory(name) {
    if (!name || !name.trim()) { alert('Enter a category name'); return; }
    btn.disabled = true;
    try {
      const res = await fetch('/admin/categories/create', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name: name.trim() })
      });
      const json = await res.json().catch(()=>null);
      if (!res.ok) {
        alert((json && json.msg) || 'Failed to create category');
        return;
      }
      const cat = json.category;
      const li = document.createElement('li');
      li.setAttribute('data-id', cat.id || '');
      li.setAttribute('data-slug', cat.slug || '');
      li.style.padding = '.5rem';
      li.style.border = '1px solid #f1f1f1';
      li.style.borderRadius = '8px';
      li.style.background = '#fff';
      li.style.display = 'flex';
      li.style.justifyContent = 'space-between';
      li.style.alignItems = 'center';
      li.innerHTML = `<div>${cat.name}</div><div class="muted" style="font-size:.9rem">${cat.id || cat.slug}</div>`;
      list.prepend(li);
      input.value = '';
      alert('Category created — sellers can now select it when adding products.');
    } catch (err) {
      console.error(err);
      alert('Network error');
    } finally {
      btn.disabled = false;
    }
  }

  if (btn) btn.addEventListener('click', () => createCategory(input.value));
  if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') createCategory(input.value); });
});

// Deletion handler for categories
document.addEventListener('click', async function (e) {
  if (e.target && e.target.classList && e.target.classList.contains('btn-delete-category')) {
    const btn = e.target;
    const li = btn.closest('li');
    const id = btn.getAttribute('data-id') || (li && li.getAttribute('data-id')) || '';
    const slug = btn.getAttribute('data-slug') || (li && li.getAttribute('data-slug')) || '';
    const name = btn.getAttribute('data-name') || (li && li.querySelector('span')?.textContent) || '';

  const label = name || slug || id;
  var ok = false;
  try{ ok = window.confirmAction ? await window.confirmAction({ title: `Delete category "${label}"?`, text: 'This action cannot be undone.', icon: 'warning', confirmButtonText: 'Delete', cancelButtonText: 'Cancel' }) : window.confirm(`Delete category "${label}"? This action cannot be undone.`); }catch(e){ ok = window.confirm(`Delete category "${label}"? This action cannot be undone.`); }
  if (!ok) return;

    btn.disabled = true;
    const originalText = btn.textContent;
    btn.textContent = 'Deleting…';
    try {
      const res = await fetch('/admin/categories/delete', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, slug, name })
      });
      const json = await res.json().catch(() => null);
      if (!res.ok || !(json && json.success)) {
        alert((json && json.msg) || 'Failed to delete category');
        return;
      }
      // remove from UI
      if (li && li.parentElement) {
        li.parentElement.removeChild(li);
      }
      alert('Category deleted');
    } catch (err) {
      console.error(err);
      alert('Network error while deleting');
    } finally {
      try { btn.textContent = originalText; } catch (e) {}
      btn.disabled = false;
    }
  }
});

// Permit Modal Logic
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Permit Modal...');
    const modal = document.getElementById('permitModal');
    const modalFrame = document.getElementById('permitFrame');
    const closeBtn = document.querySelector('.permit-modal-close');

    if (!modal) {
        console.error('Permit modal element not found!');
        return;
    }

    function openModal(src) {
      console.log('Opening modal with src:', src);
      if (!modalFrame) {
        window.open(src, '_blank');
        return;
      }

      modalFrame.hidden = false;
      modalFrame.src = src;
      modal.classList.add('active');
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    function closeModal() {
        console.log('Closing modal');
        modal.classList.remove('active');
        setTimeout(() => {
          if (modalFrame) {
            modalFrame.src = '';
            modalFrame.hidden = true;
          }
        }, 300); // Clear src after transition
        document.body.style.overflow = '';
    }

    document.addEventListener('click', function(e) {
        const btnPermit = e.target.closest('.btn-view-permit');
        const btnLicense = e.target.closest('.btn-view-license');
        
        if (btnPermit) {
            e.preventDefault();
            const src = btnPermit.dataset.src;
            if (src) openModal(src);
        } else if (btnLicense) {
            e.preventDefault();
            const src = btnLicense.dataset.src;
            if (src) openModal(src);
        }
        
        if (e.target === modal) {
            closeModal();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeModal();
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });
});

// Store Details Modal Logic
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('storeDetailsModal');
    const content = document.getElementById('storeDetailsContent');
    const closeBtn = modal ? modal.querySelector('.permit-modal-close') : null;

    if (!modal) return;

    function openDetailsModal(data) {
        // Helper to create row
        const row = (label, value) => `
            <div class="detail-row">
                <span class="detail-label">${label}</span>
                <span class="detail-value">${value || 'N/A'}</span>
            </div>
        `;

        content.innerHTML = `
            ${row('Store Name', data.storename)}
            ${row('Owner Name', data.sellername)}
            ${row('Email', data.email)}
            ${row('Contact Number', data.contact)}
            ${row('Category', data.category)}
            ${row('Description', data.desc)}
            ${row('Address', `${data.barangay || ''}, ${data.city || ''}, ${data.province || ''}, ${data.region || ''}`.replace(/^, |, , | ,/g, ''))}
        `;
        
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeDetailsModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }

    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.btn-view-details');
        if (btn) {
            e.preventDefault();
            const data = {
                storename: btn.dataset.storename,
                sellername: btn.dataset.sellername,
                email: btn.dataset.email,
                contact: btn.dataset.contact,
                desc: btn.dataset.desc,
                category: btn.dataset.category,
                region: btn.dataset.region,
                province: btn.dataset.province,
                city: btn.dataset.city,
                barangay: btn.dataset.barangay
            };
            openDetailsModal(data);
        }

        if (e.target === modal) {
            closeDetailsModal();
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeDetailsModal();
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeDetailsModal();
        }
    });
});

// Delete sellers tab
document.addEventListener('click', async function (e) {
  const btn = e.target.closest('.btn-delete-seller');
  if (!btn) return;
  e.preventDefault();
  const sellerId = btn.dataset.id;
  const sellerName = btn.dataset.name || ('Seller #' + sellerId);
  if (!sellerId) {
    alert('Missing seller identifier.');
    return;
  }

  const confirmed = await confirmAdminDecision({
    title: `Delete ${sellerName}?`,
    text: 'All products, chats, orders, notifications, and financial data for this store will be permanently removed.',
    icon: 'warning',
    confirmButtonText: 'Yes, delete',
    cancelButtonText: 'Cancel'
  });
  if (!confirmed) {
    return;
  }

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Deleting…';

  try {
    const res = await fetch(`/admin/delete-seller/${encodeURIComponent(sellerId)}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const json = await res.json().catch(() => null);
    if (!res.ok || !json || !json.success) {
      const msg = (json && (json.msg || json.message)) || 'Failed to delete seller.';
      alert(msg);
      return;
    }

    const row = btn.closest('tr');
    if (row) {
      row.classList.add('removing');
      setTimeout(() => {
        row.remove();
        const tbody = document.querySelector('#deleteSellersTable tbody');
        if (tbody && !tbody.querySelector('tr')) {
          const empty = document.createElement('tr');
          empty.innerHTML = '<td colspan="6" style="padding:24px;text-align:center;color:#94a3b8;">No sellers found.</td>';
          tbody.appendChild(empty);
        }
      }, 220);
    }

    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Seller deleted',
        text: `${sellerName} and all linked records were removed.`,
        confirmButtonText: 'OK'
      });
    } else {
      alert('Seller deleted successfully.');
    }
  } catch (err) {
    console.error('Delete seller failed', err);
    alert('Network error while deleting seller.');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
});

// Delete riders tab
document.addEventListener('click', async function (e) {
  const btn = e.target.closest('.btn-delete-rider');
  if (!btn) return;
  e.preventDefault();
  const riderId = btn.dataset.id;
  const riderName = btn.dataset.name || ('Rider #' + riderId);
  if (!riderId) {
    alert('Missing rider identifier.');
    return;
  }

  const confirmed = await confirmAdminDecision({
    title: `Delete ${riderName}?`,
    text: 'Their delivery chats, responses, and rider profile will be permanently removed.',
    icon: 'warning',
    confirmButtonText: 'Yes, delete',
    cancelButtonText: 'Cancel'
  });
  if (!confirmed) {
    return;
  }

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Deleting…';

  try {
    const res = await fetch(`/admin/delete-rider/${encodeURIComponent(riderId)}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    const json = await res.json().catch(() => null);
    if (!res.ok || !json || !json.success) {
      const msg = (json && (json.msg || json.message)) || 'Failed to delete rider.';
      alert(msg);
      return;
    }

    const row = btn.closest('tr');
    if (row) {
      row.classList.add('removing');
      setTimeout(() => {
        row.remove();
        const tbody = document.querySelector('#deleteRidersTable tbody');
        if (tbody && !tbody.querySelector('tr')) {
          const empty = document.createElement('tr');
          empty.innerHTML = '<td colspan="6" style="padding:24px;text-align:center;color:#94a3b8;">No riders found.</td>';
          tbody.appendChild(empty);
        }
      }, 220);
    }

    if (window.Swal) {
      await Swal.fire({
        icon: 'success',
        title: 'Rider deleted',
        text: `${riderName} was removed successfully.`,
        confirmButtonText: 'OK'
      });
    } else {
      alert('Rider deleted successfully.');
    }
  } catch (err) {
    console.error('Delete rider failed', err);
    alert('Network error while deleting rider.');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
});

// Support Chat Logic has been moved to admin_support_chat.js

/**
 * Load sellers from API and populate the three seller tables
 */
async function loadSellers() {
  try {
    const resp = await fetch('/api/admin/sellers', {
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!resp.ok) {
      console.error('Failed to fetch sellers:', resp.statusText);
      return;
    }
    const sellers = await resp.json();
    const approved = sellers.filter(s => (s.status || '').toLowerCase() === 'approved');
    const pending = sellers.filter(s => (s.status || '').toLowerCase() === 'pending');
    const all = sellers;

    // Render approved sellers table
    const approvedTbody = document.getElementById('approvedSellersTbody');
    if (approvedTbody) {
      if (approved.length === 0) {
        approvedTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">No approved stores yet</td></tr>';
      } else {
        approvedTbody.innerHTML = approved.map(s => `
          <tr data-id="${escapeHtml(s.id)}">
            <td>${escapeHtml(s.id)}</td>
            <td><strong>${escapeHtml(s.storename || '—')}</strong></td>
            <td>${escapeHtml(s.sellername || '—')}<br><small>${escapeHtml(s.selleremail || '—')}</small></td>
            <td>${escapeHtml(s.seller_category || 'N/A')}</td>
            <td class="status-cell">${escapeHtml(s.status || '—')}</td>
            <td>
              <div class="action-stack">
                <button class="btn-view-details"
                  data-id="${escapeHtml(s.id)}"
                  data-storename="${escapeHtml(s.storename || '')}"
                  data-sellername="${escapeHtml(s.sellername || '')}"
                  data-email="${escapeHtml(s.selleremail || '')}"
                  data-contact="${escapeHtml(s.contactnumber || '')}"
                  data-desc="${escapeHtml(s.storedesc || '')}"
                  data-category="${escapeHtml(s.seller_category || 'N/A')}"
                  data-region="${escapeHtml(s.region || '')}"
                  data-province="${escapeHtml(s.province || '')}"
                  data-city="${escapeHtml(s.city || '')}"
                  data-barangay="${escapeHtml(s.barangay || '')}"
                  type="button">View Details</button>
                ${s.businesspermit_path ? `<button class="btn-view-permit" data-src="/admin/uploads/${escapeHtml(s.businesspermit_path)}" type="button">View Permit</button>` : ''}
              </div>
            </td>
          </tr>
        `).join('');
        // Reattach event listeners for approved sellers
      }
    }

    // Render pending sellers table
    const pendingTbody = document.getElementById('pendingSellersTbody');
    if (pendingTbody) {
      if (pending.length === 0) {
        pendingTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px; color: #666;">No pending store approvals</td></tr>';
      } else {
        pendingTbody.innerHTML = pending.map(s => `
          <tr data-id="${escapeHtml(s.id)}">
            <td>${escapeHtml(s.id)}</td>
            <td><strong>${escapeHtml(s.storename || '—')}</strong></td>
            <td>${escapeHtml(s.sellername || '—')}<br><small>${escapeHtml(s.selleremail || '—')}</small></td>
            <td class="status-cell">${escapeHtml(s.status || '—')}</td>
            <td>
              <div class="action-stack">
                <button class="btn-approve" data-id="${escapeHtml(s.id)}" type="button">Approve</button>
                <button class="btn-reject" data-id="${escapeHtml(s.id)}" type="button">Reject</button>
                ${s.businesspermit_path ? `<button class="btn-view-permit" data-src="/admin/uploads/${escapeHtml(s.businesspermit_path)}" type="button">View Permit</button>` : ''}
              </div>
            </td>
          </tr>
        `).join('');
        // Reattach event listeners for pending sellers
      }
    }

    // Render all sellers table for deletion
    const allTbody = document.getElementById('allSellersTbody');
    if (allTbody) {
      if (all.length === 0) {
        allTbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: #666;">No sellers found</td></tr>';
      } else {
        allTbody.innerHTML = all.map(s => {
          const st = (s.status || 'pending').toLowerCase();
          let statusHtml = '<span style="background:#fce7f3;color:#be185d;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:6px;">Pending</span>';
          if (st === 'approved') {
            statusHtml = '<span style="background:#dcfce7;color:#15803d;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:6px;">Approved</span>';
          } else if (st === 'rejected') {
            statusHtml = '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;display:inline-flex;align-items:center;gap:6px;">Rejected</span>';
          }
          return `
            <tr data-id="${escapeHtml(s.id)}" class="delete-seller-row">
              <td><strong>#${escapeHtml(s.id)}</strong></td>
              <td>
                <div>${escapeHtml(s.storename || '—')}</div>
                <small style="color:#94a3b8;">${escapeHtml(s.seller_category || 'Uncategorized')}</small>
              </td>
              <td>
                <div>${escapeHtml(s.sellername || '—')}</div>
                <small style="color:#475569;">${escapeHtml(s.selleremail || '—')}</small>
              </td>
              <td>${statusHtml}</td>
              <td><small style="color:#64748b;">${escapeHtml(s.created_at ? new Date(s.created_at).toLocaleDateString() : '—')}</small></td>
              <td style="text-align:center;">
                <button class="btn-delete-seller" data-id="${escapeHtml(s.id)}" data-name="${escapeHtml(s.storename || '')}" type="button">Delete</button>
              </td>
            </tr>
          `;
        }).join('');
        // Reattach event listeners for all sellers
      }
    }
  } catch (err) {
    console.error('Error loading sellers:', err);
  }
}

// Load sellers on page load as a fallback to ensure fresh data
document.addEventListener('DOMContentLoaded', function() {
  loadSellers();
});
