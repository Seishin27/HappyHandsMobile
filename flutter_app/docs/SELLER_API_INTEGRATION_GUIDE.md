# Seller Dashboard Integration Guide

## Overview

This guide explains how to integrate the seller dashboard between the Flutter mobile app and Flask web backend, enabling bidirectional sync for products and orders.

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐         ┌─────────────┐
│  Flutter Mobile App │ ◄─────► │  Flask REST API      │ ◄─────► │   MySQL DB  │
│  (Seller Dashboard) │  JWT    │  (seller_api.py)     │         │  (products) │
└─────────────────────┘         └──────────────────────┘         └─────────────┘
```

## Part 1: Flask Backend Setup

### Step 1: Install the Seller API Module

1. Copy the seller API file:
   ```bash
   cp flutter_app/docs/flask_seller_api.py app/seller_api.py
   ```

2. Register the blueprint in `run.py`:
   ```python
   from app.seller_api import seller_api_bp
   
   # After creating the Flask app
   app.register_blueprint(seller_api_bp)
   ```

3. Restart the Flask server:
   ```bash
   python run.py
   ```

### Step 2: Verify Endpoints

Test that the endpoints are accessible:

```bash
# Test seller login
curl -X POST http://localhost:5500/api/seller/login \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@example.com","password":"password"}'

# Test products endpoint (with token from login)
curl -X GET http://localhost:5500/api/seller/products \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Part 2: Database Schema

### Required Tables

The seller API expects these tables to exist:

#### Products Table
```sql
CREATE TABLE IF NOT EXISTS products (
    productID INT AUTO_INCREMENT PRIMARY KEY,
    productname VARCHAR(255) NOT NULL,
    productdescription TEXT,
    productprice DECIMAL(10,2) NOT NULL,
    productcategory VARCHAR(100),
    productquantity INT DEFAULT 0,
    image_path TEXT,
    sellerID INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (sellerID) REFERENCES sellers(sellerID)
);
```

#### Seller Orders Table
```sql
CREATE TABLE IF NOT EXISTS seller_orders (
    seller_order_id INT AUTO_INCREMENT PRIMARY KEY,
    seller_id INT NOT NULL,
    order_number VARCHAR(50),
    customer_name VARCHAR(255),
    total_amount DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES sellers(sellerID)
);
```

#### Order Line Items Table (Optional)
```sql
CREATE TABLE IF NOT EXISTS order_line_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    seller_order_id INT NOT NULL,
    product_id INT,
    product_name VARCHAR(255),
    quantity INT,
    price DECIMAL(10,2),
    FOREIGN KEY (seller_order_id) REFERENCES seller_orders(seller_order_id)
);
```

## Part 3: API Endpoints Reference

### Authentication

All seller endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <JWT_TOKEN>
```

### Product Management

#### 1. List Products
```http
GET /api/seller/products?page=1&page_size=20
```

**Response:**
```json
{
  "success": true,
  "products": [
    {
      "id": 1,
      "name": "Product Name",
      "description": "Product description",
      "price": 99.99,
      "category": "Electronics",
      "stock_quantity": 10,
      "images": ["/uploads/image1.jpg"],
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 50,
    "total_pages": 3
  }
}
```

#### 2. Create Product
```http
POST /api/seller/products
Content-Type: application/json

{
  "name": "New Product",
  "description": "Product description",
  "price": 99.99,
  "category": "Electronics",
  "stock_quantity": 10,
  "images": []
}
```

**Response:**
```json
{
  "success": true,
  "message": "Product created successfully",
  "product": {
    "id": 123,
    "name": "New Product",
    ...
  }
}
```

#### 3. Update Product
```http
PUT /api/seller/products/123
Content-Type: application/json

{
  "name": "Updated Product Name",
  "price": 89.99,
  "stock_quantity": 15
}
```

#### 4. Delete Product
```http
DELETE /api/seller/products/123
```

**Response:**
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

#### 5. Upload Images
```http
POST /api/seller/products/upload-images
Content-Type: multipart/form-data

images: [file1.jpg, file2.jpg]
```

**Response:**
```json
{
  "success": true,
  "message": "2 image(s) uploaded successfully",
  "urls": [
    "/uploads/seller_1_20240101_120000_image1.jpg",
    "/uploads/seller_1_20240101_120001_image2.jpg"
  ]
}
```

### Order Management

#### 1. List Orders
```http
GET /api/seller/orders?page=1&page_size=20&status=pending
```

**Response:**
```json
{
  "success": true,
  "orders": [
    {
      "id": 1,
      "order_number": "ORD-001",
      "customer_name": "John Doe",
      "total_amount": 299.99,
      "status": "pending",
      "order_date": "2024-01-01T00:00:00",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### 2. Get Order Details
```http
GET /api/seller/orders/1
```

**Response:**
```json
{
  "success": true,
  "order": {
    "id": 1,
    "order_number": "ORD-001",
    "customer_name": "John Doe",
    "total_amount": 299.99,
    "status": "pending",
    "order_date": "2024-01-01T00:00:00",
    "line_items": [
      {
        "product_id": 123,
        "product_name": "Product A",
        "quantity": 2,
        "price": 99.99
      }
    ]
  }
}
```

#### 3. Update Order Status
```http
PUT /api/seller/orders/1/status
Content-Type: application/json

{
  "status": "processing"
}
```

**Valid Status Values:**
- `pending` - Order placed, awaiting processing
- `processing` - Order is being prepared
- `shipped` - Order has been shipped
- `delivered` - Order delivered to customer
- `cancelled` - Order cancelled

**Response:**
```json
{
  "success": true,
  "message": "Order status updated successfully",
  "order": {
    "id": 1,
    "status": "processing",
    ...
  }
}
```

## Part 4: Flutter App Configuration

The Flutter app is already configured and ready to use these endpoints. No changes needed!

### Verify Configuration

1. Check API base URL in `lib/core/config/app_config.dart`:
   ```dart
   static String get apiBaseUrl {
     // Should point to your Flask server
     return 'http://127.0.0.1:5500/api';
   }
   ```

2. Run the integration test:
   ```bash
   flutter test test/integration/seller_integration_test.dart
   ```

## Part 5: Testing the Integration

### Manual Testing Steps

1. **Start Flask Backend:**
   ```bash
   cd ..  # Go to Flask project root
   python run.py
   ```

2. **Start Flutter App:**
   ```bash
   cd flutter_app
   flutter run
   ```

3. **Test Seller Login:**
   - Open the Flutter app
   - Navigate to Seller Login
   - Login with seller credentials
   - You should be redirected to the seller dashboard

4. **Test Dashboard Stats:**
   - The dashboard should display:
     - Sales metrics (total, today, monthly, yearly)
     - Order metrics (total, pending, processing, completed)
     - Recent orders list

5. **Test Product Management:**
   - Navigate to Products tab
   - Click "+" to create a new product
   - Fill in product details
   - Save the product
   - Verify it appears in the list
   - Edit the product
   - Delete the product

6. **Test Order Management:**
   - Navigate to Orders tab
   - View list of orders
   - Filter by status
   - Click on an order to view details
   - Update order status
   - Verify status changes

### Automated Testing

Run the integration test suite:

```bash
# Make sure Flask backend is running first
cd flutter_app
flutter test test/integration/seller_integration_test.dart
```

Expected output:
```
✓ Seller can login and receive JWT token
✓ Seller can fetch sales statistics
✓ Seller can fetch order statistics
✓ Seller can fetch recent orders
✓ Seller can fetch their products
✓ Seller can create a new product
✓ Product created in Flutter appears in web (bidirectional sync)
✓ Flask backend is accessible
```

## Part 6: Bidirectional Sync Verification

### Web → Mobile Sync

1. Login to web dashboard as seller
2. Create a new product on the web
3. Open Flutter app
4. Navigate to Products tab
5. Pull to refresh
6. **Verify:** New product appears in the list

### Mobile → Web Sync

1. Open Flutter app as seller
2. Create a new product in the app
3. Open web dashboard
4. Refresh the products page
5. **Verify:** New product appears in the web list

## Troubleshooting

### Issue: 404 Not Found on /api/seller/products

**Solution:**
- Verify `seller_api.py` is in the `app/` directory
- Check that the blueprint is registered in `run.py`
- Restart the Flask server

### Issue: 401 Unauthorized

**Solution:**
- Verify seller is logged in
- Check JWT token is being sent in Authorization header
- Verify token hasn't expired
- Check seller ID is in JWT claims

### Issue: Empty Products List

**Solution:**
- Check if seller has products in database
- Verify `sellerID` in products table matches logged-in seller
- Check database connection

### Issue: CORS Errors

**Solution:**
Add CORS headers in Flask:
```python
from flask_cors import CORS
CORS(app)
```

## Security Considerations

1. **JWT Token Security:**
   - Tokens expire after a set time
   - Store tokens securely in Flutter (flutter_secure_storage)
   - Never log tokens in production

2. **Authorization:**
   - All endpoints verify seller owns the resource
   - Cannot access other sellers' products/orders

3. **Input Validation:**
   - All inputs are validated on the backend
   - SQL injection protection via parameterized queries
   - File upload validation (type, size)

4. **HTTPS:**
   - Use HTTPS in production
   - Never send credentials over HTTP

## Performance Optimization

1. **Pagination:**
   - All list endpoints support pagination
   - Default page size: 20 items
   - Maximum page size: 100 items

2. **Caching:**
   - Consider caching product lists in Flutter
   - Implement pull-to-refresh for manual updates

3. **Image Optimization:**
   - Compress images before upload
   - Use thumbnails for list views
   - Lazy load images

## Next Steps

1. ✅ Install Flask backend endpoints
2. ✅ Verify database schema
3. ✅ Test authentication flow
4. ✅ Test product CRUD operations
5. ✅ Test order management
6. ✅ Verify bidirectional sync
7. 🔄 Continue with remaining Flutter UI tasks (Chat, Notifications, Profile)

## Support

For issues or questions:
1. Check the integration test output
2. Review Flask server logs
3. Check Flutter app logs
4. Verify database schema matches requirements
