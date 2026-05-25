(function(){
  // Lightweight modern toast notifications available globally as window.tinyFlash(type)
  const STYLE_ID = 'tinyflash-styles';
  function injectStyles(){
    if (document.getElementById(STYLE_ID)) return;
    const s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = `
      .tf-container{position:fixed;right:18px;bottom:22px;z-index:99999;display:flex;flex-direction:column;gap:10px;}
      .tf-item{min-width:240px;max-width:420px;background:rgba(16,24,40,.96);color:#fff;padding:10px 14px;border-radius:10px;box-shadow:0 10px 28px rgba(2,6,23,.35);font-weight:600;opacity:0;transform:translateY(12px);transition:opacity .22s ease,transform .22s ease;display:flex;align-items:center;gap:10px}
      .tf-item.show{opacity:1;transform:translateY(0)}
      .tf-item.success{background:linear-gradient(135deg,#16a34a,#0e7a36)}
      .tf-item.error{background:linear-gradient(135deg,#dc2626,#b91c1c)}
      .tf-item.info{background:linear-gradient(135deg,#2563eb,#1e40af)}
      .tf-close{margin-left:auto;background:transparent;border:0;color:#fff;font-size:18px;cursor:pointer;opacity:.9}
    `;
    document.head.appendChild(s);
  }
  function ensureContainer(){
    let c = document.querySelector('.tf-container');
    if (!c){
      c = document.createElement('div');
      c.className = 'tf-container';
      document.body.appendChild(c);
    }
    return c;
  }
  function tinyFlash(message, type){
    try{ injectStyles(); }catch(e){}
    const c = ensureContainer();
    const el = document.createElement('div');
    el.className = 'tf-item ' + (type||'info');
    el.innerHTML = `<span>${message||''}</span><button class="tf-close" aria-label="Close">&times;</button>`;
    c.appendChild(el);
    // force reflow before show
    void el.offsetWidth; el.classList.add('show');
    const close = ()=>{ el.classList.remove('show'); setTimeout(()=>{ try{ c.removeChild(el);}catch(_){} }, 220); };
    el.querySelector('.tf-close').onclick = close;
    setTimeout(close, 2600);
  }
  window.tinyFlash = tinyFlash;
  window.tinySuccess = (msg)=>tinyFlash(msg,'success');
  window.tinyError = (msg)=>tinyFlash(msg,'error');

  // Render any server-provided flashes
  document.addEventListener('DOMContentLoaded', function(){
    const flashes = (window.__server_flashes||[]);
    if (Array.isArray(flashes)){
      flashes.forEach(([cat,msg])=> tinyFlash(msg, cat==='error'?'error':(cat==='success'?'success':'info')));
      // clear after showing
      try{ window.__server_flashes = []; }catch(e){}
    }
  });
})();
