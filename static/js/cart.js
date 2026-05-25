// Cart functionality for BabyBloom - Backend Integration
class Cart {
    constructor() {
        this.updateCartCount();
        this.bindEvents();
    }

    // Update cart count in header
    updateCartCount() {
        // This will be updated by the backend when cart changes
        const cartCount = document.querySelector('.cart-count');
        if (cartCount) {
            // For now, we'll fetch the count from the server
            this.fetchCartCount();
        }
    }

    // Fetch cart count from server
    async fetchCartCount() {
        try {
            const response = await fetch('/cart/count');
            if (response.ok) {
                const data = await response.json();
                const cartCount = document.querySelector('.cart-count');
                if (cartCount) {
                    cartCount.textContent = data.count || 0;
                }
            }
        } catch (error) {
            console.error('Error fetching cart count:', error);
        }
    }

    // Add item to cart via backend
    async addItem(productId, quantity = 1, productName = 'Item') {
        console.log('Adding item to cart:', productId, 'quantity:', quantity);
        try{
            const q = parseInt(quantity, 10);
            if (Number.isNaN(q) || q < 1){
                this.showError('Quantity must be at least 1');
                console.warn('Rejected add to cart due to invalid quantity', { productId, quantity });
                return;
            }
        }catch(e){ /* ignore */ }
        try {
            const formData = new FormData();
            formData.append('quantity', quantity);
            
            const response = await fetch(`/add_to_cart/${productId}`, {
                method: 'POST',
                body: formData
            });

            console.log('Add to cart response:', response.status);

            if (response.ok) {
                // Update cart count and show success message instead of redirecting
                this.updateCartCount();
                this.showAddToCartMessage(productName);
            } else if (response.status === 302 || response.redirected) {
                // If redirected to login page, follow the redirect
                window.location.href = response.url;
            } else {
                console.error('Failed to add item to cart');
                alert('Failed to add item to cart. Please try again.');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            alert('Error adding to cart. Please try again.');
        }
    }

    // Show add to cart success message
    showAddToCartMessage(productName) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #2c5aa0;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(44, 90, 160, 0.3);
            z-index: 1000;
            font-weight: 600;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = `${productName} added to cart!`;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    // Bind event listeners
    bindEvents() {
        // Cart button click - redirect to cart page
        const cartBtn = document.getElementById('cartBtn');
        if (cartBtn) {
            cartBtn.addEventListener('click', () => {
                window.location.href = '/cart';
            });
        }

        // Add to cart buttons and per-item checkout buttons
        document.addEventListener('click', (e) => {
            const addBtn = e.target.closest('.add-to-cart-btn');
            if (addBtn) {
                console.log('Add to cart button clicked');
                e.preventDefault();
                const productContainer = addBtn.closest('[data-product-id]');
                console.log('Product container:', productContainer);
                const productId = this.extractProductId(productContainer);
                console.log('Extracted product ID:', productId);
                if (productId) {
                    let qty = 1;
                    try{
                        const qEl = productContainer ? (productContainer.querySelector('input[name="quantity"], .quantity-input') || null) : null;
                        if (qEl){ qty = parseInt(qEl.value||'1',10) || 1; }
                        if (Number.isNaN(qty) || qty < 1){
                            this.showError('Quantity must be at least 1');
                            console.warn('Blocked add to cart: invalid qty', { productId, qty });
                            if (qEl){ qEl.classList.add('qty-invalid'); qEl.setAttribute('aria-invalid','true'); }
                            return;
                        }
                    }catch(e){ }
                    
                    // Try to get product name for the success message
                    let productName = 'Item';
                    try {
                        // Check for data-product-name attribute first (product detail page)
                        if (productContainer.dataset.productName) {
                            productName = productContainer.dataset.productName;
                        } else {
                            // Fallback to finding h3 or .product-title
                            const titleEl = productContainer.querySelector('h3') || productContainer.querySelector('.product-title');
                            if (titleEl) productName = titleEl.textContent.trim();
                        }
                    } catch(e) {}

                    this.addItem(productId, qty, productName);
                } else {
                    console.error('Could not extract product ID');
                }
                return;
            }

            const checkoutBtn = e.target.closest('.btn-checkout');
            if (checkoutBtn) {
                e.preventDefault();
                const row = checkoutBtn.closest('.cart-item');
                const pidAttr = checkoutBtn.getAttribute('data-product-id') || (row ? row.getAttribute('data-product-id') : null);
                const productId = pidAttr ? parseInt(pidAttr, 10) : null;
                if (!row || !productId) {
                    console.error('Missing cart row or product id for checkout');
                    return;
                }
                const qtyInput = row.querySelector('.quantity-input');
                const stockRaw = row.dataset.stock;
                const stock = stockRaw !== undefined ? parseInt(stockRaw, 10) || 0 : 0;
                let qty = 1;
                try{
                    qty = qtyInput ? (parseInt(qtyInput.value || '1', 10) || 1) : 1;
                }catch(_){ qty = 1; }

                if (!qtyInput || Number.isNaN(qty) || qty < 1) {
                    const msg = 'Quantity must be at least 1 before checkout.';
                    if (window.Swal) { window.Swal.fire({ icon: 'warning', title: 'Invalid quantity', text: msg }); }
                    else if (window.confirmAction) { window.confirmAction({ title: 'Invalid quantity', text: msg, icon: 'warning', confirmButtonText: 'OK', showCancelButton: false }); }
                    else { alert(msg); }
                    return;
                }

                if (stock <= 0) {
                    const msg = 'This item is out of stock and cannot be checked out.';
                    if (window.Swal) { window.Swal.fire({ icon: 'info', title: 'Out of stock', text: msg }); }
                    else if (window.confirmAction) { window.confirmAction({ title: 'Out of stock', text: msg, icon: 'info', confirmButtonText: 'OK', showCancelButton: false }); }
                    else { alert(msg); }
                    return;
                }

                if (stock > 0 && qty > stock) {
                    const msg = `Requested quantity exceeds available stock (${stock}).`;
                    if (window.Swal) { window.Swal.fire({ icon: 'warning', title: 'Insufficient stock', text: msg }); }
                    else if (window.confirmAction) { window.confirmAction({ title: 'Insufficient stock', text: msg, icon: 'warning', confirmButtonText: 'OK', showCancelButton: false }); }
                    else { alert(msg); }
                    return;
                }

                const url = `/checkout?product_id=${encodeURIComponent(productId)}&qty=${encodeURIComponent(qty)}`;
                window.location.href = url;
            }
        });

        const qtyInputs = Array.from(document.querySelectorAll('.quantity-input'));
        qtyInputs.forEach(input => {
            input.addEventListener('input', ()=>{
                const v = parseInt(input.value||'0',10);
                const invalid = Number.isNaN(v) || v < 1;
                if (invalid){ input.classList.add('qty-invalid'); input.setAttribute('aria-invalid','true'); }
                else { input.classList.remove('qty-invalid'); input.removeAttribute('aria-invalid'); }
                const btn = input.closest('[data-product-id]')?.querySelector('.add-to-cart-btn');
                if (btn) btn.disabled = invalid;
            });
        });
    }


    // Extract product ID from product card
    extractProductId(productCard) {
        if (!productCard) return null;
        // Try to get product ID from data attribute first
        const productId = productCard.getAttribute('data-product-id');
        if (productId) {
            return parseInt(productId);
        }

        // Try to extract from product link
        const productLink = productCard.querySelector('a[href*="/product/"]');
        if (productLink) {
            const href = productLink.getAttribute('href');
            const match = href.match(/\/product\/(\d+)/);
            if (match) {
                return parseInt(match[1]);
            }
        }

        // Try to extract from product name and price (fallback)
        const nameElement = productCard.querySelector('h3');
        const priceElement = productCard.querySelector('.product-price');
        
        if (nameElement && priceElement) {
            const name = nameElement.textContent.trim();
            const priceText = priceElement.textContent.trim();
            const price = parseFloat(priceText.replace('₱', '').replace(',', '')) || 0;
            
            // Generate a unique ID based on name and price (this is a fallback)
            const id = btoa(name + price).replace(/[^a-zA-Z0-9]/g, '').substring(0, 10);
            return id;
        }

        return null;
    }

    showError(msg){
        try{
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ef4444;
                color: #fff;
                padding: 10px 14px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                font-weight: 600;
            `;
            notification.textContent = msg;
            document.body.appendChild(notification);
            setTimeout(()=>{ try{ notification.remove(); }catch(e){} }, 2000);
        }catch(e){ alert(msg); }
    }
}

// Initialize cart when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cart = new Cart();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);



