// Category page interactions: navbar, search, cart, price filter, dynamic products, and report login gating
(function(){
  const body = document.body || document.querySelector('body');
  if (!body) return;

  // Config from data attributes
  let initialProducts = [];
  try {
    const raw = body.dataset.categoryProducts || '[]';
    initialProducts = JSON.parse(raw);
  } catch (e) {
    console.warn('category_page: failed to parse initial products', e);
    initialProducts = [];
  }
  const isLoggedIn = body.dataset.categoryUserLoggedIn === 'true';
  const defaultImage = body.dataset.defaultImage || '/static/images/default.png';
  let activeSlug = body.dataset.currentCategorySlug || '';

  // Expose globals for compatibility if something else relies on them
  window.__initialCategoryProducts = initialProducts;
  window.__isCategoryUserLoggedIn = isLoggedIn;

  // Navbar, Cart, User Dropdown, and Logout logic are now handled by index.js
  // to prevent duplicate event listeners and conflicts.

  // Helper to escape HTML
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, function(c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] || c;
    });
  }

  const categoryPanel = document.getElementById('categoryProductsPanel');
  const productsGrid = document.getElementById('productsGrid');
  const productsContainer = document.getElementById('productsContainer');
  const pageTitle = document.getElementById('pageTitle');
  const pageSubtitle = document.getElementById('pageSubtitle');
  const popularList = document.getElementById('popularList');
  const paginationNav = categoryPanel ? categoryPanel.querySelector('[data-role="pagination"]') : null;
  const statusBanner = categoryPanel ? categoryPanel.querySelector('[data-role="status"]') : null;

  if (categoryPanel && categoryPanel.dataset.slug) {
    activeSlug = categoryPanel.dataset.slug;
  }

  let activePage = categoryPanel ? Number(categoryPanel.dataset.currentPage || 1) : 1;
  let totalPages = categoryPanel ? Number(categoryPanel.dataset.totalPages || 1) : 1;
  let pageSize = categoryPanel ? Number(categoryPanel.dataset.pageSize || 12) : 12;
  let totalItems = categoryPanel ? Number(categoryPanel.dataset.totalItems || initialProducts.length) : initialProducts.length;
  let isPaginating = false;
  let currentRequest = null;

  function normalizeProduct(p) {
    if (!p) return null;
    const id = p.id ?? p.productID ?? p.productId ?? p.product_id;
    if (id === undefined || id === null) return null;
    const priceValue = Number(p.price ?? p.Price ?? p.total_price ?? 0);
    const name = p.name ?? p.title ?? 'Product';
    const desc = p.short_description ?? p.description ?? '';
    const stockValue = Number(p.stock ?? p.Stock ?? 0);
    let rawImage = p.image_url || p.imageURL || p.image || p.image_path || p.main_image || p.image0;
    if (rawImage && typeof rawImage === 'string' && rawImage.includes(',')) {
        rawImage = rawImage.split(',')[0];
    }
    let imageUrl = defaultImage;
    if (rawImage) {
      if (/^https?:/i.test(rawImage)) imageUrl = rawImage;
      else if (rawImage.indexOf('/uploads/') === 0) imageUrl = rawImage;
      else if (rawImage.indexOf('/static/') === 0) imageUrl = rawImage;
      else imageUrl = '/uploads/' + rawImage;
    }
    return {
      id: id,
      name: name,
      short_description: desc,
      price: Number.isFinite(priceValue) ? priceValue : 0,
      stock: Number.isFinite(stockValue) ? stockValue : 0,
      image_url: imageUrl,
    };
  }

  function createPriceFilter(onChange) {
    const minInput = document.getElementById('priceMinInput');
    const maxInput = document.getElementById('priceMaxInput');
    const minRange = document.getElementById('priceRangeMin');
    const maxRange = document.getElementById('priceRangeMax');
    const sliderRange = document.getElementById('priceSliderRange');
    const panel = document.getElementById('priceFilterPanel');
    if (!minInput || !maxInput || !minRange || !maxRange) {
      return {
        setProducts: function(list) {
          const normalized = (list || []).map(normalizeProduct).filter(Boolean);
          onChange(normalized);
        },
      };
    }

    let products = [];
    let bounds = { min: 0, max: 0 };
    const MIN_GAP = 1;

    function determineStep(spread) {
      if (spread > 2000) return 100;
      if (spread > 500) return 50;
      if (spread > 200) return 10;
      if (spread > 50) return 5;
      return 1;
    }

    function clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    }

    function updateSliderRange() {
      if (!sliderRange) return;
      if (bounds.max === bounds.min) {
        sliderRange.style.left = '0%';
        sliderRange.style.right = '0%';
        return;
      }
      const minVal = Number(minRange.value) || bounds.min;
      const maxVal = Number(maxRange.value) || bounds.max;
      const minPercent = Math.max(0, Math.min(100, ((minVal - bounds.min) / (bounds.max - bounds.min)) * 100));
      const maxPercent = Math.max(0, Math.min(100, ((maxVal - bounds.min) / (bounds.max - bounds.min)) * 100));
      sliderRange.style.left = minPercent + '%';
      sliderRange.style.right = (100 - maxPercent) + '%';
    }

    function disableFilter() {
      [minInput, maxInput, minRange, maxRange].forEach(function(el) {
        el.value = 0;
        el.disabled = true;
      });
      if (panel) panel.classList.add('is-disabled');
      const doneBtn = document.getElementById('priceFilterDoneBtn');
      if (doneBtn) doneBtn.disabled = true;
    }

    function enableFilter() {
      [minInput, maxInput, minRange, maxRange].forEach(function(el) {
        el.disabled = false;
      });
      if (panel) panel.classList.remove('is-disabled');
      const doneBtn = document.getElementById('priceFilterDoneBtn');
      if (doneBtn) doneBtn.disabled = false;
    }

    function setProducts(list) {
      products = (list || []).map(normalizeProduct).filter(Boolean);
      if (!products.length) {
        disableFilter();
        onChange([]);
        return;
      }
      enableFilter();
      const prices = products.map(function(p) {
        return p.price;
      });
      const minVal = Math.floor(Math.min.apply(Math, prices));
      const maxVal = Math.ceil(Math.max.apply(Math, prices));
      bounds.min = Number.isFinite(minVal) ? minVal : 0;
      bounds.max = Number.isFinite(maxVal) && maxVal > bounds.min ? maxVal : bounds.min + 100;
      const step = determineStep(bounds.max - bounds.min);
      [minInput, maxInput, minRange, maxRange].forEach(function(el) {
        el.min = bounds.min;
        el.max = bounds.max;
        el.step = step;
      });
      // Set initial values to show all products
      minInput.value = bounds.min;
      maxInput.value = bounds.max;
      minRange.value = bounds.min;
      maxRange.value = bounds.max;
      updateSliderRange();
      // Initially show all products (no filter applied until user clicks Done)
      onChange(products);
    }

    function applyFilter() {
      if (!products.length) {
        onChange([]);
        return;
      }
      let minVal = Number(minInput.value);
      let maxVal = Number(maxInput.value);
      if (isNaN(minVal) || minVal < bounds.min) minVal = bounds.min;
      if (isNaN(maxVal) || maxVal > bounds.max) maxVal = bounds.max;
      if (minVal > maxVal) {
        const temp = minVal;
        minVal = maxVal;
        maxVal = temp;
      }
      minVal = clamp(minVal, bounds.min, bounds.max);
      maxVal = clamp(maxVal, bounds.min, bounds.max);
      minInput.value = minVal;
      maxInput.value = maxVal;
      minRange.value = minVal;
      maxRange.value = maxVal;
      updateSliderRange();
      const filtered = products.filter(function(p) {
        const price = Number(p.price) || 0;
        return price >= minVal && price <= maxVal;
      });
      onChange(filtered);
    }

    minRange.addEventListener('input', function() {
      if (Number(maxRange.value) - Number(minRange.value) < MIN_GAP) {
        minRange.value = Number(maxRange.value) - MIN_GAP;
      }
      minInput.value = minRange.value;
      updateSliderRange();
    });

    maxRange.addEventListener('input', function() {
      if (Number(maxRange.value) - Number(minRange.value) < MIN_GAP) {
        maxRange.value = Number(minRange.value) + MIN_GAP;
      }
      maxInput.value = maxRange.value;
      updateSliderRange();
    });

    minInput.addEventListener('input', function() {
      let val = Number(minInput.value);
      if (isNaN(val)) val = bounds.min;
      val = clamp(val, bounds.min, Number(maxRange.value) - MIN_GAP);
      minInput.value = val;
      minRange.value = val;
      updateSliderRange();
    });

    maxInput.addEventListener('input', function() {
      let val = Number(maxInput.value);
      if (isNaN(val)) val = bounds.max;
      val = clamp(val, Number(minRange.value) + MIN_GAP, bounds.max);
      maxInput.value = val;
      maxRange.value = val;
      updateSliderRange();
    });

    minInput.addEventListener('change', function() {
      let val = Number(minInput.value);
      if (isNaN(val)) val = bounds.min;
      val = clamp(val, bounds.min, Number(maxRange.value) - MIN_GAP);
      minInput.value = val;
      minRange.value = val;
      updateSliderRange();
    });

    maxInput.addEventListener('change', function() {
      let val = Number(maxInput.value);
      if (isNaN(val)) val = bounds.max;
      val = clamp(val, Number(minRange.value) + MIN_GAP, bounds.max);
      maxInput.value = val;
      maxRange.value = val;
      updateSliderRange();
    });

    const doneBtn = document.getElementById('priceFilterDoneBtn');
    if (doneBtn) {
      doneBtn.addEventListener('click', function() {
        applyFilter();
      });
    }

    return { setProducts: setProducts };
  }

  function renderProducts(items) {
    const container = productsContainer || productsGrid;
    if (!container) {
      console.warn('Price filter: No product container found');
      return;
    }

    if (!items || !items.length) {
      if (productsGrid) {
        productsGrid.innerHTML = '<div class="panel" style="grid-column:1/-1;padding:1rem;"><p class="muted">No products found within this price range.</p></div>';
      } else if (productsContainer) {
        productsContainer.innerHTML = '<div class="panel"><p class="muted">No products found within this price range.</p></div>';
      }
      return;
    }

    if (productsGrid) {
      // Grid layout - render as product cards
      productsGrid.innerHTML = items.map(function(p) {
        const productId = p.id || p.productID || p.productId || p.product_id;
        const imageUrl = p.image_url || defaultImage;
        const name = escapeHtml(p.name || p.title || 'Product');
        const price = Number(p.price || 0).toFixed(2);
        const stock = Number(p.stock || 0);
        const addToCartBtn = '<div style="width:100%;margin-top:.5rem;padding:.5rem;text-align:center;color:#64748b;font-size:0.9rem;font-weight:500;">Stock: ' + stock + '</div>';

        return (
          '<article class="product-card" style="background:#fff;border-radius:10px;padding:.8rem;border:1px solid rgba(15,23,42,0.04);" data-product-id="' + productId + '">' +
          '  <a href="/product/' + productId + '">' +
          '    <div style="height:160px;display:flex;align-items:center;justify-content:center;overflow:hidden;border-radius:8px;margin-bottom:.6rem;">' +
          '      <img src="' + imageUrl + '" alt="' + name + '" style="max-width:100%;max-height:100%;object-fit:cover;">' +
          '    </div>' +
          '    <h3 style="margin:.25rem 0;font-size:1rem">' + name + '</h3>' +
          '    <div style="color:var(--brand);font-weight:700">₱' + price + '</div>' +
          '  </a>' +
          addToCartBtn +
          '</article>'
        );
      }).join('');
    } else if (productsContainer) {
      // List layout - render as product rows
      productsContainer.innerHTML = items.map(function(p) {
        const productId = p.id || p.productID || p.productId || p.product_id;
        const imageUrl = p.image_url || defaultImage;
        const name = escapeHtml(p.name || p.title || 'Product');
        const price = Number(p.price || 0).toFixed(2);
        const stock = Number(p.stock || 0);
        const addToCartBtn = '<div style="padding:.5rem;text-align:center;color:#64748b;font-size:0.9rem;font-weight:500;">Stock: ' + stock + '</div>';
        const shortDesc = escapeHtml(p.short_description || p.description || '');

        return (
          '<article class="product-row" data-id="' + productId + '">' +
          '  <div class="product-thumb"><img src="' + imageUrl + '" alt="' + name + '"></div>' +
          '  <div class="product-info">' +
          '    <h3 class="product-title">' + name + '</h3>' +
          '    <p class="product-desc muted">' + shortDesc + '</p>' +
          '    <div class="product-actions">' +
          '      <div class="price">₱' + price + '</div>' +
          '      <div style="display:flex;gap:.5rem">' +
          '        ' + addToCartBtn +
          '        <a class="continue-shopping-btn" href="/product/' + productId + '">View</a>' +
          '      </div>' +
          '    </div>' +
          '  </div>' +
          '</article>'
        );
      }).join('');
    }
  }

  function updateStatus(message, isError) {
    if (!statusBanner) return;
    if (!message) {
      statusBanner.textContent = '';
      statusBanner.hidden = true;
      statusBanner.classList.remove('error');
      return;
    }
    statusBanner.textContent = message;
    statusBanner.hidden = false;
    statusBanner.classList.toggle('error', Boolean(isError));
  }

  function getBaseCategoryUrl() {
    if (!categoryPanel) {
      return window.location.pathname || '/';
    }
    if (categoryPanel.dataset.baseUrl) {
      return categoryPanel.dataset.baseUrl;
    }
    if (activeSlug) {
      return '/category/' + encodeURIComponent(activeSlug);
    }
    return window.location.pathname || '/';
  }

  function buildCategoryHref(page) {
    const base = getBaseCategoryUrl();
    try {
      const url = new URL(base, window.location.origin);
      if (activeSlug) {
        url.pathname = '/category/' + encodeURIComponent(activeSlug);
      }
      url.searchParams.set('page', page);
      url.searchParams.set('per_page', pageSize);
      url.hash = 'productsGrid';
      return url.pathname + url.search + url.hash;
    } catch (err) {
      const hasQuery = base.indexOf('?') !== -1;
      const queryPrefix = hasQuery ? '&' : '?';
      return base + queryPrefix + 'page=' + encodeURIComponent(page) + '&per_page=' + encodeURIComponent(pageSize) + '#productsGrid';
    }
  }

  function rebuildCategoryPageNumbers(total, current) {
    const numbers = [];
    for (let page = 1; page <= total; page += 1) {
      if (page === current) {
        numbers.push('<span class="page-number active" data-page="' + page + '" aria-current="page">' + page + '</span>');
      } else {
        numbers.push('<a class="page-number" data-page="' + page + '" href="' + buildCategoryHref(page) + '">' + page + '</a>');
      }
    }
    return numbers.join('');
  }

  function refreshPaginationControls(meta) {
    if (!paginationNav) return;
    const total = Number((meta && (meta.total_pages ?? meta.totalPages)) || totalPages || 1);
    const current = Number((meta && (meta.page ?? meta.current_page)) || activePage || 1);
    paginationNav.hidden = total <= 1;
    if (total <= 1) {
      return;
    }
    const prevBtn = paginationNav.querySelector('[data-role="prev"]');
    const nextBtn = paginationNav.querySelector('[data-role="next"]');
    const numbersContainer = paginationNav.querySelector('.page-numbers');
    const prevTarget = Math.max(1, current - 1);
    const nextTarget = Math.min(total, current + 1);

    if (prevBtn) {
      prevBtn.dataset.page = String(prevTarget);
      prevBtn.href = buildCategoryHref(prevTarget);
      if (current <= 1) {
        prevBtn.classList.add('disabled');
        prevBtn.setAttribute('aria-disabled', 'true');
      } else {
        prevBtn.classList.remove('disabled');
        prevBtn.removeAttribute('aria-disabled');
      }
    }

    if (nextBtn) {
      nextBtn.dataset.page = String(nextTarget);
      nextBtn.href = buildCategoryHref(nextTarget);
      if (current >= total) {
        nextBtn.classList.add('disabled');
        nextBtn.setAttribute('aria-disabled', 'true');
      } else {
        nextBtn.classList.remove('disabled');
        nextBtn.removeAttribute('aria-disabled');
      }
    }

    if (numbersContainer) {
      numbersContainer.innerHTML = rebuildCategoryPageNumbers(total, current);
    }
  }

  function setActiveCategoryLink(slug) {
    const items = document.querySelectorAll('.side-categories li');
    items.forEach(function(li) {
      li.classList.remove('active');
    });
    if (!slug) return;
    const normalized = slug.toLowerCase();
    const candidates = document.querySelectorAll('.side-categories a[data-slug]');
    let activeLink = null;
    candidates.forEach(function(link) {
      const value = (link.dataset.slug || '').toLowerCase();
      if (value === normalized && !activeLink) {
        activeLink = link;
      }
    });
    if (activeLink) {
      const parent = activeLink.closest('li');
      if (parent) parent.classList.add('active');
    }
  }

  function applyCategoryPayload(data, options) {
    const payload = data && data.data && typeof data.data === 'object' ? data.data : data;
    const paginationMeta = payload && payload.pagination ? payload.pagination : {};
    const products = Array.isArray(payload && payload.products) ? payload.products : [];
    const resolvedCategory = (payload && (payload.category || payload.current_category)) || null;
    const resolvedSlug = options && options.slug ? options.slug : (resolvedCategory && resolvedCategory.slug) || activeSlug;
    const resolvedPage = Number(paginationMeta.page || (options && options.page) || 1);
    const resolvedPerPage = Number(paginationMeta.per_page || paginationMeta.perPage || (options && options.perPage) || pageSize || 12);
    const resolvedTotalPages = Number(paginationMeta.total_pages || paginationMeta.totalPages || 1);
    const resolvedTotalItems = Number(paginationMeta.total_products || paginationMeta.totalProducts || products.length);

    activeSlug = resolvedSlug || '';
    activePage = resolvedPage;
    pageSize = resolvedPerPage;
    totalPages = resolvedTotalPages;
    totalItems = resolvedTotalItems;

    if (categoryPanel) {
      categoryPanel.dataset.slug = activeSlug;
      categoryPanel.dataset.currentPage = String(activePage);
      categoryPanel.dataset.pageSize = String(pageSize);
      categoryPanel.dataset.totalPages = String(totalPages);
      categoryPanel.dataset.totalItems = String(totalItems);
      if (activeSlug) {
        categoryPanel.dataset.endpoint = '/api/categories/' + encodeURIComponent(activeSlug);
        categoryPanel.dataset.baseUrl = '/category/' + activeSlug;
      }
    }

    if (pageTitle && resolvedCategory) {
      pageTitle.textContent = resolvedCategory.name || 'Category';
    }
    if (pageSubtitle) {
      if (resolvedCategory && resolvedCategory.description) {
        pageSubtitle.textContent = resolvedCategory.description;
      } else if (resolvedCategory && resolvedCategory.name) {
        pageSubtitle.textContent = 'Category: ' + resolvedCategory.name;
      }
    }

    initialProducts = products.slice();
    window.__initialCategoryProducts = initialProducts;
    priceFilter.setProducts(initialProducts);
    if (payload && payload.popular) {
      updatePopular(payload.popular);
    }
    setActiveCategoryLink(activeSlug);
    refreshPaginationControls({ page: activePage, total_pages: totalPages });
    updateStatus('');

    const shouldUpdateHistory = !options || options.updateHistory !== false;
    if (shouldUpdateHistory && window.history && typeof window.history.replaceState === 'function') {
      try {
        const nextUrl = new URL(window.location.href);
        if (activeSlug) {
          nextUrl.pathname = '/category/' + encodeURIComponent(activeSlug);
        }
        nextUrl.searchParams.set('page', activePage);
        nextUrl.searchParams.set('per_page', pageSize);
        nextUrl.hash = activeSlug ? encodeURIComponent(activeSlug) : 'productsGrid';
        window.history.replaceState({}, '', nextUrl.toString());
      } catch (err) {
        /* no-op */
      }
    }

    const shouldScroll = !options || options.scrollIntoView !== false;
    if (shouldScroll) {
      const grid = document.getElementById('productsGrid');
      if (grid && typeof grid.scrollIntoView === 'function') {
        grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  async function fetchCategoryData(options) {
    if (isPaginating && (!options || !options.allowConcurrency)) {
      return;
    }
    const slug = (options && options.slug) || activeSlug || (categoryPanel && categoryPanel.dataset.slug);
    if (!slug) {
      return;
    }
    const page = Number((options && options.page) || 1);
    const perPage = Number((options && options.perPage) || pageSize || 12);
    const usingSameSlug = categoryPanel && slug === categoryPanel.dataset.slug;
    const endpoint = usingSameSlug && categoryPanel && categoryPanel.dataset.endpoint
      ? categoryPanel.dataset.endpoint
      : '/api/categories/' + encodeURIComponent(slug);
    let url;
    try {
      url = new URL(endpoint, window.location.origin);
    } catch (err) {
      url = new URL('/api/categories/' + encodeURIComponent(slug), window.location.origin);
    }
    url.searchParams.set('page', page);
    url.searchParams.set('per_page', perPage);

    if (currentRequest) {
      currentRequest.abort();
    }
    currentRequest = new AbortController();
    isPaginating = true;
    updateStatus('Loading products…');
    if (categoryPanel) {
      categoryPanel.classList.add('is-loading');
    }

    try {
      const resp = await fetch(url.toString(), {
        signal: currentRequest.signal,
        credentials: 'same-origin',
      });
      if (!resp.ok) throw new Error('category_request_failed');
      const payload = await resp.json();
      applyCategoryPayload(payload, {
        slug: slug,
        page: page,
        perPage: perPage,
        updateHistory: options && options.updateHistory,
        scrollIntoView: options && options.scrollIntoView,
      });
    } catch (err) {
      if (err.name === 'AbortError') return;
      console.error('Category pagination failed', err);
      updateStatus('Unable to load products right now. Please try again.', true);
    } finally {
      isPaginating = false;
      if (categoryPanel) {
        categoryPanel.classList.remove('is-loading');
      }
    }
  }

  function updatePopular(popular) {
    if (!popularList || !Array.isArray(popular)) return;
    if (!popular.length) {
      popularList.innerHTML = '<li class="muted" style="padding:8px 0;">No popular products</li>';
      return;
    }
    popularList.innerHTML = popular.map(function(pp) {
      return (
        '<li>' +
        '  <img src="' + (pp.image_url || defaultImage) + '" alt="' + escapeHtml(pp.name) + '">' +
        '  <div>' +
        '    <div style="font-weight:700">' + escapeHtml(pp.name) + '</div>' +
        '    <div class="muted">₱' + Number(pp.price || 0).toFixed(2) + '</div>' +
        '  </div>' +
        '</li>'
      );
    }).join('');
  }

  const priceFilter = createPriceFilter(renderProducts);
  priceFilter.setProducts(initialProducts);
  refreshPaginationControls({ page: activePage, total_pages: totalPages });
  setActiveCategoryLink(activeSlug);

  // Search functionality using priceFilter
  if (searchBar) {
    let searchTimeout;
    
    // Helper to perform search
    async function performSearch(query) {
      if (!query) {
        // Show all products if search is empty
        priceFilter.setProducts(initialProducts);
        if (pageTitle) pageTitle.textContent = activeSlug ? (document.querySelector('.side-categories .active a')?.textContent || 'Category') : 'All Products';
        return;
      }

      // 1. Check if query matches a category name locally
      const catLink = document.querySelector(`.side-categories a[data-slug="${query.toLowerCase().replace(/\s+/g, '-')}"]`);
      if (catLink) {
        catLink.click();
        return;
      }

      // 2. Fetch search results from server
      try {
        const res = await fetch('/api/products/search?q=' + encodeURIComponent(query));
        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();
        
        if (data.success && Array.isArray(data.products)) {
          priceFilter.setProducts(data.products);
          if (pageTitle) pageTitle.textContent = `Search Results: "${query}"`;
        } else {
          priceFilter.setProducts([]);
          if (pageTitle) pageTitle.textContent = `No results for "${query}"`;
        }
      } catch (e) {
        console.error('Search error:', e);
        // Fallback to local filtering if API fails
        const filtered = initialProducts.filter(function(p) {
          const name = (p.name || p.title || '').toLowerCase();
          return name.indexOf(query) !== -1;
        });
        priceFilter.setProducts(filtered);
      }
    }

    searchBar.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      const query = (searchBar.value || '').trim().toLowerCase();

      searchTimeout = setTimeout(function() {
        performSearch(query);
      }, 500); // Debounce search by 500ms
    });

    // Handle Enter key to trigger search
    searchBar.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const query = (searchBar.value || '').trim().toLowerCase();
        performSearch(query);
      }
    });
  }

  function loadCategory(slug, shouldUpdateHistory) {
    if (!slug) return;
    fetchCategoryData({
      slug: slug,
      page: 1,
      perPage: pageSize,
      updateHistory: shouldUpdateHistory !== false,
    });
  }

  // Bind category links for AJAX category loading (if present)
  const catLinks = Array.from(document.querySelectorAll('.cat-link[data-slug]'));
  catLinks.forEach(function(a) {
    a.addEventListener('click', function(e) {
      e.preventDefault();
      const slug = a.getAttribute('data-slug');
      loadCategory(slug, true);
    });
  });

  if (categoryPanel && paginationNav) {
    categoryPanel.addEventListener('click', function(evt) {
      const link = evt.target.closest('.category-pagination a');
      if (!link) return;
      const targetPage = Number(link.dataset.page || link.getAttribute('data-page'));
      if (!targetPage) {
        evt.preventDefault();
        return;
      }
      if (link.classList.contains('disabled') || targetPage === activePage) {
        evt.preventDefault();
        return;
      }
      evt.preventDefault();
      fetchCategoryData({
        slug: activeSlug,
        page: targetPage,
        perPage: pageSize,
      });
    });
  }

  const hashSlug = location.hash ? decodeURIComponent(location.hash.slice(1)) : '';
  if (hashSlug && hashSlug !== 'productsGrid' && hashSlug !== activeSlug) {
    loadCategory(hashSlug, false);
  }

  // Delegated handlers for add-to-cart
  document.addEventListener('click', function(e) {
    // Example add-to-cart handler (for dynamically rendered buttons)
    if (e.target.matches('.add-to-cart')) {
      const id = e.target.dataset.id;
      if (!id) return;
      fetch('/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: id, qty: 1 }),
      })
        .then(function() {
          const el = document.getElementById('cartCount');
          if (el) el.textContent = String(Number(el.textContent || 0) + 1);
          window.location.href = '/cart';
        })
        .catch(function(err) {
          console.error(err);
        });
      return;
    }

  });
})();
