(function(){
  var initialized = false;
  var currentProduct = null;
  var checkoutMode = null;

  function getModal(){
    return document.getElementById('checkoutModal');
  }

  function closeCheckoutModal(){
    var modal = getModal();
    if (modal) modal.style.display = 'none';
    checkoutMode = null;
    currentProduct = null;
  }

  async function applyAddressToCheckoutForm(addr){
    if (!addr) return;
    try {
      // Text fields (home address, contact number)
      var textMap = {
        home_address: 'chk_home_address',
        contact_number: 'chk_contact_number'
      };
      Object.keys(textMap).forEach(function(key){
        var el = document.getElementById(textMap[key]);
        if (el) el.value = addr[key] || '';
      });
      // Geographic dropdowns (region, province, city, barangay)
      await applyAddressGeoDropdowns(addr);
    } catch(e) {
      console.error('applyAddressToCheckoutForm error', e);
    }
  }

  async function loadSavedAddressIntoModal(){
    var list = document.getElementById('chk_savedAddressesList');
    if (!list) return;
    list.innerHTML = '<p class="saved-empty">Loading address...</p>';
    try {
      var resp = await fetch('/api/user/address', { credentials: 'same-origin' });
      var data = await resp.json();
      if (!data || !data.success || !data.address){
        list.innerHTML = '<p class="saved-empty">No saved address yet.</p>';
        return;
      }
      var addr = data.address;
      list.innerHTML = '';
      var card = document.createElement('div');
      card.id = 'chk_savedAddressCard';
      card.className = 'saved-address-card';
      card.style.padding = '10px';
      card.style.borderRadius = '8px';
      card.style.border = '1px solid #e5e7eb';
      card.style.background = '#ffffff';
      card.style.cursor = 'pointer';
      card.innerHTML = '' +
        '<div style="font-weight:600;margin-bottom:4px;">Saved Address</div>' +
        '<div style="font-size:.9rem;color:#111;">' + (addr.home_address || '') + '</div>' +
        '<div style="font-size:.85rem;color:#4b5563;">' + (addr.barangay || '') + ', ' + (addr.city || '') + '</div>' +
        '<div style="font-size:.85rem;color:#4b5563;">' + (addr.province || '') + ', ' + (addr.region || '') + '</div>' +
        '<div style="font-size:.85rem;color:#4b5563;margin-top:4px;">Contact: ' + (addr.contact_number || '') + '</div>';
      list.appendChild(card);
      card.addEventListener('click', function(){ applyAddressToCheckoutForm(addr); });
      // Auto-apply on load
      await applyAddressToCheckoutForm(addr);
    } catch (e) {
      console.error('Failed to load saved address', e);
      list.innerHTML = '<p class="saved-empty" style="color:#ef4444;">Failed to load saved address.</p>';
    }
  }

  function initHandlers(){
    if (initialized) return;
    initialized = true;
    var modal = getModal();
    if (!modal) return;

    var closeBtn = document.getElementById('checkoutClose');
    var cancelBtn = document.getElementById('chk_cancel');
    if (closeBtn) closeBtn.addEventListener('click', function(){ closeCheckoutModal(); });
    if (cancelBtn) cancelBtn.addEventListener('click', function(){ closeCheckoutModal(); });

    // backdrop click
    modal.addEventListener('click', function(ev){ if (ev.target === modal) closeCheckoutModal(); });

    // Save Address modal controls
    var saveModal = document.getElementById('saveAddressModal');
    var openSaveBtn = document.getElementById('chk_openSaveAddress');
    var saClose = document.getElementById('sa_close');
    var saCancel = document.getElementById('sa_cancel');
    function openSaveModal(){
      if (!saveModal) return;
      // Prefill from main checkout form
      try {
        var map = {
          region: ['chk_region','sa_region'],
          province: ['chk_province','sa_province'],
          city: ['chk_city','sa_city'],
          barangay: ['chk_barangay','sa_barangay'],
          home_address: ['chk_home_address','sa_home_address'],
          contact_number: ['chk_contact_number','sa_contact_number']
        };
        Object.keys(map).forEach(function(key){
          var src = document.getElementById(map[key][0]);
          var dest = document.getElementById(map[key][1]);
          if (!src || !dest) return;
          // For geographic dropdowns, use the selected option's label; for others, use raw value
          if ((key === 'region' || key === 'province' || key === 'city' || key === 'barangay') && src.tagName === 'SELECT'){
            var sel = src.selectedOptions && src.selectedOptions[0];
            dest.value = sel ? sel.textContent.trim() : '';
          } else {
            dest.value = src.value || '';
          }
        });
      } catch(_){ }
      saveModal.style.display = 'block';
    }
    function closeSaveModal(){ if (saveModal) saveModal.style.display = 'none'; }
    if (openSaveBtn) openSaveBtn.addEventListener('click', openSaveModal);
    if (saClose) saClose.addEventListener('click', closeSaveModal);
    if (saCancel) saCancel.addEventListener('click', closeSaveModal);
    if (saveModal) {
      saveModal.addEventListener('click', function(ev){ if (ev.target === saveModal) closeSaveModal(); });
    }

    // Initialize PH geographical dropdowns
    setupGeoDropdowns();

    var saveForm = document.getElementById('saveAddressForm');
    if (saveForm) {
      saveForm.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var fd = new FormData(saveForm);
        var payload = {
          region: (fd.get('region') || '').trim(),
          province: (fd.get('province') || '').trim(),
          city: (fd.get('city') || '').trim(),
          barangay: (fd.get('barangay') || '').trim(),
          home_address: (fd.get('home_address') || '').trim(),
          contact_number: (fd.get('contact_number') || '').trim()
        };
        if (!payload.region || !payload.province || !payload.city || !payload.barangay || !payload.home_address || !payload.contact_number){
          if (window.Swal){ window.Swal.fire({ icon:'warning', title:'Missing fields', text:'Please fill in all address fields.' }); }
          else { alert('Please fill in all address fields.'); }
          return;
        }
        try {
          var resp = await fetch('/api/user/address', {
            method: 'POST',
            headers: { 'Content-Type':'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
          });
          var data = await resp.json();
          if (data && data.success){
            if (window.Swal){ window.Swal.fire({ icon:'success', title:'Address saved', text:'Your address has been saved.' }); }
            applyAddressToCheckoutForm(payload);
            closeSaveModal();
            loadSavedAddressIntoModal();
          } else {
            var msg = (data && data.msg) || 'Failed to save address.';
            if (window.Swal){ window.Swal.fire({ icon:'error', title:'Error', text: msg }); }
            else { alert(msg); }
          }
        } catch(err){
          console.error('Save address error', err);
          if (window.Swal){ window.Swal.fire({ icon:'error', title:'Error', text:'Failed to save address. Please try again.' }); }
          else { alert('Failed to save address. Please try again.'); }
        }
      });
    }

    var checkoutForm = document.getElementById('checkoutFormAjax');
    if (checkoutForm) {
      checkoutForm.addEventListener('submit', async function(ev){
        ev.preventDefault();
        var fd = new FormData(checkoutForm);
        var regionEl = document.getElementById('chk_region');
        var provinceEl = document.getElementById('chk_province');
        var cityEl = document.getElementById('chk_city');
        var barangayEl = document.getElementById('chk_barangay');
        var payload = {
          region: regionEl && regionEl.selectedOptions[0] ? regionEl.selectedOptions[0].textContent.trim() : '',
          province: provinceEl && provinceEl.selectedOptions[0] ? provinceEl.selectedOptions[0].textContent.trim() : '',
          city: cityEl && cityEl.selectedOptions[0] ? cityEl.selectedOptions[0].textContent.trim() : '',
          barangay: barangayEl && barangayEl.selectedOptions[0] ? barangayEl.selectedOptions[0].textContent.trim() : '',
          home_address: (fd.get('home_address') || '').trim(),
          contact_number: (fd.get('contact_number') || '').trim(),
          payment_method: (fd.get('payment_method') || 'cash_on_delivery').trim()
        };
        if (checkoutMode === 'direct_product' && currentProduct && currentProduct.product_id){
          payload.product_id = currentProduct.product_id;
          payload.quantity = currentProduct.quantity || 1;
          payload.mode = 'direct_product';
        }
        if (!payload.region || !payload.province || !payload.city || !payload.barangay || !payload.home_address || !payload.contact_number){
          var msg = 'Please fill in all required fields.';
          if (window.Swal){ window.Swal.fire({ icon:'warning', title:'Incomplete address', text: msg }); }
          else { alert(msg); }
          return;
        }
        try {
          var resp = await fetch('/checkout', {
            method: 'POST',
            headers: { 'Content-Type':'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
          });
          var ct = resp.headers.get('content-type') || '';
          if (!ct.includes('application/json')){
            var text = await resp.text();
            console.error('Non-JSON response:', text);
            if (window.Swal){ window.Swal.fire({ icon:'error', title:'Server error', text:'Please check if the server is running properly.' }); }
            else { alert('Server error: Please check if the server is running properly.'); }
            return;
          }
          var data = await resp.json();
          if (data && data.success){
            var go = function(){ closeCheckoutModal(); window.location.href = '/orders'; };
            if (window.Swal){
              window.Swal.fire({ icon:'success', title:'Checkout successful!', text:'Please proceed to Your Orders to track your order.' }).then(go).catch(go);
            } else {
              alert('Checkout successful! Please proceed to Your Orders to track your order.');
              go();
            }
          } else {
            var emsg = (data && data.msg) ? String(data.msg) : 'Checkout failed';
            if (window.Swal){ window.Swal.fire({ icon:'error', title:'Checkout failed', text: emsg }); }
            else { alert('Error: ' + emsg); }
          }
        } catch(err){
          console.error('Checkout error', err);
          if (window.Swal){ window.Swal.fire({ icon:'error', title:'Checkout error', text:'Please try again.' }); }
          else { alert('An error occurred during checkout. Please try again.'); }
        }
      });
    }
  }

  function selectOptionByText(select, text){
    if (!select || !text) return;
    var target = text.trim().toLowerCase();
    for (var i = 0; i < select.options.length; i++){
      var opt = select.options[i];
      if (opt.textContent.trim().toLowerCase() === target){
        select.selectedIndex = i;
        break;
      }
    }
  }

  async function loadRegionsForCheckout(selectedName){
    var regionSelect = document.getElementById('chk_region');
    if (!regionSelect) return;
    regionSelect.innerHTML = '<option value="">Select Region</option>';
    try {
      var resp = await fetch('/get_regions');
      var regions = await resp.json();
      regions.forEach(function(region){
        var opt = document.createElement('option');
        opt.value = region.code;
        opt.textContent = region.name;
        regionSelect.appendChild(opt);
      });
      if (selectedName){
        selectOptionByText(regionSelect, selectedName);
      }
    } catch(e){
      console.error('Error loading regions for checkout modal', e);
    }
  }

  async function loadProvincesForCheckout(selectedName){
    var regionSelect = document.getElementById('chk_region');
    var provinceSelect = document.getElementById('chk_province');
    var citySelect = document.getElementById('chk_city');
    var barangaySelect = document.getElementById('chk_barangay');
    if (!regionSelect || !provinceSelect || !citySelect || !barangaySelect) return;
    var regionCode = regionSelect.value;
    provinceSelect.innerHTML = '<option value="">Select Province</option>';
    citySelect.innerHTML = '<option value="">Select City/Municipality</option>';
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    if (!regionCode) return;
    try {
      var resp = await fetch('/get_provinces/' + encodeURIComponent(regionCode));
      var contentType = resp.headers.get('content-type') || '';
      if (!contentType.includes('application/json')){
        console.error('Non-JSON response for provinces:', await resp.text());
        return;
      }
      var provinces = await resp.json();
      provinces.forEach(function(province){
        var opt = document.createElement('option');
        opt.value = province.code;
        opt.textContent = province.name;
        provinceSelect.appendChild(opt);
      });
      if (selectedName){
        selectOptionByText(provinceSelect, selectedName);
      }
    } catch(e){
      console.error('Error loading provinces for checkout modal', e);
    }
  }

  async function loadCitiesForCheckout(selectedName){
    var provinceSelect = document.getElementById('chk_province');
    var citySelect = document.getElementById('chk_city');
    var barangaySelect = document.getElementById('chk_barangay');
    if (!provinceSelect || !citySelect || !barangaySelect) return;
    var provinceCode = provinceSelect.value;
    citySelect.innerHTML = '<option value="">Select City/Municipality</option>';
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    if (!provinceCode) return;
    try {
      var resp = await fetch('/get_cities/' + encodeURIComponent(provinceCode));
      var contentType = resp.headers.get('content-type') || '';
      if (!contentType.includes('application/json')){
        console.error('Non-JSON response for cities:', await resp.text());
        return;
      }
      var cities = await resp.json();
      cities.forEach(function(city){
        var opt = document.createElement('option');
        opt.value = city.code;
        opt.textContent = city.name;
        citySelect.appendChild(opt);
      });
      if (selectedName){
        selectOptionByText(citySelect, selectedName);
      }
    } catch(e){
      console.error('Error loading cities for checkout modal', e);
    }
  }

  async function loadBarangaysForCheckout(selectedName){
    var citySelect = document.getElementById('chk_city');
    var barangaySelect = document.getElementById('chk_barangay');
    if (!citySelect || !barangaySelect) return;
    var cityCode = citySelect.value;
    barangaySelect.innerHTML = '<option value="">Select Barangay</option>';
    if (!cityCode) return;
    try {
      var resp = await fetch('/get_barangays/' + encodeURIComponent(cityCode));
      var contentType = resp.headers.get('content-type') || '';
      if (!contentType.includes('application/json')){
        console.error('Non-JSON response for barangays:', await resp.text());
        return;
      }
      var barangays = await resp.json();
      barangays.forEach(function(bar){
        var opt = document.createElement('option');
        opt.value = bar.code;
        opt.textContent = bar.name;
        barangaySelect.appendChild(opt);
      });
      if (selectedName){
        selectOptionByText(barangaySelect, selectedName);
      }
    } catch(e){
      console.error('Error loading barangays for checkout modal', e);
    }
  }

  function setupGeoDropdowns(){
    var regionSelect = document.getElementById('chk_region');
    var provinceSelect = document.getElementById('chk_province');
    var citySelect = document.getElementById('chk_city');
    var barangaySelect = document.getElementById('chk_barangay');
    if (!regionSelect || !provinceSelect || !citySelect || !barangaySelect) return;
    regionSelect.addEventListener('change', function(){ loadProvincesForCheckout(); });
    provinceSelect.addEventListener('change', function(){ loadCitiesForCheckout(); });
    citySelect.addEventListener('change', function(){ loadBarangaysForCheckout(); });
    // Initial population of regions
    loadRegionsForCheckout();
  }

  async function applyAddressGeoDropdowns(addr){
    if (!addr) return;
    try {
      await loadRegionsForCheckout(addr.region || '');
      await loadProvincesForCheckout(addr.province || '');
      await loadCitiesForCheckout(addr.city || '');
      await loadBarangaysForCheckout(addr.barangay || '');
    } catch(e){
      console.error('Failed to apply geo dropdowns from address', e);
    }
  }

  function renderProductSummary(opts){
    var summary = document.getElementById('chk_orderSummary');
    if (!summary) return;
    var name = opts && opts.name ? String(opts.name) : 'Product';
    var qty = opts && opts.quantity ? parseInt(opts.quantity,10) || 1 : 1;
    var price = opts && opts.price ? Number(opts.price) || 0 : 0;
    var total = price * qty;
    summary.innerHTML = '' +
      '<div>' +
      '  <h3>Order Summary</h3>' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
      '    <span>' + name + ' × ' + qty + '</span>' +
      '    <span>₱' + total.toFixed(2) + '</span>' +
      '  </div>' +
      '</div>';
  }

  async function openForProduct(opts){
    var modal = getModal();
    if (!modal) return;
    if (!initialized) initHandlers();
    // Track direct product context for backend checkout
    checkoutMode = 'direct_product';
    currentProduct = null;
    try {
      var pid = opts && (opts.productId || opts.product_id);
      var qtyRaw = opts && (opts.quantity != null ? opts.quantity : 1);
      var pidNum = pid != null ? parseInt(pid, 10) : null;
      var qtyNum = parseInt(qtyRaw, 10);
      if (!Number.isNaN(pidNum) && pidNum > 0){
        if (Number.isNaN(qtyNum) || qtyNum < 1) qtyNum = 1;
        currentProduct = { product_id: pidNum, quantity: qtyNum };
      }
    } catch(e){
      console.error('Failed to capture direct product context', e);
    }
    renderProductSummary(opts || {});
    modal.style.display = 'flex';
    try { await loadSavedAddressIntoModal(); } catch(e){}
  }

  window.CheckoutModal = {
    openForProduct: openForProduct,
    loadSavedAddress: loadSavedAddressIntoModal,
    applyAddress: applyAddressToCheckoutForm,
    close: closeCheckoutModal
  };
})();
