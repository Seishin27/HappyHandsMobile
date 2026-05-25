// Lightweight SweetAlert2 wrapper with graceful fallback to native confirm()
// Usage: await confirmAction({ title:'Delete item?', text:'This cannot be undone', icon:'warning', confirmButtonText:'Delete' })
(function(){
  window.confirmAction = function(opts){
    opts = opts || {};
    var title = opts.title || opts.message || 'Are you sure?';
    var text = opts.text || '';
    var icon = opts.icon || 'warning';
    var confirmButtonText = opts.confirmButtonText || opts.okText || 'Yes';
    var cancelButtonText = opts.cancelButtonText || 'Cancel';

    // SweetAlert2 (cdn exposes `Swal` with .fire)
    if (window.Swal && typeof window.Swal.fire === 'function') {
      return window.Swal.fire({
        title: title,
        text: text,
        icon: icon,
        showCancelButton: true,
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText,
        reverseButtons: true
      }).then(function(res){ return !!res.isConfirmed; });
    }

    // SweetAlert (older) fallback
    if (window.swal && typeof window.swal === 'function') {
      return new Promise(function(resolve){
        try{
          window.swal({ title: title, text: text, icon: icon, buttons: [cancelButtonText, confirmButtonText], dangerMode: (icon==='warning') }, function(isConfirm){ resolve(!!isConfirm); });
        }catch(e){ resolve(window.confirm(title + (text? '\n\n'+text : ''))); }
      });
    }

    // Last-resort: native confirm()
    return Promise.resolve(window.confirm(title + (text? '\n\n'+text : '')));
  };

  // Auto-bind attribute-based confirmations for elements with `data-confirm`
  document.addEventListener('DOMContentLoaded', function(){
    // Delegate submit events for forms with data-confirm
    document.addEventListener('submit', function(e){
      try{
        var form = e.target;
        if (!form || !form.hasAttribute('data-confirm')) return;
        e.preventDefault();
        var msg = form.getAttribute('data-confirm') || 'Are you sure?';
        window.confirmAction({ title: msg, icon: form.getAttribute('data-confirm-icon') || 'warning', confirmButtonText: form.getAttribute('data-confirm-ok') || 'Yes', cancelButtonText: form.getAttribute('data-confirm-cancel') || 'Cancel' })
        .then(function(ok){ if (ok) form.submit(); });
      }catch(e){}
    }, true);

    // Delegate clicks for elements with data-confirm (buttons, links)
    document.addEventListener('click', function(e){
      try{
        var el = e.target.closest && e.target.closest('[data-confirm]');
        if (!el) return;
        // Don't double-handle forms (submit will be handled above)
        if (el.tagName === 'FORM') return;
        e.preventDefault();
        var msg = el.getAttribute('data-confirm') || 'Are you sure?';
        var icon = el.getAttribute('data-confirm-icon') || 'warning';
        var okText = el.getAttribute('data-confirm-ok') || 'Yes';
        var cancelText = el.getAttribute('data-confirm-cancel') || 'Cancel';
        window.confirmAction({ title: msg, icon: icon, confirmButtonText: okText, cancelButtonText: cancelText })
        .then(function(ok){
          if (!ok) return;
          // If it's a link, navigate
          if (el.tagName === 'A' && el.href) { window.location = el.href; return; }
          // If it's a button inside a form, submit the form
          if (el.tagName === 'BUTTON' && (el.type === 'submit' || el.getAttribute('data-submit')==='true')) {
            var f = el.closest('form'); if (f) { f.submit(); return; }
          }
          // If it has data-action, evaluate it (rare, kept for compatibility)
            if (el.dataset && el.dataset.action) {
              try{
                // Avoid string-evaluation (eval/new Function) to respect CSP.
                // Permit only safe function references like `myApp.doThing` or `globalFunc`.
                (function callActionString(actionStr, ctx){
                  if (!actionStr) return;
                  // only allow simple names and dot-separated paths (alphanumeric, _, $, and dots)
                  if (!/^[A-Za-z0-9_.$]+$/.test(actionStr)) return;
                  const parts = actionStr.split('.');
                  let fn = window;
                  for (let i = 0; i < parts.length; i++){
                    if (fn == null) return;
                    fn = fn[parts[i]];
                  }
                  if (typeof fn === 'function'){
                    try{ fn.call(ctx || window); }catch(e){}
                  }
                })(el.dataset.action, el);
              }catch(e){}
            }
          // If element has an onclick handler, call it
          if (typeof el.onclick === 'function') { try{ el.onclick(); }catch(e){} }
        });
      }catch(e){}
    }, true);
  });
})();
