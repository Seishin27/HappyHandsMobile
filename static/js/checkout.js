// Dedicated checkout page logic for BabyBloom / Happy Hands
// Handles saved addresses, PH geo dropdowns, order summary, and checkout submission.

(function(){
  // Get user ID from body attribute to ensure addresses are saved per user
  const userId = document.body.getAttribute('data-user-id') || 'guest';
  const STORAGE_KEY = 'hh_checkout_addresses_' + userId;

  function $(sel){ return document.querySelector(sel); }

  function safeParseJSON(str, fallback){
    if (!str) return fallback;
    try { return JSON.parse(str); } catch(e){ return fallback; }
  }

  var placeOrderBtn = null;
  var currentShippingEstimate = 0;
  var currentCheckoutMode = 'cart';
  var currentDirectItem = null;
  var currentCartItems = [];

  function loadLocalAddresses(){
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const data = safeParseJSON(raw, []);
      return Array.isArray(data) ? data : [];
    } catch (e){ return []; }
  }

  function saveLocalAddresses(addrs){
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(addrs || [])); } catch (e){}
  }

  function buildAddressFromForm(){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    const homeInput = $('#homeAddress');
    const contactInput = $('#contactNumber');

    const regionName = regionSel && regionSel.selectedOptions[0] ? regionSel.selectedOptions[0].textContent.trim() : '';
    const provinceName = provSel && provSel.selectedOptions[0] ? provSel.selectedOptions[0].textContent.trim() : '';
    const cityName = citySel && citySel.selectedOptions[0] ? citySel.selectedOptions[0].textContent.trim() : '';
    const barangayName = brgySel && brgySel.selectedOptions[0] ? brgySel.selectedOptions[0].textContent.trim() : '';
    const home = homeInput ? homeInput.value.trim() : '';
    const contact = contactInput ? contactInput.value.trim() : '';

    return {
      id: Date.now(),
      label: home || [barangayName, cityName].filter(Boolean).join(', ') || 'Address',
      region: regionName,
      province: provinceName,
      city: cityName,
      barangay: barangayName,
      home_address: home,
      contact_number: contact
    };
  }

  function validateAddress(addr){
    return !!(addr && addr.region && addr.province && addr.city && addr.barangay && addr.home_address && addr.contact_number);
  }

  function getAddressFromFormForValidation(){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    const homeInput = $('#homeAddress');
    const contactInput = $('#contactNumber');

    const regionName = regionSel && regionSel.selectedOptions[0] ? regionSel.selectedOptions[0].textContent.trim() : '';
    const provinceName = provSel && provSel.selectedOptions[0] ? provSel.selectedOptions[0].textContent.trim() : '';
    const cityName = citySel && citySel.selectedOptions[0] ? citySel.selectedOptions[0].textContent.trim() : '';
    const barangayName = brgySel && brgySel.selectedOptions[0] ? brgySel.selectedOptions[0].textContent.trim() : '';
    const home = homeInput ? homeInput.value.trim() : '';
    const contact = contactInput ? contactInput.value.trim() : '';

    return {
      region: regionName,
      province: provinceName,
      city: cityName,
      barangay: barangayName,
      home_address: home,
      contact_number: contact
    };
  }

  function refreshPlaceOrderButtonState(){
    if (!placeOrderBtn){
      placeOrderBtn = document.getElementById('placeOrderBtn');
    }
    if (!placeOrderBtn) return;
    const addr = getAddressFromFormForValidation();
    const ok = validateAddress(addr);
    placeOrderBtn.disabled = !ok;
  }

  function buildCheckoutBody(mode, directItem, cartItems){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    const homeInput = $('#homeAddress');
    const contactInput = $('#contactNumber');
    const payment = document.querySelector('input[name="payment_method"]:checked');

    const regionName = regionSel && regionSel.selectedOptions[0] ? regionSel.selectedOptions[0].textContent.trim() : '';
    const provinceName = provSel && provSel.selectedOptions[0] ? provSel.selectedOptions[0].textContent.trim() : '';
    const cityName = citySel && citySel.selectedOptions[0] ? citySel.selectedOptions[0].textContent.trim() : '';
    const barangayName = brgySel && brgySel.selectedOptions[0] ? brgySel.selectedOptions[0].textContent.trim() : '';
    const home = homeInput ? homeInput.value.trim() : '';
    const contact = contactInput ? contactInput.value.trim() : '';
    const paymentMethod = payment ? String(payment.value || 'cash_on_delivery').trim() : 'cash_on_delivery';

    const payload = {
      region: (regionName && regionName !== 'Select Region') ? regionName : '',
      province: (provinceName && provinceName !== 'Select Province') ? provinceName : '',
      city: (cityName && cityName !== 'Select City/Municipality') ? cityName : '',
      barangay: (barangayName && barangayName !== 'Select Barangay') ? barangayName : '',
      home_address: home,
      contact_number: contact,
      payment_method: paymentMethod
    };

    if (mode === 'direct' && directItem && directItem.product_id){
      payload.product_id = directItem.product_id;
      payload.quantity = directItem.quantity || 1;
    } else if (mode === 'cart' && Array.isArray(cartItems) && cartItems.length > 0) {
      payload.items = cartItems.map(i => i.product_id);
    }

    return payload;
  }

  var _shippingDebounceTimer = null;
  var _fetchingShipping = false;
  var _shippingRequestToken = 0; // monotonic counter; only newest fetch wins
  var DEFAULT_SHIPPING_FEE = 36; // matches backend app/shipping_utils.py DEFAULT_SHIPPING_FEE
  var MIN_SHIPPING_FEE = DEFAULT_SHIPPING_FEE;
  var _lastShippingError = false; // when true, shippingEl shows em-dash for retry visibility

  // Estimate gate: province + city are enough (barangay optional).
  // The backend uses PSGC region-prefix matching, so partial addresses still compute correctly.
  function hasAddressDropdowns(){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const regionName = regionSel && regionSel.selectedOptions[0] ? regionSel.selectedOptions[0].textContent.trim() : '';
    const provinceName = provSel && provSel.selectedOptions[0] ? provSel.selectedOptions[0].textContent.trim() : '';
    const cityName = citySel && citySel.selectedOptions[0] ? citySel.selectedOptions[0].textContent.trim() : '';
    return !!(regionName && regionName !== 'Select Region'
           && provinceName && provinceName !== 'Select Province'
           && cityName && cityName !== 'Select City/Municipality');
  }

  async function refreshShippingEstimate(mode, directItem, cartItems){
    // Province + city are enough to estimate; barangay is optional.
    var gateOk = hasAddressDropdowns();
    console.log('[Shipping] Gate:', gateOk,
      '| region:', ($('#region') || {}).value,
      '| province:', ($('#province') || {}).value,
      '| city:', ($('#city') || {}).value,
      '| barangay:', ($('#barangay') || {}).value,
      '| mode:', mode,
      '| directItem:', directItem,
      '| cartItems.length:', Array.isArray(cartItems) ? cartItems.length : cartItems);
    if (!gateOk) {
      _fetchingShipping = false;
      _lastShippingError = false;
      currentShippingEstimate = DEFAULT_SHIPPING_FEE; // show ₱36 default
      renderOrderSummary(mode, cartItems, directItem);
      document.dispatchEvent(new CustomEvent('shipping:updated', { detail: { fee: currentShippingEstimate, source: 'default' } }));
      return;
    }

    // Debounce rapid dropdown changes
    if (_shippingDebounceTimer) clearTimeout(_shippingDebounceTimer);
    _shippingDebounceTimer = setTimeout(async function(){
      const payload = buildCheckoutBody(mode, directItem, cartItems);
      const myToken = ++_shippingRequestToken;
      console.log('[Shipping] Payload to API (token=' + myToken + '):', JSON.stringify(payload));

      // Show loading state while fetching
      _fetchingShipping = true;
      _lastShippingError = false;
      renderOrderSummary(mode, cartItems, directItem);

      try {
        const resp = await fetch('/api/shipping/estimate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });
        const data = await resp.json().catch(() => null);
        // Stale response — a newer request has been issued since; ignore this one.
        if (myToken !== _shippingRequestToken) {
          console.log('[Shipping] Ignoring stale response (token=' + myToken + ', current=' + _shippingRequestToken + ')');
          return;
        }
        console.log('[Shipping] API response:', data);
        if (data && data.success) {
          const rawFee = (data && data.shipping_fee !== undefined && data.shipping_fee !== null)
            ? Number(data.shipping_fee)
            : NaN;
          if (Number.isFinite(rawFee)) {
            currentShippingEstimate = Math.max(rawFee, MIN_SHIPPING_FEE);
            _lastShippingError = false;
          } else {
            console.warn('[Shipping] Non-finite shipping_fee, falling back to default:', data && data.shipping_fee);
            currentShippingEstimate = DEFAULT_SHIPPING_FEE;
            _lastShippingError = true;
          }
        } else {
          if (data && data.msg) console.warn('[Shipping] Server returned error:', data.msg);
          currentShippingEstimate = DEFAULT_SHIPPING_FEE;
          _lastShippingError = true;
        }
      } catch (e) {
        if (myToken !== _shippingRequestToken) return;
        console.error('[Shipping] Estimate fetch error:', e);
        currentShippingEstimate = DEFAULT_SHIPPING_FEE;
        _lastShippingError = true;
      }
      if (myToken !== _shippingRequestToken) return;
      console.log('[Shipping] Final estimate:', currentShippingEstimate, 'error?', _lastShippingError);
      _fetchingShipping = false;
      renderOrderSummary(mode, cartItems, directItem);
      // Notify listeners (order-total updaters etc.) that the shipping fee just changed.
      document.dispatchEvent(new CustomEvent('shipping:updated', {
        detail: { fee: currentShippingEstimate, error: _lastShippingError }
      }));
    }, 300);
  }

  function applyAddressToForm(addr){
    if (!addr) return;
    const homeInput = $('#homeAddress');
    const contactInput = $('#contactNumber');
    if (homeInput) homeInput.value = addr.home_address || '';
    if (contactInput) contactInput.value = addr.contact_number || '';
    const p = applyAddressGeoDropdowns(addr);
    if (p && typeof p.then === 'function'){
      p.then(function(){
        refreshPlaceOrderButtonState();
        refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
      }).catch(function(){
        refreshPlaceOrderButtonState();
      });
    } else {
      refreshPlaceOrderButtonState();
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    }
  }

  function renderAddressList(addresses){
    const list = document.getElementById('savedAddressesList');
    if (!list) return;
    list.innerHTML = '';

    if (!addresses || !addresses.length){
      const p = document.createElement('p');
      p.className = 'saved-empty';
      p.textContent = 'No saved addresses yet.';
      list.appendChild(p);
      return;
    }

    addresses.forEach(addr => {
      const card = document.createElement('div');
      card.className = 'saved-address-card';
      card.setAttribute('data-id', String(addr.id));

      const title = document.createElement('div');
      title.className = 'saved-address-title';
      title.textContent = addr.label || 'Saved address';

      const body = document.createElement('div');
      body.className = 'saved-address-body';
      body.textContent = [addr.home_address, addr.barangay, addr.city, addr.province, addr.region]
        .filter(Boolean)
        .join(', ');

      const contact = document.createElement('div');
      contact.className = 'saved-address-contact';
      contact.textContent = addr.contact_number ? 'Contact: ' + addr.contact_number : '';

      const actions = document.createElement('div');
      actions.className = 'saved-address-actions';

      const useBtn = document.createElement('button');
      useBtn.type = 'button';
      useBtn.className = 'saved-address-use';
      useBtn.textContent = 'Use';

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'saved-address-delete';
      delBtn.textContent = 'Delete';

      actions.appendChild(useBtn);
      actions.appendChild(delBtn);

      card.appendChild(title);
      card.appendChild(body);
      card.appendChild(contact);
      card.appendChild(actions);

      useBtn.addEventListener('click', function(){
        // mark selected
        document.querySelectorAll('.saved-address-card').forEach(c => c.classList.remove('is-selected'));
        card.classList.add('is-selected');
        applyAddressToForm(addr);
      });

      delBtn.addEventListener('click', function(){
        let ok = true;
        try{
          if (window.Swal){
            window.Swal.fire({icon:'warning', title:'Remove address?', text:'This will remove the saved address.', showCancelButton:true}).then(r=>{
              if (r && r.isConfirmed){
                const updated = (loadLocalAddresses() || []).filter(a => String(a.id) !== String(addr.id));
                saveLocalAddresses(updated);
                renderAddressList(updated);
              }
            });
            ok = false;
          } else if (window.confirm){
            ok = window.confirm('Remove this saved address?');
          }
        }catch(e){}
        if (ok){
          const updated = (loadLocalAddresses() || []).filter(a => String(a.id) !== String(addr.id));
          saveLocalAddresses(updated);
          renderAddressList(updated);
        }
      });

      list.appendChild(card);
    });
  }

  async function loadBackendAddressIntoLocal(){
    try {
      const resp = await fetch('/api/user/address', { credentials:'same-origin' });
      const data = await resp.json().catch(() => null);
      if (!data || !data.success || !data.address) return loadLocalAddresses();
      const addr = data.address;
      const local = loadLocalAddresses();
      const exists = local.some(a =>
        a.home_address === (addr.home_address || '') &&
        a.contact_number === (addr.contact_number || '') &&
        a.region === (addr.region || '') &&
        a.province === (addr.province || '') &&
        a.city === (addr.city || '') &&
        a.barangay === (addr.barangay || '')
      );
      if (!exists){
        local.unshift({
          id: Date.now(),
          label: addr.home_address || 'Saved address',
          region: addr.region || '',
          province: addr.province || '',
          city: addr.city || '',
          barangay: addr.barangay || '',
          home_address: addr.home_address || '',
          contact_number: addr.contact_number || ''
        });
        saveLocalAddresses(local);
      }
      return local;
    } catch (e){
      return loadLocalAddresses();
    }
  }

  async function saveAddressToBackend(addr){
    try{
      const payload = {
        region: addr.region || '',
        province: addr.province || '',
        city: addr.city || '',
        barangay: addr.barangay || '',
        home_address: addr.home_address || '',
        contact_number: addr.contact_number || ''
      };
      const resp = await fetch('/api/user/address', {
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        credentials:'same-origin',
        body: JSON.stringify(payload)
      });
      await resp.json().catch(()=>null);
    }catch(e){}
  }

  function selectOptionByText(select, text){
    if (!select || !text) return;
    const target = String(text).trim().toLowerCase();
    for (let i=0;i<select.options.length;i++){
      const opt = select.options[i];
      if (opt.textContent.trim().toLowerCase() === target){
        select.selectedIndex = i;
        break;
      }
    }
  }

  async function loadRegions(selectedName){
    const sel = $('#region');
    if (!sel) return;
    sel.innerHTML = '<option value="">Select Region</option>';
    try{
      const resp = await fetch('/get_regions');
      const data = await resp.json();
      (data || []).forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.code;
        opt.textContent = r.name;
        sel.appendChild(opt);
      });
      if (selectedName) selectOptionByText(sel, selectedName);
    }catch(e){ console.error('loadRegions error', e); }
  }

  async function loadProvinces(selectedName){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    if (!regionSel || !provSel || !citySel || !brgySel) return;
    const regionCode = regionSel.value;
    provSel.innerHTML = '<option value="">Select Province</option>';
    citySel.innerHTML = '<option value="">Select City/Municipality</option>';
    brgySel.innerHTML = '<option value="">Select Barangay</option>';
    if (!regionCode) return;
    try{
      const resp = await fetch('/get_provinces/' + encodeURIComponent(regionCode));
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')){
        console.error('Non-JSON provinces response', await resp.text());
        return;
      }
      const data = await resp.json();
      (data || []).forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.code;
        opt.textContent = p.name;
        if (p.city_direct) opt.dataset.cityDirect = 'true';
        provSel.appendChild(opt);
      });
      if (selectedName) selectOptionByText(provSel, selectedName);
    }catch(e){ console.error('loadProvinces error', e); }
  }

  async function loadCities(selectedName){
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    if (!provSel || !citySel || !brgySel) return;
    const provCode = provSel.value;
    citySel.innerHTML = '<option value="">Select City/Municipality</option>';
    brgySel.innerHTML = '<option value="">Select Barangay</option>';
    if (!provCode) return;

    // Province-less region (e.g. NCR): the "province" option IS the city
    const selectedProv = provSel.selectedOptions[0];
    if (selectedProv && selectedProv.dataset.cityDirect === 'true') {
      const opt = document.createElement('option');
      opt.value = selectedProv.value;
      opt.textContent = selectedProv.textContent;
      citySel.appendChild(opt);
      citySel.selectedIndex = 1; // select the only city option
      citySel.disabled = false;
      if (selectedName) selectOptionByText(citySel, selectedName);
      await loadBarangays();
      return;
    }

    try{
      const resp = await fetch('/get_cities/' + encodeURIComponent(provCode));
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')){
        console.error('Non-JSON cities response', await resp.text());
        return;
      }
      const data = await resp.json();
      (data || []).forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.code;
        opt.textContent = c.name;
        citySel.appendChild(opt);
      });
      if (selectedName) selectOptionByText(citySel, selectedName);
    }catch(e){ console.error('loadCities error', e); }
  }

  async function loadBarangays(selectedName){
    const citySel = $('#city');
    const brgySel = $('#barangay');
    if (!citySel || !brgySel) return;
    const cityCode = citySel.value;
    brgySel.innerHTML = '<option value="">Select Barangay</option>';
    if (!cityCode) return;
    try{
      const resp = await fetch('/get_barangays/' + encodeURIComponent(cityCode));
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')){
        console.error('Non-JSON barangays response', await resp.text());
        return;
      }
      const data = await resp.json();
      (data || []).forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.code;
        opt.textContent = b.name;
        brgySel.appendChild(opt);
      });
      if (selectedName) selectOptionByText(brgySel, selectedName);
    }catch(e){ console.error('loadBarangays error', e); }
  }

  async function applyAddressGeoDropdowns(addr){
    if (!addr) return;
    try{
      await loadRegions(addr.region || '');
      await loadProvinces(addr.province || '');
      await loadCities(addr.city || '');
      await loadBarangays(addr.barangay || '');
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    }catch(e){ console.error('applyAddressGeoDropdowns error', e); }
  }

  function setupGeoDropdowns(){
    const regionSel = $('#region');
    const provSel = $('#province');
    const citySel = $('#city');
    const brgySel = $('#barangay');
    if (!regionSel || !provSel || !citySel || !brgySel) return;
    // Wire change listeners for every dropdown so distance is recomputed on each pick.
    regionSel.addEventListener('change', function(){
      loadProvinces();
      _fetchingShipping = true;
      renderOrderSummary(currentCheckoutMode, currentCartItems, currentDirectItem);
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    });
    provSel.addEventListener('change', function(){
      loadCities();
      _fetchingShipping = true;
      renderOrderSummary(currentCheckoutMode, currentCartItems, currentDirectItem);
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    });
    citySel.addEventListener('change', function(){
      loadBarangays();
      _fetchingShipping = true;
      renderOrderSummary(currentCheckoutMode, currentCartItems, currentDirectItem);
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    });
    brgySel.addEventListener('change', function(){
      _fetchingShipping = true;
      renderOrderSummary(currentCheckoutMode, currentCartItems, currentDirectItem);
      refreshShippingEstimate(currentCheckoutMode, currentDirectItem, currentCartItems);
    });
    loadRegions();
  }

  function renderOrderSummary(mode, cartItems, directItem){
    const itemsContainer = document.getElementById('orderItems');
    const subtotalEl = document.getElementById('orderSubtotal');
    const shippingEl = document.getElementById('orderShipping');
    const totalEl = document.getElementById('orderTotal');
    if (!itemsContainer || !subtotalEl || !shippingEl || !totalEl) return;

    let items = [];
    if (mode === 'direct' && directItem){
      items.push({
        name: directItem.name || 'Product',
        quantity: directItem.quantity || 1,
        price: directItem.price || 0
      });
    } else if (Array.isArray(cartItems)) {
      items = cartItems.map(i => ({
        name: i.name,
        quantity: i.quantity,
        price: i.price
      }));
    }

    itemsContainer.innerHTML = '';
    let subtotal = 0;
    items.forEach(it => {
      const lineTotal = (Number(it.price) || 0) * (parseInt(it.quantity,10) || 0);
      subtotal += lineTotal;
      const row = document.createElement('div');
      row.className = 'order-item-row';
      row.innerHTML = '<div class="order-item-main">'
        + '<span class="order-item-name">' + String(it.name || 'Item') + '</span>'
        + '<span class="order-item-qty">× ' + (it.quantity || 0) + '</span>'
        + '</div>'
        + '<div class="order-item-amount">₱' + lineTotal.toFixed(2) + '</div>';
      itemsContainer.appendChild(row);
    });

    const shipping = currentShippingEstimate;
    subtotalEl.textContent = '₱' + subtotal.toFixed(2);

    // Reflect loading / error state on the shipping fee element via data attribute.
    shippingEl.setAttribute('data-shipping-loading', _fetchingShipping ? 'true' : 'false');
    if (_fetchingShipping) {
      shippingEl.textContent = 'Calculating…';
      totalEl.textContent = '—';
    } else if (_lastShippingError) {
      // Error state: em-dash signals "retry-able" — user can change a dropdown to refetch.
      shippingEl.textContent = '—';
      totalEl.textContent = '—';
    } else {
      shippingEl.textContent = '₱' + shipping.toFixed(2);
      totalEl.textContent = '₱' + (subtotal + shipping).toFixed(2);
    }
  }

  async function handlePlaceOrder(e, mode, directItem, cartItems){
    e.preventDefault();
    const payload = buildCheckoutBody(mode, directItem, cartItems);

    if (!validateAddress(payload)){
      const msg = 'Please fill in all required address fields.';
      if (window.Swal) window.Swal.fire({ icon:'warning', title:'Incomplete address', text: msg });
      else alert(msg);
      return;
    }

    const btn = e.target;
    if (btn && btn.disabled) return;
    if (btn) btn.disabled = true;

    try{
      const resp = await fetch('/checkout', {
        method:'POST',
        headers:{ 'Content-Type':'application/json' },
        credentials:'same-origin',
        body: JSON.stringify(payload)
      });
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')){
        const txt = await resp.text();
        console.error('Non-JSON checkout response', txt);
        if (window.Swal) window.Swal.fire({ icon:'error', title:'Server error', text:'Please check if the server is running properly.' });
        else alert('Server error: Please check if the server is running properly.');
        return;
      }
      const data = await resp.json();
      if (data && data.success){
        const go = function(){ window.location.href = '/orders'; };
        if (window.Swal){
          window.Swal.fire({ icon:'success', title:'Checkout successful!', text:'Please proceed to Your Orders to track your order.' }).then(go).catch(go);
        } else {
          alert('Checkout successful! Please proceed to Your Orders to track your order.');
          go();
        }
      } else {
        const msg = (data && data.msg) ? String(data.msg) : 'Checkout failed';
        if (window.Swal) window.Swal.fire({ icon:'error', title:'Checkout failed', text: msg });
        else alert('Error: ' + msg);
      }
    }catch(err){
      console.error('Checkout error', err);
      if (window.Swal) window.Swal.fire({ icon:'error', title:'Checkout error', text:'Please try again.' });
      else alert('An error occurred during checkout. Please try again.');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  document.addEventListener('DOMContentLoaded', async function(){
    const root = document.getElementById('checkoutRoot');
    if (!root) return;

    const mode = root.getAttribute('data-mode') || 'cart';
    const cartJson = root.getAttribute('data-cart-items') || '[]';
    const directJson = root.getAttribute('data-direct-item') || 'null';
    const cartItems = safeParseJSON(cartJson, []);
    const directItem = safeParseJSON(directJson, null);
    currentCheckoutMode = mode;
    currentDirectItem = directItem;
    currentCartItems = cartItems;

    renderOrderSummary(mode, cartItems, directItem);
    setupGeoDropdowns();

    let addresses = await loadBackendAddressIntoLocal();
    renderAddressList(addresses);
    if (addresses && addresses.length){
      applyAddressToForm(addresses[0]);
    }

    const addBtn = document.getElementById('addAddressBtn');
    if (addBtn){
      addBtn.addEventListener('click', async function(e){
        e.preventDefault();
        const addr = buildAddressFromForm();
        if (!validateAddress(addr)){
          const msg = 'Please complete the address form before saving.';
          if (window.Swal) window.Swal.fire({ icon:'warning', title:'Incomplete address', text: msg });
          else alert(msg);
          return;
        }
        let list = loadLocalAddresses();
        list.unshift(addr);
        saveLocalAddresses(list);
        renderAddressList(list);
        try{ await saveAddressToBackend(addr); }catch(e){}
      });
    }

    placeOrderBtn = document.getElementById('placeOrderBtn');
    if (placeOrderBtn){
      placeOrderBtn.addEventListener('click', function(e){ handlePlaceOrder(e, mode, directItem, cartItems); });
    }

    const homeInput = document.getElementById('homeAddress');
    const contactInput = document.getElementById('contactNumber');

    // Refresh place-order-button state AND shipping estimate when any dropdown changes.
    // setupGeoDropdowns() already wires shipping refresh + cascade loading, so we only
    // wire button-state here to avoid duplicate fetches.
    ['region','province','city','barangay'].forEach(function(id){
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', refreshPlaceOrderButtonState);
    });
    if (homeInput){ homeInput.addEventListener('input', refreshPlaceOrderButtonState); }
    if (contactInput){ contactInput.addEventListener('input', refreshPlaceOrderButtonState); }

    // Order total recomputes via renderOrderSummary inside refreshShippingEstimate,
    // but also listen on the event so any future external totalizers stay in sync.
    document.addEventListener('shipping:updated', function(){
      renderOrderSummary(currentCheckoutMode, currentCartItems, currentDirectItem);
    });

    refreshPlaceOrderButtonState();
    refreshShippingEstimate(mode, directItem, cartItems);
  });
})();
