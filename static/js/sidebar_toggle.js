// Sidebar toggle: injects a hamburger into navbars and toggles sidebars on small screens
(function(){
  function createToggleButton(){
    const btn = document.createElement('button');
    btn.className = 'sidebar-toggle';
    btn.setAttribute('aria-label','Open sidebar');
    btn.innerHTML = '<span class="bars"><span></span></span>';
    btn.addEventListener('click', toggleSidebar);
    return btn;
  }

  function ensureBackdrop(){
    let d = document.getElementById('sidebarBackdrop');
    if (!d){
      d = document.createElement('div');
      d.id = 'sidebarBackdrop';
      d.className = 'sidebar-backdrop';
      d.addEventListener('click', closeSidebar);
      document.body.appendChild(d);
    }
    return d;
  }

  function toggleSidebar(e){
    const open = document.body.classList.toggle('sidebar-open');
    const backdrop = ensureBackdrop();
    backdrop.classList.toggle('visible', open);
  }
  function closeSidebar(){
    document.body.classList.remove('sidebar-open');
    const d = document.getElementById('sidebarBackdrop');
    if (d) d.classList.remove('visible');
  }

  // close on ESC
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeSidebar(); });

  // Insert hamburger into each navbar once DOM ready
  document.addEventListener('DOMContentLoaded', function(){
    try{
      const navbars = Array.from(document.querySelectorAll('.navbar, .admin-header .header-content, header .navbar'));
      if (!navbars.length) return;
      navbars.forEach(nav => {
        // avoid inserting duplicate toggles
        if (nav.querySelector('.sidebar-toggle')) return;
        const btn = createToggleButton();
        // place at the start of nav-actions if present, else prepend to nav
        const target = nav.querySelector('.nav-actions') || nav.querySelector('.header-content') || nav;
        target.insertBefore(btn, target.firstChild);
      });
      ensureBackdrop();
    }catch(e){ /* non-fatal */ console.warn('sidebar_toggle init error', e); }
  });
})();
