# Seller API Specification

## Version: 1.0.0
## Base URL: `/api/seller`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Product Management](#product-management)
3. [Order Management](#order-management)
4. [Error Handling](#error-handling)
5. [Data Models](#data-models)

---

## Authentication

All endpoints require JWT authentication via the `Authorization` header:

```
Authorization: Bearer <JWT_TOKEN>
```

### Obtaining a Token

Use the seller login endpoint:

```http
POST /api/seller/login
Content-Type: application/json

{
  "email": "seller@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

---

## Product Management

### 1. List Products

Retrieve a paginated list of the authenticated seller's products.

**Endpoint:** `GET /api/seller/products`

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (min: 1) |
| page_size | integer | No | 20 | Items per page (min: 1, max: 100) |

**Request Example:**
```http
GET /api/seller/products?page=1&page_size=20
Authorization: Bearer <JWT_TOKEN>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "products": [
    {
      "id": 1,
      "name": "Wireless Headphones",
      "description": "High-quality wireless headphones with noise cancellation",
      "price": 99.99,
      "category": "Electronics",
      "stock_quantity": 50,
      "images": [
        "/uploads/headphones_1.jpg",
        "/uploads/headphones_2.jpg"
      ],
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-20T14:45:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or missing JWT token
- `500 Internal Server Error` - Database or server error

---

### 2. Create Product

Create a new product for the authenticated seller.

**Endpoint:** `POST /api/seller/products`

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| name | string | Yes | Max 255 chars | Product name |
| description | string | No | - | Product description |
| price | number | Yes | >= 0 | Product price |
| category | string | No | Max 100 chars | Product category |
| stock_quantity | integer | No | >= 0, default: 0 | Available stock |
| images | array[string] | No | - | Array of image URLs |

**Request Example:**
```http
POST /api/seller/products
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "name": "Wireless Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "price": 99.99,
  "category": "Electronics",
  "stock_quantity": 50,
  "images": [
    "/uploads/headphones_1.jpg",
    "/uploads/headphones_2.jpg"
  ]
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "Product created successfully",
  "product": {
    "id": 123,
    "name": "Wireless Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 99.99,
    "category": "Electronics",
    "stock_quantity": 50,
    "images": [
      "/uploads/headphones_1.jpg",
      "/uploads/headphones_2.jpg"
    ],
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation error
  ```json
  {
    "success": false,
    "message": "Validation error: Product name is required",
    "errors": {
      "name": "Required"
    }
  }
  ```
- `401 Unauthorized` - Invalid or missing JWT token
- `500 Internal Server Error` - Database or server error

---

### 3. Update Product

Update an existing product owned by the authenticated seller.

**Endpoint:** `PUT /api/seller/products/{product_id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | integer | Yes | Product ID to update |

**Request Body:** (All fields optional, only include fields to update)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | string | Max 255 chars | Product name |
| description | string | - | Product description |
| price | number | >= 0 | Product price |
| category | string | Max 100 chars | Product category |
| stock_quantity | integer | >= 0 | Available stock |
| images | array[string] | - | Array of image URLs (replaces existing) |

**Request Example:**
```http
PUT /api/seller/products/123
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "price": 89.99,
  "stock_quantity": 75
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Product updated successfully",
  "product": {
    "id": 123,
    "name": "Wireless Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 89.99,
    "category": "Electronics",
    "stock_quantity": 75,
    "images": [
      "/uploads/headphones_1.jpg",
      "/uploads/headphones_2.jpg"
    ],
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-20T14:45:00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation error or no fields to update
- `401 Unauthorized` - Invalid or missing JWT token
- `403 Forbidden` - Product doesn't belong to authenticated seller
- `404 Not Found` - Product doesn't exist
- `500 Internal Server Error` - Database or server error

---

### 4. Delete Product

Delete a product owned by the authenticated seller.

**Endpoint:** `DELETE /api/seller/products/{product_id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| product_id | integer | Yes | Product ID to delete |

**Request Example:**
```http
DELETE /api/seller/products/123
Authorization: Bearer <JWT_TOKEN>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or missing JWT token
- `403 Forbidden` - Product doesn't belong to authenticated seller
- `404 Not Found` - Product doesn't exist
- `500 Internal Server Error` - Database or server error

---

### 5. Upload Product Images

Upload one or more product images.

**Endpoint:** `POST /api/seller/products/upload-images`

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| images | file[] | Yes | One or more image files |

**Supported Formats:** PNG, JPG, JPEG, GIF, WEBP

**Max File Size:** 10MB per file

**Request Example:**
```http
POST /api/seller/products/upload-images
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data

images: [file1.jpg, file2.jpg]
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "2 image(s) uploaded successfully",
  "urls": [
    "/uploads/seller_1_20240115_103000_file1.jpg",
    "/uploads/seller_1_20240115_103001_file2.jpg"
  ]
}
```

**Error Responses:**
- `400 Bad Request` - No images provided or invalid format
- `401 Unauthorized` - Invalid or missing JWT token
- `500 Internal Server Error` - Upload or server error

---

## Order Management

### 1. List Orders

Retrieve a paginated list of the authenticated seller's orders.

**Endpoint:** `GET /api/seller/orders`

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (min: 1) |
| page_size | integer | No | 20 | Items per page (min: 1, max: 100) |
| status | string | No | - | Filter by status |

**Valid Status Values:**
- `pending` - Order placed, awaiting processing
- `processing` - Order is being prepared
- `shipped` - Order has been shipped
- `delivered` - Order delivered to customer
- `cancelled` - Order cancelled

**Request Example:**
```http
GET /api/seller/orders?page=1&page_size=20&status=pending
Authorization: Bearer <JWT_TOKEN>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "orders": [
    {
      "id": 1,
      "order_number": "ORD-2024-001",
      "customer_name": "John Doe",
      "total_amount": 299.99,
      "status": "pending",
      "order_date": "2024-01-15T10:30:00",
      "created_at": "2024-01-15T10:30:00",
      "updated_at": "2024-01-15T10:30:00"
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

**Error Responses:**
- `401 Unauthorized` - Invalid or missing JWT token
- `500 Internal Server Error` - Database or server error

---

### 2. Get Order Details

Retrieve detailed information for a specific order.

**Endpoint:** `GET /api/seller/orders/{order_id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | integer | Yes | Order ID |

**Request Example:**
```http
GET /api/seller/orders/1
Authorization: Bearer <JWT_TOKEN>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "order": {
    "id": 1,
    "order_number": "ORD-2024-001",
    "customer_name": "John Doe",
    "total_amount": 299.99,
    "status": "pending",
    "order_date": "2024-01-15T10:30:00",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00",
    "line_items": [
      {
        "product_id": 123,
        "product_name": "Wireless Headphones",
        "quantity": 2,
        "price": 99.99
      },
      {
        "product_id": 456,
        "product_name": "Phone Case",
        "quantity": 1,
        "price": 19.99
      }
    ]
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or missing JWT token
- `404 Not Found` - Order doesn't exist or doesn't belong to seller
- `500 Internal Server Error` - Database or server error

---

### 3. Update Order Status

Update the status of an order.

**Endpoint:** `PUT /api/seller/orders/{order_id}/status`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | integer | Yes | Order ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| status | string | Yes | New order status |

**Valid Status Values:**
- `pending` → `processing`, `cancelled`
- `processing` → `shipped`, `cancelled`
- `shipped` → `delivered`
- `delivered` → (final state, cannot change)
- `cancelled` → (final state, cannot change)

**Request Example:**
```http
PUT /api/seller/orders/1/status
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "status": "processing"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Order status updated successfully",
  "order": {
    "id": 1,
    "order_number": "ORD-2024-001",
    "customer_name": "John Doe",
    "total_amount": 299.99,
    "status": "processing",
    "order_date": "2024-01-15T10:30:00",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T14:30:00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid status or invalid status transition
  ```json
  {
    "success": false,
    "message": "Cannot change status of delivered order",
    "errors": {
      "status": "Invalid transition"
    }
  }
  ```
- `401 Unauthorized` - Invalid or missing JWT token
- `403 Forbidden` - Order doesn't belong to authenticated seller
- `404 Not Found` - Order doesn't exist
- `500 Internal Server Error` - Database or server error

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "message": "Human-readable error message",
  "errors": {
    "field_name": "Field-specific error message"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data or validation error |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but not authorized for this resource |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Server or database error |

### Common Error Scenarios

#### 1. Authentication Errors

**Missing Token:**
```json
{
  "success": false,
  "message": "Unauthorized: Seller authentication required"
}
```

**Invalid Token:**
```json
{
  "msg": "Token has expired"
}
```

#### 2. Validation Errors

**Missing Required Field:**
```json
{
  "success": false,
  "message": "Validation error: Product name is required",
  "errors": {
    "name": "Required"
  }
}
```

**Invalid Value:**
```json
{
  "success": false,
  "message": "Validation error: Price must be >= 0",
  "errors": {
    "price": "Must be >= 0"
  }
}
```

#### 3. Authorization Errors

**Resource Ownership:**
```json
{
  "success": false,
  "message": "Unauthorized: You don't own this product"
}
```

#### 4. Not Found Errors

```json
{
  "success": false,
  "message": "Product not found"
}
```

---

## Data Models

### Product

```typescript
interface Product {
  id: number;                    // Unique product ID
  name: string;                  // Product name (max 255 chars)
  description: string;           // Product description
  price: number;                 // Product price (>= 0)
  category: string;              // Product category (max 100 chars)
  stock_quantity: number;        // Available stock (>= 0)
  images: string[];              // Array of image URLs
  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
}
```

### Order

```typescript
interface Order {
  id: number;                    // Unique order ID
  order_number: string;          // Human-readable order number
  customer_name: string;         // Customer's name
  total_amount: number;          // Total order amount
  status: OrderStatus;           // Order status
  order_date: string;            // ISO 8601 timestamp
  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
  line_items?: OrderLineItem[];  // Order items (only in detail view)
}

type OrderStatus = 
  | 'pending' 
  | 'processing' 
  | 'shipped' 
  | 'delivered' 
  | 'cancelled';
```

### Order Line Item

```typescript
interface OrderLineItem {
  product_id: number;            // Product ID
  product_name: string;          // Product name
  quantity: number;              // Quantity ordered
  price: number;                 // Price per unit
}
```

### Pagination

```typescript
interface Pagination {
  page: number;                  // Current page number
  page_size: number;             // Items per page
  total: number;                 // Total number of items
  total_pages: number;           // Total number of pages
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting in production:

- **Recommended:** 100 requests per minute per seller
- **Burst:** 20 requests per second

---

## Versioning

**Current Version:** 1.0.0

API versioning is not currently implemented. Future versions may use URL versioning:

```
/api/v2/seller/products
```

---

## Changelog

### Version 1.0.0 (2024-01-15)
- Initial release
- Product management endpoints
- Order management endpoints
- JWT authentication
- Image upload support

---

## Support

For API support or bug reports:
1. Check the integration test suite
2. Review server logs
3. Verify database schema
4. Contact development team

---

## License

Internal API - Proprietary
