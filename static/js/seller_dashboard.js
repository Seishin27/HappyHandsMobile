const SellerDescriptionFormatting = (() => {
  const allowedTags = new Set(['BR', 'P', 'UL', 'OL', 'LI', 'STRONG', 'B', 'EM', 'I', 'DIV', 'SPAN']);
  const tagPattern = /<(?:br|p|ul|ol|li|div|span|strong|em|b|i)/i;

  function sanitizeHtml(input) {
    if (!input) return '';
    const template = document.createElement('template');
    template.innerHTML = String(input);
    (function clean(node) {
      Array.from(node.childNodes).forEach(child => {
        if (child.nodeType === 1) {
          clean(child);
          if (!allowedTags.has(child.tagName)) {
            while (child.firstChild) {
              child.parentNode.insertBefore(child.firstChild, child);
            }
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

  function normalizeLegacyBreaks(html) {
    if (!html) return '';
    if (tagPattern.test(html)) return html;
    const normalized = html.replace(/\r\n|\r/g, '\n');
    return normalized
      .split(/\n\n+/)
      .map(block => block.replace(/\n/g, '<br>'))
      .join('<br><br>');
  }

  function formatValue(value) {
    if (!value) return '';
    return normalizeLegacyBreaks(sanitizeHtml(value));
  }

  function insertDoubleBreak(editor) {
    if (!editor) return;
    if (document.queryCommandSupported && document.queryCommandSupported('insertHTML')) {
      try {
        document.execCommand('insertHTML', false, '<br><br>');
        return;
      } catch (e) { /* ignore */ }
    }
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      editor.appendChild(document.createElement('br'));
      editor.appendChild(document.createElement('br'));
      return;
    }
    const range = selection.getRangeAt(0);
    range.deleteContents();
    const br1 = document.createElement('br');
    const br2 = document.createElement('br');
    range.insertNode(br2);
    range.insertNode(br1);
    range.setStartAfter(br2);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function initEditor(opts) {
    const input = document.getElementById(opts.inputId);
    const editor = document.getElementById(opts.editorId);
    const wrapper = opts.wrapperId ? document.getElementById(opts.wrapperId) : null;
    if (!input || !editor) return null;
    if (wrapper) {
      wrapper.hidden = false;
    }
    input.classList.add('rich-text-hidden-input');
    const toolbar = opts.toolbarId ? document.getElementById(opts.toolbarId) : (wrapper ? wrapper.querySelector('.rich-text-toolbar') : null);

    function ensureEmptyState() {
      const text = (editor.textContent || '').replace(/\u00a0/g, ' ').trim();
      if (!text && !editor.querySelector('li')) {
        editor.innerHTML = '';
      }
    }

    function syncInput() {
      input.value = formatValue(editor.innerHTML);
    }

    function focusEditor() {
      editor.focus();
      const selection = window.getSelection();
      if (!selection) return;
      if (selection.rangeCount === 0) {
        const range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }

    function handleToolbar(ev) {
      const btn = ev.target.closest('.rich-text-btn');
      if (!btn) return;
      ev.preventDefault();
      focusEditor();
      const action = btn.dataset.action;
      if (action === 'bullet') {
        try { document.execCommand('insertUnorderedList'); }
        catch (e) { /* ignore */ }
        syncInput();
        return;
      }
      if (action === 'break') {
        insertDoubleBreak(editor);
        syncInput();
      }
    }

    toolbar?.addEventListener('click', handleToolbar);

    editor.addEventListener('input', () => {
      ensureEmptyState();
      syncInput();
    });
    editor.addEventListener('blur', () => {
      ensureEmptyState();
      syncInput();
    });

    const api = {
      setContent(value) {
        const formatted = formatValue(value);
        editor.innerHTML = formatted || '';
        syncInput();
      },
      getValue() {
        return formatValue(editor.innerHTML);
      },
      sync() {
        syncInput();
      },
      clear() {
        editor.innerHTML = '';
        syncInput();
      }
    };

    if (input.value) {
      api.setContent(input.value);
    } else {
      api.clear();
    }

    return api;
  }

  return { initEditor, formatValue };
})();

window.SellerDescriptionFormatting = SellerDescriptionFormatting;
window.sellerDescriptionEditors = window.sellerDescriptionEditors || {};

// Account dropdown & logout for seller (mirrors rider behavior)
document.addEventListener('DOMContentLoaded', function(){
  const editorRegistry = window.sellerDescriptionEditors || (window.sellerDescriptionEditors = {});
  const addEditor = SellerDescriptionFormatting.initEditor({
    inputId: 'addProductDescription',
    editorId: 'addProductDescriptionEditor',
    wrapperId: 'addProductDescriptionRich',
    toolbarId: 'addProductDescriptionToolbar'
  });
  if (addEditor) editorRegistry.add = addEditor;
  const editEditor = SellerDescriptionFormatting.initEditor({
    inputId: 'editProductDescription',
    editorId: 'editProductDescriptionEditor',
    wrapperId: 'editProductDescriptionRich',
    toolbarId: 'editProductDescriptionToolbar'
  });
  if (editEditor) editorRegistry.edit = editEditor;

  (function(){
    const acctBtn = document.getElementById('ActBtnSeller') || document.getElementById('ActBtn') || document.getElementById('profileBtn');
    const acctMenu = document.getElementById('sellerDropdown') || document.getElementById('userDropdown') || document.getElementById('profileMenu');
    if (acctBtn && acctMenu) {
      function closeAcct(){ acctMenu.style.display=''; acctMenu.classList.remove('visible'); acctMenu.setAttribute && acctMenu.setAttribute('aria-hidden','true'); acctBtn.setAttribute && acctBtn.setAttribute('aria-expanded','false'); }
      function openAcct(){ acctMenu.style.display='block'; acctMenu.classList.add('visible'); acctMenu.setAttribute && acctMenu.setAttribute('aria-hidden','false'); acctBtn.setAttribute && acctBtn.setAttribute('aria-expanded','true'); }
      acctBtn.addEventListener('click', function(ev){ ev.stopPropagation(); if (acctMenu.classList.contains('visible')) closeAcct(); else openAcct(); });
      document.addEventListener('click', function(ev){ if (!acctMenu.contains(ev.target) && !acctBtn.contains(ev.target)) closeAcct(); });
      document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') closeAcct(); });
      const logoutIds = ['sellerLogoutBtn','logoutBtn','adminLogoutBtn'];
      for (const id of logoutIds){
        const b = document.getElementById(id);
        if (!b) continue;
        b.addEventListener('click', async function(){
          let endpoint = '/logout';
          if (id === 'sellerLogoutBtn') endpoint = '/seller-logout';
          else if (id === 'adminLogoutBtn') endpoint = '/admin-logout';
          try { await fetch(endpoint,{ method:'POST', credentials:'include', headers:{'Content-Type':'application/json'} }); } catch(e){}
          window.location = (id === 'adminLogoutBtn') ? '/login' : '/';
        });
      }
    }
    })();

    (function(){
      const modal = document.getElementById('editProductModal');
      const form = document.getElementById('editProductForm');
      const idEl = document.getElementById('editProductID');
      const nameEl = document.getElementById('editProductName');
      const descriptionEl = document.getElementById('editProductDescription');
      const currentImagesRoot = document.getElementById('editCurrentImages');
      const currentImageSlots = currentImagesRoot ? Array.from(currentImagesRoot.querySelectorAll('.current-image-slot')) : [];
      const newImageBoxes = Array.from(document.querySelectorAll('#editNewImageGrid .image-box'));
      const priceEl = document.getElementById('editProductPrice');
      const stockEl = document.getElementById('editProductStock');
      const msgEl = document.getElementById('editProductMsg');
      const saveBtn = document.getElementById('editProdSave');
      const cancelBtn = document.getElementById('editProdCancel');
      const closeBtn = document.getElementById('editProdClose');
      const getEditDescriptionEditor = () => (window.sellerDescriptionEditors && window.sellerDescriptionEditors.edit) || null;

      function normalizeImageSrc(val){
        if (!val) return '';
        const raw = String(val).trim();
        if (!raw) return '';
        const lowered = raw.toLowerCase();
        if (lowered === 'none' || lowered === 'null') return '';
        if (/^(?:https?:|data:|blob:)/i.test(raw)) return raw;
        if (raw.startsWith('/uploads/')) return raw;
        if (raw.startsWith('uploads/')) return '/' + raw;
        if (raw.startsWith('/')) return raw;
        return '/uploads/' + raw.replace(/^\/+/, '');
      }

      function renderCurrentImages(list){
        if (!currentImageSlots.length) return;
        const images = Array.isArray(list) ? list : [];
        currentImageSlots.forEach((slot, index) => {
          const imgEl = slot.querySelector('.current-image');
          const emptyState = slot.querySelector('.empty-state');
          const src = images[index] ? normalizeImageSrc(images[index]) : '';
          if (imgEl){
            if (src){
              imgEl.src = src;
              imgEl.style.display = 'block';
              slot.classList.add('has-image');
            } else {
              imgEl.removeAttribute('src');
              imgEl.style.display = 'none';
              slot.classList.remove('has-image');
            }
          }
          if (emptyState){
            emptyState.style.display = src ? 'none' : 'block';
          }
        });
      }

      function resetNewImageUploads(){
        newImageBoxes.forEach(box => {
          const input = box.querySelector('.edit-image-input');
          const preview = box.querySelector('img.preview');
          if (input){
            try { input.value = ''; } catch(e){}
          }
          if (preview){
            preview.removeAttribute('src');
          }
          box.classList.remove('has-image');
        });
      }

      function setupNewImageUploads(){
        newImageBoxes.forEach(box => {
          const input = box.querySelector('.edit-image-input');
          const preview = box.querySelector('img.preview');
          const removeBtn = box.querySelector('.remove-image');
          if (!input) return;
          box.addEventListener('click', ev => {
            if (ev.target === removeBtn) return;
            input.click();
          });
          input.addEventListener('change', () => {
            const file = input.files && input.files[0];
            if (file){
              try {
                if (preview) {
                  preview.src = URL.createObjectURL(file);
                }
                box.classList.add('has-image');
              } catch(err){
                if (preview) preview.removeAttribute('src');
                box.classList.remove('has-image');
              }
            } else {
              if (preview) preview.removeAttribute('src');
              box.classList.remove('has-image');
            }
          });
          removeBtn?.addEventListener('click', ev => {
            ev.stopPropagation();
            try { input.value = ''; } catch(e){}
            if (preview) preview.removeAttribute('src');
            box.classList.remove('has-image');
          });
        });
      }
      setupNewImageUploads();

      function open(){ if (modal) modal.style.display='block'; }
      function close(){ 
        if (modal) modal.style.display='none'; 
        try { form.reset(); } catch(e){} 
        if (msgEl){ msgEl.textContent=''; msgEl.style.display=''; } 
        if (descriptionEl) descriptionEl.value = '';
        const editorInstance = getEditDescriptionEditor();
        if (editorInstance && typeof editorInstance.clear === 'function') {
          editorInstance.clear();
        }
        renderCurrentImages([]);
        resetNewImageUploads();
      }
      function prefillFromRow(id){
        const row = document.querySelector(`section#manage-product tr[data-id='${id}']`);
        if (!row) return;
        const nm = row.getAttribute('data-name') || (row.querySelector('.prod-name')?.textContent || '');
        const pr = row.getAttribute('data-price');
        const st = row.getAttribute('data-stock');
        const desc = row.getAttribute('data-description') || '';
        const imagesAttr = row.getAttribute('data-images') || '[]';
        let parsedImages = [];
        try {
          const maybeArr = JSON.parse(imagesAttr);
          if (Array.isArray(maybeArr)) parsedImages = maybeArr;
        } catch(err){ parsedImages = []; }
        idEl.value = id;
        nameEl.value = nm || '';
        priceEl.value = pr || '';
        stockEl.value = st || '';
        const formattedDesc = (window.SellerDescriptionFormatting && typeof SellerDescriptionFormatting.formatValue === 'function') ? SellerDescriptionFormatting.formatValue(desc) : (desc || '');
        if (descriptionEl) descriptionEl.value = formattedDesc;
        const editorInstance = getEditDescriptionEditor();
        if (editorInstance && typeof editorInstance.setContent === 'function') {
          editorInstance.setContent(formattedDesc);
        }
        renderCurrentImages(parsedImages);
        resetNewImageUploads();
      }
      document.addEventListener('click', function(e){
        if (e.target.matches('.btn-edit')){
          const id = e.target.getAttribute('data-id');
          if (!id) return;
          prefillFromRow(id);
          open();
        }
      });
      cancelBtn?.addEventListener('click', function(){ close(); });
      closeBtn?.addEventListener('click', function(){ close(); });
      window.addEventListener('click', function(ev){ if (ev.target === modal) close(); });
      form?.addEventListener('submit', async function(ev){
        ev.preventDefault();
        const id = idEl.value.trim();
        const name = nameEl.value.trim();
        const price = priceEl.value.trim();
        const stock = stockEl.value.trim();
        const editorInstance = getEditDescriptionEditor();
        if (editorInstance && typeof editorInstance.sync === 'function') {
          editorInstance.sync();
        }
        let description = descriptionEl ? descriptionEl.value : '';
        if (window.SellerDescriptionFormatting && typeof SellerDescriptionFormatting.formatValue === 'function') {
          description = SellerDescriptionFormatting.formatValue(description);
        } else {
          description = (description || '').trim();
        }
        if (descriptionEl) descriptionEl.value = description;
        let errors = [];
        if (!name) errors.push('Name is required');
        if (name.length > 120) errors.push('Name too long');
        const priceNum = Number(price);
        if (!(price !== '' && !Number.isNaN(priceNum) && priceNum >= 0)) errors.push('Invalid price');
        const stockNum = Number(stock);
        if (!(stock !== '' && Number.isInteger(stockNum) && stockNum >= 0)) errors.push('Invalid stock');
        if (errors.length){ if (msgEl){ msgEl.textContent = errors[0]; msgEl.style.display='block'; msgEl.style.color='#ef4444'; } return; }
        const fd = new FormData();
        fd.append('productID', id);
        fd.append('name', name);
        fd.append('price', String(priceNum));
        fd.append('stock', String(stockNum));
        fd.append('description', description);
        newImageBoxes.forEach((box, index) => {
          const input = box.querySelector('.edit-image-input');
          if (input && input.files && input.files[0]) {
            fd.append(`image${index}`, input.files[0]);
          }
        });
        saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
        try{
          const res = await fetch('/seller/manage/product', { method:'POST', credentials:'include', body: fd });
          const j = await res.json().catch(()=>null);
          if (res.ok && j && j.success){
            const row = document.querySelector(`section#manage-product tr[data-id='${id}']`);
            if (row){
              row.setAttribute('data-name', name);
              row.setAttribute('data-price', String(priceNum));
              row.setAttribute('data-stock', String(stockNum));
              row.setAttribute('data-description', description);
              if (j.image) {
                  let newImages = [];
                  try {
                    newImages = Array.isArray(j.image) ? j.image : String(j.image).split(',').map(s => s.trim()).filter(Boolean);
                  } catch(err) {
                    newImages = [];
                  }
                  if (newImages.length) {
                    row.setAttribute('data-images', JSON.stringify(newImages));
                  }
              }
              const nameCell = row.querySelector('.prod-name'); if (nameCell) nameCell.textContent = name;
              const priceCell = row.querySelector('.prod-price'); if (priceCell) priceCell.textContent = '₱'+priceNum.toFixed(2);
              const stockCell = row.querySelector('.prod-stock'); if (stockCell) stockCell.textContent = String(stockNum);
            }
            if (msgEl){ msgEl.textContent = j.msg || 'Product updated'; msgEl.style.display='block'; msgEl.style.color='#059669'; }
            setTimeout(close, 800);
          } else {
            const err = (j && j.msg) ? j.msg : `Failed (${res.status})`;
            if (msgEl){ msgEl.textContent = err; msgEl.style.display='block'; msgEl.style.color='#ef4444'; }
          }
        }catch(e){ if (msgEl){ msgEl.textContent = 'Network error'; msgEl.style.display='block'; msgEl.style.color='#ef4444'; } }
        finally{ saveBtn.disabled=false; saveBtn.textContent='Save Changes'; }
      });
    })();
});

 (function(){
              const form = document.getElementById('addProductForm');
              const msg = document.getElementById('addProductMsg');
              const boxes = document.querySelectorAll('#add-product .image-box');
              const getAddDescriptionEditor = () => (window.sellerDescriptionEditors && window.sellerDescriptionEditors.add) || null;

              // Image preview + aligned box triggers
              boxes.forEach(box => {
                const input = box.querySelector('input[type=file]');
                if (!input) return;

                // create preview img if missing
                let img = box.querySelector('img.preview');
                if (!img) {
                  img = document.createElement('img');
                  img.className = 'preview';
                  box.appendChild(img);
                }
                // create remove button if missing
                let rm = box.querySelector('.remove-image');
                if (!rm) {
                  rm = document.createElement('button');
                  rm.type = 'button';
                  rm.className = 'remove-image';
                  rm.textContent = 'Remove';
                  box.appendChild(rm);
                }

                // Click anywhere on box to open file chooser (except remove)
                box.addEventListener('click', (ev) => {
                  if (ev.target === rm) return; // handled separately
                  input.click();
                });

                // Handle file selection -> show preview
                input.addEventListener('change', () => {
                  const f = input.files && input.files[0];
                  if (f) {
                    try { img.src = URL.createObjectURL(f); } catch (e) { img.removeAttribute('src'); }
                    box.classList.add('has-image');
                  } else {
                    img.removeAttribute('src');
                    box.classList.remove('has-image');
                  }
                });

                // Remove selected image
                rm.addEventListener('click', (ev) => {
                  ev.stopPropagation();
                  input.value = '';
                  img.removeAttribute('src');
                  box.classList.remove('has-image');
                });
              });

              if (form) {
                form.addEventListener('reset', function(){
                  const editorInstance = getAddDescriptionEditor();
                  if (editorInstance && typeof editorInstance.clear === 'function') {
                    editorInstance.clear();
                  }
                });
                form.addEventListener('submit', async function(ev){
                  ev.preventDefault();
                  if (msg) msg.style.display = 'none';
  
                  // basic validation
                  const name = (form.name.value || '').trim();
                  const price = form.price.value;
                  const stock = form.stock.value;
                  const addDescEditor = getAddDescriptionEditor();
                  if (addDescEditor && typeof addDescEditor.sync === 'function') {
                    addDescEditor.sync();
                  }
                  if (form.description && window.SellerDescriptionFormatting && typeof SellerDescriptionFormatting.formatValue === 'function') {
                    form.description.value = SellerDescriptionFormatting.formatValue(form.description.value);
                  }
                  if (!name || price === '' || stock === '') {
                    if (msg) {
                      msg.style.display = 'block';
                      msg.style.color = '#b45309';
                      msg.textContent = 'Please fill required fields: Name, Price and Stock.';
                    }
                    return;
                  }
  
                  const fd = new FormData(form);
                  try {
                    const res = await fetch('/seller/manage/product', {
                      method: 'POST',
                      body: fd,
                      credentials: 'include'
                    });
                    const j = await res.json().catch(()=>null);
                    if (res.ok && j && j.success) {
                      if (msg) {
                        msg.style.display = 'block';
                        msg.style.color = '#059669';
                        msg.textContent = j.msg || 'Product created';
                      }
                      form.reset();
                      const editorInstance = getAddDescriptionEditor();
                      if (editorInstance && typeof editorInstance.clear === 'function') {
                        editorInstance.clear();
                      }
                      boxes.forEach(b => {
                        b.classList.remove('has-image');
                        const img = b.querySelector('img.preview');
                        if (img) img.removeAttribute('src');
                      });
  
                      // Append the created product to the manage table if present
                      if (j.productID) {
                        const tbody = document.querySelector('#manage-product table tbody');
                        if (tbody) {
                          const tr = document.createElement('tr');
                          tr.setAttribute('data-id', j.productID);
                          tr.innerHTML = `
                            <td style="padding:8px;">${j.productID}</td>
                            <td style="padding:8px;">${name}</td>
                            <td style="padding:8px;">${parseFloat(price).toFixed(2)}</td>
                            <td style="padding:8px;">${stock}</td>
                            <td style="padding:8px;">
                              <button class="btn btn-edit" data-id="${j.productID}" style="margin-right:6px;">Edit</button>
                              <button class="btn btn-delete" data-id="${j.productID}" style="background:#ef4444;color:#fff;">Delete</button>
                            </td>
                          `;
                          tbody.prepend(tr);
                        }
                      }
                      return;
                    }
  
                    // error handling
                    const errMsg = j && j.msg ? j.msg : `Request failed (${res.status})`;
                    if (msg) {
                      msg.style.display = 'block';
                      msg.style.color = '#ef4444';
                      msg.textContent = errMsg;
                    } else {
                      alert(errMsg);
                    }
                  } catch (e) {
                    console.error(e);
                    if (msg) {
                      msg.style.display = 'block';
                      msg.style.color = '#ef4444';
                      msg.textContent = 'Network error while creating product.';
                    } else {
                      alert('Network error while creating product.');
                    }
                  }
                });
              }

              // single delegated delete handler
              document.addEventListener('click', async function(e){
                if (!e.target.matches('.btn-delete')) return;
                const btn = e.target;
                const id = btn.dataset.id;
                if (!id) return;
                // Use SweetAlert2 confirmAction if available, fallback to native confirm
                var shouldDelete = false;
                try{
                  if (window.confirmAction) {
                    shouldDelete = await window.confirmAction({ title: 'Delete this product?', text: '', icon: 'warning', confirmButtonText: 'Delete', cancelButtonText: 'Cancel' });
                  } else {
                    shouldDelete = window.confirm('Delete this product?');
                  }
                }catch(e){ shouldDelete = window.confirm('Delete this product?'); }
                if (!shouldDelete) return;
                btn.disabled = true;
                try {
                  const res = await fetch(`/seller/remove/product/${encodeURIComponent(id)}`, {
                    method: 'DELETE',
                    credentials: 'include'
                  });
                  const j = await res.json().catch(()=>null);
                  if (res.ok && j && j.success) {
                    const row = document.querySelector(`tr[data-id=\"${id}\"]`);
                    if (row) row.remove();
                    // show quick feedback in the add product message area if present
                    if (msg) {
                      msg.style.display = 'block';
                      msg.style.color = '#059669';
                      msg.textContent = j.msg || 'Product removed';
                    } else {
                      alert(j.msg || 'Product removed');
                    }
                    return;
                  }
                  alert((j && j.msg) ? j.msg : `Delete failed (${res.status})`);
                } catch (err) {
                  console.error(err);
                  alert('Network error');
                } finally {
                  btn.disabled = false;
                }
              });

            })();

            // ----- Seller Orders handlers (View / Update / Assign Rider) -----
            (function(){
              const ordersRoot = document.getElementById('orders');
              if (!ordersRoot) return; // only run on dashboard with orders section

              // Pending overlay controls
              const overlay = document.getElementById('pendingOverlay');
              const main = document.querySelector('.admin-main');
              function setBlur(active){
                try { if (main) main.classList.toggle('content-blur', !!active); } catch(e){}
              }
              if (overlay && overlay.classList.contains('visible')) setBlur(true);
              const refreshBtn = document.getElementById('refreshStatusBtn');
              if (refreshBtn) {
                refreshBtn.addEventListener('click', async () => {
                  refreshBtn.disabled = true;
                  try {
                    const res = await fetch('/api/seller/status', { credentials: 'include' });
                    const j = await res.json().catch(()=>null);
                    const status = j && (j.status || j.State || j.state);
                    if (res.ok && status === 'approved') {
                      if (overlay) overlay.classList.remove('visible');
                      setBlur(false);
                      if (window.tinyFlash) tinyFlash('Your seller account is approved!','success');
                    } else {
                      if (window.tinyFlash) tinyFlash('Your account is still pending approval.','info'); else alert('Your account is still pending approval.');
                    }
                  } catch (e) {
                    console.error(e);
                    alert('Failed to check status.');
                  } finally {
                    refreshBtn.disabled = false;
                  }
                });
              }

              // Parse orders JSON from hidden div
              const DASH_ORDERS = (function(){
                const el = document.getElementById('dashOrdersData');
                if (!el) return [];
                try { return JSON.parse(el.getAttribute('data-orders') || '[]'); }
                catch(e){ console.error('dash orders parse', e); return []; }
              })();
              function findOrder(id){
                return (DASH_ORDERS||[]).find(o => String(o.sellerOrderID) === String(id)) || null;
              }

              // Modals
              const statusModal = document.getElementById('dashStatusModal');
              const riderModal = document.getElementById('dashRiderModal');
              const detailsModal = document.getElementById('dashOrderDetailsModal');
              let currentOrderId = null;
              let currentRow = null;
              let selectedRiderId = null;

              function dashOpenStatus(orderId, currentStatus, row){
                currentOrderId = orderId; currentRow = row || null;
                const sel = document.getElementById('dashNewStatus');
                if (sel) sel.value = currentStatus || 'pending';
                if (statusModal) statusModal.style.display = 'block';
              }
              function dashCloseStatusModal(){
                if (statusModal) statusModal.style.display = 'none';
                try { document.getElementById('dashStatusForm')?.reset(); } catch(e){}
                currentOrderId = null; currentRow = null;
              }
              window.dashCloseStatusModal = dashCloseStatusModal;

              function dashOpenRider(orderId){
                currentOrderId = orderId; selectedRiderId = null;
                const load = document.getElementById('dashRiderLoadState');
                const list = document.getElementById('dashRiderList');
                const empty = document.getElementById('dashRiderEmpty');
                const btn = document.getElementById('dashRiderAssignBtn');
                if (btn) btn.disabled = true;
                if (list) list.style.display = 'none';
                if (empty) empty.style.display = 'none';
                if (load) load.style.display = 'block';
                if (riderModal) riderModal.style.display = 'block';

                fetch('/api/seller/riders', { credentials:'include' })
                  .then(r=>r.json())
                  .then(data=>{
                    if (load) load.style.display = 'none';
                    if (!data || !data.success) { if (empty){ empty.textContent = (data&&data.msg)||'Failed to load riders'; empty.style.display='block'; } return; }
                    const riders = data.riders||[];
                    if (!riders.length){ if (empty){ empty.style.display='block'; } return; }
                    if (list){
                      list.innerHTML = riders.map(r => `
                        <label class="rider-row">
                          <input type="radio" name="dashRiderPick" value="${r.riderID}" data-name="${r.ridername}">
                          <span class="rider-name">${r.ridername}</span>
                          <span class="rider-meta">${r.phone ? r.phone : ''} ${r.rideremail ? '• '+r.rideremail : ''}</span>
                        </label>`).join('');
                      list.style.display = 'block';
                      list.querySelectorAll('input[name="dashRiderPick"]').forEach(inp=>{
                        inp.addEventListener('change', ()=>{ selectedRiderId = inp.value; if (btn) btn.disabled = !selectedRiderId; });
                      });
                    }
                  })
                  .catch(err=>{ console.error(err); if (load) load.style.display='none'; if (empty){ empty.textContent='Network error while loading riders'; empty.style.display='block'; } });
              }
              function dashCloseRiderModal(){ if (riderModal) riderModal.style.display='none'; currentOrderId=null; selectedRiderId=null; }
              window.dashCloseRiderModal = dashCloseRiderModal;

              function dashShowOrderDetails(orderId){
                const o = findOrder(orderId);
                if (!o){ alert('Order not found'); return; }
                const c = document.getElementById('dashOrderDetailsContent');
                const itemsHtml = (o.items||[]).map(it=>`
                  <div class="order-item">
                    <div class="item-image"><img src="${it.image_path ? '/uploads/'+it.image_path.split(',')[0] : '/static/images/default.png'}" alt="${(it.name||'Item')}"></div>
                    <div class="item-details"><h4>${it.name||'Product'}</h4><p>Quantity: ${it.quantity||0}</p><p class="item-price">₱${(parseFloat(it.price||0).toFixed(2))}</p></div>
                  </div>`).join('');

                // Parse address from stored shipping_address "home, barangay, city, province, region"
                const parts = (o.shipping_address||'').split(',').map(s=>s.trim());
                const home = parts[0] || '';
                const barangay = parts[1] || '';
                const city = parts[2] || '';
                const province = parts[3] || '';
                const region = parts[4] || '';
                const payment = (o.payment_method || 'cash_on_delivery').replace(/_/g,' ');

                if (c) c.innerHTML = `
                  <div class="order-header modal-order-header">
                    <h3>Order #${o.order_number}</h3>
                    <div class="order-meta">Customer: ${o.customer_name || '—'} • Placed: ${(String(o.created_at||'').slice(0,19) || '—')} • Total: ₱${(parseFloat(o.total_amount||0).toFixed(2))}</div>
                  </div>
                  <div class="order-items">${itemsHtml || '<p>No items</p>'}</div>
                  <div class="order-details">
                    <div class="detail-section"><h4><i class="fas fa-map-marker-alt"></i> Shipping Address</h4>
                      <p><strong>Region:</strong> ${region || '—'}</p>
                      <p><strong>Province:</strong> ${province || '—'}</p>
                      <p><strong>City:</strong> ${city || '—'}</p>
                      <p><strong>Barangay:</strong> ${barangay || '—'}</p>
                      <p><strong>Home Address:</strong> ${home || '—'}</p>
                    </div>
                    <div class="detail-section"><h4><i class="fas fa-phone"></i> Contact</h4><p>${o.contact_number || '—'}</p></div>
                    <div class="detail-section"><h4><i class="fas fa-credit-card"></i> Payment Method</h4><p>${payment ? (payment[0].toUpperCase()+payment.slice(1)) : 'Cash on Delivery'}</p></div>
                  </div>`;
                if (detailsModal) detailsModal.style.display='block';
              }
              function dashCloseOrderDetails(){ if (detailsModal) detailsModal.style.display='none'; try { document.getElementById('dashOrderDetailsContent').innerHTML=''; } catch(e){} }
              window.dashCloseOrderDetails = dashCloseOrderDetails;

              // Wire table buttons (delegated)
              ordersRoot.addEventListener('click', function(e){
                const t = e.target;
                if (t.matches('.btn-update-status')){
                  const id = t.getAttribute('data-order-id');
                  const st = t.getAttribute('data-order-status') || 'pending';
                  const row = t.closest('tr');
                  if (id) dashOpenStatus(id, st, row);
                } else if (t.matches('.btn-assign-rider')){
                  const id = t.getAttribute('data-order-id');
                  if (id) dashOpenRider(id);
                } else if (t.matches('.btn-view-order')){
                  const id = t.getAttribute('data-order-id');
                  if (id) dashShowOrderDetails(id);
                }
              });

              function notify(msg, type){
                if (window.tinyFlash) window.tinyFlash(msg, type||'info'); else alert(msg);
              }
              // Submit status form
              const statusForm = document.getElementById('dashStatusForm');
              if (statusForm){
                statusForm.addEventListener('submit', async function(ev){
                  ev.preventDefault();
                  if (!currentOrderId){ notify('No order selected','error'); return; }
                  const newStatus = document.getElementById('dashNewStatus')?.value || 'pending';
                  const notes = document.getElementById('dashStatusNotes')?.value || '';
                  try{
                    const res = await fetch(`/api/seller/orders/${currentOrderId}/status`, {
                      method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({status:newStatus, notes})
                    });
                    const j = await res.json().catch(()=>null);
                    if (!res.ok || !j || !j.success){ notify((j&&j.msg)||`Update failed (${res.status})`,'error'); return; }
                    // Update row badge + data attribute
                    if (currentRow){
                      const badge = currentRow.querySelector('.status-badge');
                      if (badge){
                        badge.className = `status-badge status-${newStatus}`;
                        const pretty = newStatus.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
                        badge.textContent = pretty;
                      }
                      const btn = currentRow.querySelector('.btn-update-status');
                      if (btn) btn.setAttribute('data-order-status', newStatus);
                    }
                    dashCloseStatusModal();
                    notify('Order status updated','success');
                  } catch(err){ console.error(err); notify('Network error while updating status','error'); }
                });
              }

              // Assign rider confirm
              const riderBtn = document.getElementById('dashRiderAssignBtn');
              if (riderBtn){
                riderBtn.addEventListener('click', async function(){
                  if (!currentOrderId || !selectedRiderId) return;
                  riderBtn.disabled = true;
                  try{
                    const res = await fetch(`/api/seller/orders/${currentOrderId}/assign-rider`, { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ riderID: selectedRiderId }) });
                    const j = await res.json().catch(()=>null);
                    if (!res.ok || !j || !j.success){ notify((j&&j.msg)||`Assign failed (${res.status})`,'error'); riderBtn.disabled=false; return; }
                    // update table Rider cell
                    const row = ordersRoot.querySelector(`tr[data-order-id=\"${currentOrderId}\"]`);
                    if (row){
                      const cell = row.querySelector('td[data-label=\"Rider\"]');
                      if (cell) cell.textContent = (j.rider && j.rider.ridername) ? j.rider.ridername : 'Assigned';
                    }
                    dashCloseRiderModal();
                    notify('Rider requested','success');
                  } catch(err){ console.error(err); notify('Network error while assigning rider','error'); riderBtn.disabled=false; }
                });
              }

              // Click outside to close modals
              window.addEventListener('click', function(ev){
                if (ev.target === statusModal) dashCloseStatusModal();
                if (ev.target === riderModal) dashCloseRiderModal();
                if (ev.target === detailsModal) dashCloseOrderDetails();
              });
            })();

            // ----- Seller Order Reports handlers -----
            (function(){
              const reportsSection = document.getElementById('order-reports');
              const dataEl = document.getElementById('dashOrderReportsData');
              if (!reportsSection || !dataEl) return;

              let ORDER_REPORTS = [];
              try {
                ORDER_REPORTS = JSON.parse(dataEl.getAttribute('data-order-reports') || '[]') || [];
              } catch (err) {
                console.error('Failed to parse order reports payload', err);
                ORDER_REPORTS = [];
              }

              const detailModal = document.getElementById('reportDetailModal');
              const detailContent = document.getElementById('reportDetailContent');
              const escalateModal = document.getElementById('reportEscalateModal');
              const escalateForm = document.getElementById('reportEscalateForm');
              const escalateIdInput = document.getElementById('escalateReportId');
              const escalateError = document.getElementById('escalateError');
              const escalateSubmitBtn = document.getElementById('escalateSubmitBtn');
              const escalationNoteField = document.getElementById('escalationNote');

              const ISSUE_LABELS = {
                not_received: 'Product not received',
                product_problem: 'Product problems or discrepancies'
              };

              let activeEscalateButton = null;

              function showToast(message, type){
                if (!message) return;
                if (window.tinyFlash) {
                  window.tinyFlash(message, type || 'info');
                } else {
                  alert(message);
                }
              }

              function humanize(value){
                if (!value) return '';
                return value.toString().replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
              }

              function formatDate(value){
                if (!value) return '—';
                try {
                  const d = new Date(value);
                  if (!Number.isNaN(d.getTime())) {
                    return d.toLocaleString();
                  }
                } catch (err) {
                  /* ignore */
                }
                return String(value);
              }

              function findReport(id){
                return (ORDER_REPORTS || []).find(r => String(r.id) === String(id)) || null;
              }

              function renderDetail(report){
                if (!detailContent) return;
                detailContent.innerHTML = '';
                const wrapper = document.createElement('div');
                wrapper.className = 'report-detail-grid';

                function addRow(label, value){
                  const row = document.createElement('div');
                  row.className = 'report-detail-row';
                  const key = document.createElement('span');
                  key.className = 'label';
                  key.textContent = label;
                  const val = document.createElement('span');
                  val.className = 'value';
                  val.textContent = value || '—';
                  row.appendChild(key);
                  row.appendChild(val);
                  wrapper.appendChild(row);
                }

                addRow('Report #', report.id);
                addRow('Order #', report.order_number || report.order_id || '—');
                addRow('Issue', ISSUE_LABELS[report.issue_type] || report.description || humanize(report.issue_type || ''));
                addRow('Status', humanize(report.status || 'open'));
                addRow('Filed', formatDate(report.created_at));
                addRow('Reporter', report.reporter_name || report.reporter_username || '—');
                if (report.total_amount != null) {
                  addRow('Order Total', `₱${Number(report.total_amount || 0).toFixed(2)}`);
                }
                if (report.rider_name) {
                  addRow('Assigned Rider', report.rider_name);
                }
                if (report.escalated_to_admin) {
                  addRow('Escalated At', formatDate(report.escalated_at));
                  if (report.escalation_note) {
                    addRow('Escalation Note', report.escalation_note);
                  }
                }

                if (report.message) {
                  const noteBlock = document.createElement('div');
                  noteBlock.className = 'report-detail-note';
                  const heading = document.createElement('div');
                  heading.className = 'label';
                  heading.textContent = 'Buyer Message';
                  const body = document.createElement('p');
                  body.textContent = report.message;
                  noteBlock.appendChild(heading);
                  noteBlock.appendChild(body);
                  wrapper.appendChild(noteBlock);
                }

                detailContent.appendChild(wrapper);
              }

              function openDetail(reportId){
                const report = findReport(reportId);
                if (!report || !detailModal) {
                  showToast('Report not found.', 'error');
                  return;
                }
                renderDetail(report);
                detailModal.style.display = 'block';
              }

              function closeDetail(){
                if (detailModal) detailModal.style.display = 'none';
              }

              function openEscalate(reportId, triggerBtn){
                const report = findReport(reportId);
                if (!report || !escalateModal) {
                  showToast('Report not found.', 'error');
                  return;
                }
                activeEscalateButton = triggerBtn || null;
                if (escalateIdInput) escalateIdInput.value = reportId;
                if (escalationNoteField) {
                  escalationNoteField.value = report.escalation_note || '';
                  escalationNoteField.focus();
                }
                if (escalateError) {
                  escalateError.style.display = 'none';
                  escalateError.textContent = '';
                }
                escalateModal.style.display = 'block';
              }

              function closeEscalate(){
                if (escalateModal) escalateModal.style.display = 'none';
                if (escalateForm) {
                  try { escalateForm.reset(); } catch (err) {}
                }
                if (escalateError) {
                  escalateError.style.display = 'none';
                  escalateError.textContent = '';
                }
                activeEscalateButton = null;
              }

              function updateRow(reportId, updates){
                const row = document.querySelector(`tr[data-report-id="${reportId}"]`);
                if (!row) return;
                if (updates.status) {
                  row.dataset.status = updates.status;
                  const badge = row.querySelector('.status-badge');
                  if (badge) {
                    const statusName = updates.status.toLowerCase();
                    badge.className = 'status-badge status-' + statusName;
                    badge.textContent = humanize(updates.status);
                  }
                }
                if (updates.escalated_to_admin) {
                  row.dataset.escalated = '1';
                  const statusCell = row.querySelector('td[data-label="Status"]');
                  if (statusCell && !statusCell.querySelector('small')) {
                    const note = document.createElement('small');
                    note.style.display = 'block';
                    note.style.color = '#b91c1c';
                    note.style.fontWeight = '600';
                    note.style.marginTop = '4px';
                    note.textContent = 'Escalated to admin';
                    statusCell.appendChild(note);
                  }
                  const escalateBtn = row.querySelector('.btn-escalate-report');
                  if (escalateBtn) {
                    escalateBtn.disabled = true;
                    escalateBtn.textContent = 'Escalated';
                  }
                }
              }

              window.closeSellerReportDetail = closeDetail;
              window.closeSellerReportEscalate = closeEscalate;

              document.addEventListener('click', function(ev){
                const viewBtn = ev.target.closest && ev.target.closest('.btn-view-report');
                if (viewBtn) {
                  ev.preventDefault();
                  const reportId = viewBtn.getAttribute('data-report-id');
                  if (reportId) openDetail(reportId);
                  return;
                }
                const escalateBtn = ev.target.closest && ev.target.closest('.btn-escalate-report');
                if (escalateBtn) {
                  ev.preventDefault();
                  if (escalateBtn.disabled) return;
                  const reportId = escalateBtn.getAttribute('data-report-id');
                  if (reportId) openEscalate(reportId, escalateBtn);
                }
              });

              if (escalateForm) {
                escalateForm.addEventListener('submit', async function(ev){
                  ev.preventDefault();
                  const reportId = escalateIdInput ? escalateIdInput.value : '';
                  if (!reportId) {
                    showToast('No report selected.', 'error');
                    return;
                  }
                  const note = (escalationNoteField ? escalationNoteField.value : '').trim();
                  if (!note) {
                    if (escalateError) {
                      escalateError.textContent = 'Please describe why this report needs admin review.';
                      escalateError.style.display = 'block';
                    }
                    return;
                  }
                  if (escalateError) {
                    escalateError.style.display = 'none';
                    escalateError.textContent = '';
                  }
                  if (escalateSubmitBtn) {
                    escalateSubmitBtn.disabled = true;
                    escalateSubmitBtn.textContent = 'Sending…';
                  }
                  let escalateSucceeded = false;
                  try {
                    const res = await fetch(`/api/seller/reports/${encodeURIComponent(reportId)}/escalate`, {
                      method: 'POST',
                      credentials: 'include',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ note })
                    });
                    const data = await res.json().catch(() => ({}));
                    if (!res.ok || !data || !data.success) {
                      const msg = (data && data.msg) ? data.msg : 'Unable to escalate this report right now.';
                      throw new Error(msg);
                    }

                    const report = findReport(reportId);
                    if (report) {
                      report.status = 'escalated';
                      report.escalated_to_admin = true;
                      report.escalated_at = data.escalated_at || new Date().toISOString();
                      report.escalation_note = note;
                    }
                    updateRow(reportId, { status: 'escalated', escalated_to_admin: true });
                    closeEscalate();
                     if (activeEscalateButton) {
                      activeEscalateButton.disabled = true;
                      activeEscalateButton.textContent = 'Escalated';
                     }
                     escalateSucceeded = true;
                    showToast(data.msg || 'Report escalated to admin.', 'success');
                  } catch (error) {
                    if (escalateError) {
                      escalateError.textContent = error.message || 'Unable to escalate this report right now.';
                      escalateError.style.display = 'block';
                    } else {
                      showToast(error.message || 'Unable to escalate this report right now.', 'error');
                    }
                  } finally {
                    if (escalateSubmitBtn) {
                      escalateSubmitBtn.disabled = false;
                      escalateSubmitBtn.textContent = 'Escalate Report';
                    }
                    if (!escalateSucceeded && activeEscalateButton) {
                      // keep button interactive on failure
                      activeEscalateButton.focus();
                    }
                    activeEscalateButton = null;
                  }
                });
              }

              window.addEventListener('click', function(ev){
                if (ev.target === detailModal) closeDetail();
                if (ev.target === escalateModal) closeEscalate();
              });
            })();

  // Inject lightweight styles so the seller chat panel matches the product page chatbox look
  (function injectSellerChatStyles(){
    try{
      const css = `
        /* Seller chat panel: mimic product_detail chat modal */
        #sellerChatsOverlay { backdrop-filter: blur(4px); }
        #sellerChatsOverlay > div { border-radius:12px; overflow:hidden; }
        #sellerChatPanel { background: #ffffff; display:flex; flex-direction:column; }
        #sellerChatHeader { padding:12px 16px; border-bottom:1px solid #eef2f7; background:#f8fafc; display:flex; align-items:center; justify-content:space-between; font-weight:600; }
        #sellerChatMessages { padding:12px; background: #fbfdff; display:flex; flex-direction:column; gap:8px; overflow:auto; }
        /* message bubbles: keep JS alignment but standardize paddings and radii */
        #sellerChatMessages div[data-message-id] { max-width: 78%; padding:8px 12px; border-radius:12px; font-size:14px; line-height:1.3; }
        /* user (left) bubble */
        #sellerChatMessages div[data-message-id][data-sender='user'],
        #sellerChatMessages div.user-bubble { background:#f1f5f9; color:#0f1724; align-self:flex-start; }
        /* seller (right) bubble */
        #sellerChatMessages div[data-message-id][data-sender='seller'],
        #sellerChatMessages div.seller-bubble { background:#0b73ff; color:#fff; align-self:flex-end; }
        /* input area */
        #sellerChatPanel .chat-input-row { padding:12px; border-top:1px solid #eef2f7; display:flex; gap:8px; align-items:center; background:#fafafa; }
        #sellerChatPanel .chat-input-row input[type=text] { flex:1;padding:10px 12px;border-radius:8px;border:1px solid #e6eef8;font-size:14px; }
        #sellerChatPanel .chat-input-row button { padding:8px 12px;border-radius:8px;border:none;background:#007bff;color:#fff;font-weight:600;cursor:pointer; }
      `;
      const s = document.createElement('style'); s.setAttribute('data-generated','seller-chat-styles'); s.appendChild(document.createTextNode(css));
      document.head.appendChild(s);
    }catch(e){ console.error('injectSellerChatStyles', e); }
  })();

  document.addEventListener('DOMContentLoaded', function(){
    let restrictionState = {};
    try {
      restrictionState = JSON.parse(document.body.getAttribute('data-restriction-state') || '{}') || {};
    } catch (err) {
      restrictionState = {};
    }
    const level = Number(restrictionState.level || 0);
    const overlay = document.getElementById('restrictionOverlay');
    const main = document.querySelector('.admin-main');

    function showRestrictionOverlay() {
      if (!overlay) return;
      overlay.classList.add('visible');
      document.body.style.overflow = 'hidden';
      if (main) main.classList.add('content-blur');
    }

    function hideRestrictionOverlay() {
      if (!overlay) return;
      overlay.classList.remove('visible');
      document.body.style.overflow = '';
      if (main) main.classList.remove('content-blur');
    }

    if (overlay && overlay.classList.contains('visible')) {
      showRestrictionOverlay();
    }

    const copyEmailBtn = document.getElementById('copyAdminEmailBtn');
    if (copyEmailBtn) {
      copyEmailBtn.addEventListener('click', async () => {
        const email = copyEmailBtn.getAttribute('data-email') || '';
        if (!email) {
          return;
        }
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(email);
          } else {
            const temp = document.createElement('textarea');
            temp.value = email;
            temp.setAttribute('readonly', '');
            temp.style.position = 'absolute';
            temp.style.left = '-9999px';
            document.body.appendChild(temp);
            temp.select();
            document.execCommand('copy');
            document.body.removeChild(temp);
          }
          if (window.tinyFlash) {
            window.tinyFlash('Admin email copied to clipboard.', 'success');
          } else {
            alert('Admin email copied to clipboard.');
          }
        } catch (err) {
          console.error('Failed to copy admin email', err);
          if (window.tinyFlash) {
            window.tinyFlash('Unable to copy email. Please copy manually.', 'error');
          } else {
            alert('Unable to copy automatically. Please copy the email manually.');
          }
        }
      });
    }

    if (level === 2) {
      const warningId = overlay ? (overlay.getAttribute('data-warning-id') || '') : '';
      const ackKey = warningId ? `sellerWarningAck_${warningId}` : 'sellerWarningAck';
      let alreadyAcknowledged = false;
      try {
        alreadyAcknowledged = sessionStorage.getItem(ackKey) === 'ack';
      } catch (err) {
        alreadyAcknowledged = false;
      }
      if (alreadyAcknowledged) {
        hideRestrictionOverlay();
      }

      const proceedBtn = document.getElementById('warningProceedBtn');
      if (proceedBtn) {
        proceedBtn.addEventListener('click', () => {
          try {
            sessionStorage.setItem(ackKey, 'ack');
          } catch (err) {
            console.debug('Unable to persist warning acknowledgement', err);
          }
          hideRestrictionOverlay();
        });
      }
    }

    if (level >= 3) {
      const appealBtn = document.getElementById('submitAppealBtn');
      const freezeContent = document.getElementById('freezeContent');
      const appealContent = document.getElementById('appealContent');
      const cancelAppealBtn = document.getElementById('cancelAppealBtn');
      const sendAppealBtn = document.getElementById('sendAppealBtn');
      const appealReasonInput = document.getElementById('appealReason');

      if (appealBtn && freezeContent && appealContent) {
        appealBtn.addEventListener('click', function() {
          freezeContent.style.display = 'none';
          appealContent.style.display = 'block';
          if (appealReasonInput) appealReasonInput.focus();
        });
      }

      if (cancelAppealBtn && freezeContent && appealContent) {
        cancelAppealBtn.addEventListener('click', function() {
          appealContent.style.display = 'none';
          freezeContent.style.display = 'block';
          if (appealReasonInput) appealReasonInput.value = ''; // Optional: clear input on cancel
        });
      }

      if (sendAppealBtn && appealReasonInput) {
        sendAppealBtn.addEventListener('click', async function() {
          const reason = appealReasonInput.value.trim();
          if (!reason) {
            if (window.Swal) {
              await Swal.fire({ icon: 'error', title: 'Appeal required', text: 'Please describe why your account should be unfrozen.' });
            } else {
              alert('Please describe why your account should be unfrozen.');
            }
            return;
          }

          sendAppealBtn.disabled = true;
          const originalText = sendAppealBtn.textContent;
          sendAppealBtn.textContent = 'Sending…';

          try {
            const res = await fetch('/seller/restrictions/appeal', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ message: reason })
            });
            const json = await res.json().catch(() => null);

            if (res.ok && json && json.success) {
              // Switch to pending view immediately
              if (appealContent) appealContent.style.display = 'none';
              const pending = document.getElementById('appealPendingContent');
              if (pending) {
                pending.style.display = 'block';
              } else {
                // Fallback: reload to show server-rendered pending state
                window.location.reload();
                return;
              }
              if (appealReasonInput) appealReasonInput.value = '';
              
              // Optional non-blocking feedback
              if (window.tinyFlash) tinyFlash('Appeal sent. Admin will review shortly.', 'success');
            } else {
              const message = (json && json.msg) || 'Failed to send appeal.';
              if (window.Swal) {
                Swal.fire({ icon: 'error', title: 'Could not send appeal', text: message });
              } else {
                alert(message);
              }
            }
          } catch (err) {
            console.error('Appeal submit failed', err);
            if (window.Swal) {
              Swal.fire({ icon: 'error', title: 'Network error', text: 'Please try again shortly.' });
            } else {
              alert('Network error. Please try again shortly.');
            }
          } finally {
            sendAppealBtn.disabled = false;
            sendAppealBtn.textContent = originalText;
          }
        });
      }
    }
  });
