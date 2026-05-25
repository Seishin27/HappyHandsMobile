# Implementation Plan: Seller Dashboard Integration

## Overview

This implementation plan breaks down the seller dashboard integration into five incremental phases, each delivering standalone value. The implementation follows the existing Flutter/Dart architecture with Provider-based state management, FlaskApiService for API communication, and JWT authentication.

**Technology Stack:**
- Frontend: Flutter/Dart with Provider state management
- Backend: Flask REST APIs + Socket.IO
- Database: MySQL
- Authentication: JWT tokens

**Implementation Approach:**
- Each phase builds on previous phases
- Incremental validation through checkpoints
- Focus on code implementation and automated testing
- Follow existing codebase patterns and conventions

---

## Phase 1: Dashboard Statistics Integration

### Tasks

- [x] 1. Create data models for dashboard statistics
  - Create `lib/models/sales_stats.dart` with fields: totalSales, todaySales, monthlySales, yearlyRevenue
  - Create `lib/models/order_stats.dart` with fields: totalOrders, pendingOrders, processingOrders, completedOrders
  - Create `lib/models/recent_order.dart` with fields: orderId, orderNumber, customerName, totalAmount, status, orderDate
  - Implement `fromJson()` factory constructors for JSON deserialization
  - Implement `toJson()` methods for serialization
  - _Requirements: 1.1, 1.2, 1.3_

- [ ]* 1.1 Write unit tests for dashboard statistics models
  - Test JSON deserialization for all model classes
  - Test edge cases (null values, missing fields)
  - Test date parsing for recent orders
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Add dashboard statistics API methods to FlaskApiService
  - Add `fetchSalesStats()` method calling GET `/api/seller/stats/sales`
  - Add `fetchOrderStats()` method calling GET `/api/seller/stats/orders`
  - Add `fetchRecentOrders()` method calling GET `/api/seller/stats/recent-orders`
  - Handle HTTP errors and return appropriate error messages
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. Implement SellerProvider for dashboard state management
  - Extend existing `lib/providers/seller_provider.dart` or create if missing
  - Add state fields: `SalesStats? salesStats`, `OrderStats? orderStats`, `List<RecentOrder> recentOrders`
  - Add loading and error state fields: `bool isLoading`, `String? error`
  - Implement `fetchDashboardStats()` method that calls all three API endpoints
  - Implement `refresh()` method for pull-to-refresh functionality
  - Call `notifyListeners()` after state changes
  - _Requirements: 1.1, 1.2, 1.3, 1.7_

- [ ]* 3.1 Write unit tests for SellerProvider
  - Test successful data fetching
  - Test error handling for API failures
  - Test loading state transitions
  - Mock FlaskApiService for isolated testing
  - _Requirements: 1.1, 1.2, 1.3, 1.7, 1.8_

- [x] 4. Create Dashboard tab UI screen
  - Create `lib/screens/seller/dashboard_tab.dart`
  - Implement StatefulWidget with pull-to-refresh functionality
  - Display sales metrics cards (total sales, today's sales, monthly sales, yearly revenue)
  - Display order metrics cards (total orders, pending, processing, completed)
  - Display recent orders list with order number, customer name, amount, status
  - Show loading indicator while fetching data
  - Show error message with retry button on failure
  - Use `context.watch<SellerProvider>()` to consume state
  - _Requirements: 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

- [ ]* 4.1 Write widget tests for Dashboard tab
  - Test loading state display
  - Test error state display with retry button
  - Test successful data display
  - Test pull-to-refresh interaction
  - _Requirements: 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

- [x] 5. Checkpoint - Phase 1 validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 2: Product and Order Management

### Tasks

- [x] 6. Create data models for products and orders
  - Create `lib/models/seller_product.dart` with fields: id, name, description, price, category, stockQuantity, images
  - Create `lib/models/seller_order.dart` with fields: id, orderNumber, customerName, totalAmount, status, orderDate, lineItems
  - Create `lib/models/order_line_item.dart` with fields: productId, productName, quantity, price
  - Implement `fromJson()` and `toJson()` methods for all models
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4_

- [ ]* 6.1 Write unit tests for product and order models
  - Test JSON serialization and deserialization
  - Test edge cases and validation
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4_

- [x] 7. Implement multipart upload service for product images
  - Create `lib/services/image_upload_service.dart`
  - Implement `uploadProductImages(List<File> images)` method
  - Use `http.MultipartRequest` for file uploads
  - Handle image compression and validation
  - Return list of uploaded image URLs
  - _Requirements: 2.5, 3.6, 3.7, 3.10_

- [x] 8. Add product management API methods to FlaskApiService
  - Add `fetchSellerProducts({int page, int pageSize})` calling GET `/api/seller/products`
  - Add `createProduct(SellerProduct product, List<File>? images)` calling POST `/api/seller/products`
  - Add `updateProduct(String id, SellerProduct product, List<File>? images)` calling PUT `/api/seller/products/{id}`
  - Add `deleteProduct(String id)` calling DELETE `/api/seller/products/{id}`
  - Integrate ImageUploadService for multipart requests
  - Handle validation errors from backend
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9_

- [x] 9. Add order management API methods to FlaskApiService
  - Add `fetchSellerOrders({int page, int pageSize})` calling GET `/api/seller/orders`
  - Add `fetchOrderDetails(String orderId)` calling GET `/api/seller/orders/{id}`
  - Add `updateOrderStatus(String orderId, String newStatus)` calling PUT `/api/seller/orders/{id}/status`
  - Handle status validation errors
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 10. Implement ProductsProvider for product state management
  - Extend existing `lib/providers/products_provider.dart`
  - Add methods: `fetchSellerProducts()`, `createProduct()`, `updateProduct()`, `deleteProduct()`
  - Manage loading and error states
  - Update local product list after mutations
  - Call `notifyListeners()` after state changes
  - _Requirements: 3.1, 3.7, 3.9, 3.10, 3.11_

- [ ]* 10.1 Write unit tests for ProductsProvider
  - Test CRUD operations
  - Test error handling
  - Test state updates and notifications
  - Mock FlaskApiService
  - _Requirements: 3.1, 3.7, 3.9, 3.10, 3.11_

- [x] 11. Implement OrdersProvider for order state management
  - Create `lib/providers/orders_provider.dart` extending ChangeNotifier
  - Add state fields: `List<SellerOrder> orders`, `SellerOrder? selectedOrder`, `bool isLoading`, `String? error`
  - Implement `fetchOrders()`, `fetchOrderDetails(String id)`, `updateOrderStatus(String id, String status)` methods
  - Implement filtering by order status
  - Call `notifyListeners()` after state changes
  - _Requirements: 5.1, 5.7, 5.8_

- [ ]* 11.1 Write unit tests for OrdersProvider
  - Test order fetching and filtering
  - Test status updates
  - Test error handling
  - Mock FlaskApiService
  - _Requirements: 5.1, 5.7, 5.8_

- [x] 12. Create Products tab UI screen
  - Create `lib/screens/seller/products_tab.dart`
  - Display paginated list of seller products with name, price, thumbnail
  - Add floating action button for creating new products
  - Implement navigation to product edit screen on tap
  - Show loading indicator and error states
  - Use `context.watch<ProductsProvider>()` to consume state
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.11, 3.12_

- [x] 13. Create product edit/create screen
  - Create `lib/screens/seller/product_edit_screen.dart`
  - Add form fields: name, description, price, category, stock quantity
  - Implement image picker for multiple product images
  - Add save button that calls ProductsProvider methods
  - Add delete button for existing products with confirmation dialog
  - Show validation errors from backend
  - Navigate back on successful save/delete
  - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ]* 13.1 Write widget tests for product screens
  - Test product list display
  - Test product creation flow
  - Test product editing flow
  - Test product deletion with confirmation
  - Test image upload UI
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [x] 14. Create Orders tab UI screen
  - Create `lib/screens/seller/orders_tab.dart`
  - Display list of orders with order number, customer name, amount, status
  - Add filter chips for order status (pending, processing, shipped, delivered, cancelled)
  - Implement navigation to order detail screen on tap
  - Show loading indicator and error states
  - Use `context.watch<OrdersProvider>()` to consume state
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.9, 5.10_

- [x] 15. Create order detail screen
  - Create `lib/screens/seller/order_detail_screen.dart`
  - Display complete order information: order number, customer details, line items, total amount, status
  - Add status update buttons for valid transitions (e.g., pending → processing → shipped → delivered)
  - Disable invalid status transitions
  - Show confirmation dialog before status update
  - Refresh order list after successful update
  - _Requirements: 5.4, 5.5, 5.6, 5.7, 5.8_

- [ ]* 15.1 Write widget tests for order screens
  - Test order list display and filtering
  - Test order detail display
  - Test status update flow
  - Test invalid status transition handling
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

- [x] 16. Wire Products and Orders tabs into seller dashboard
  - Update seller dashboard navigation to include Products and Orders tabs
  - Register OrdersProvider in main.dart provider list
  - Ensure proper provider initialization and disposal
  - _Requirements: 3.1, 5.1_

- [x] 17. Checkpoint - Phase 2 validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 3: Profile Management

### Tasks

- [x] 18. Create data models for seller profile
  - Create `lib/models/seller_profile.dart` with fields: id, name, email, phone, businessName, businessAddress
  - Implement `fromJson()` and `toJson()` methods
  - Add validation methods for email and phone formats
  - _Requirements: 6.4, 7.2_

- [x] 18.1 Write unit tests for seller profile model
  - Test JSON serialization and deserialization
  - Test validation methods
  - _Requirements: 6.4, 7.2_

- [x] 19. Add profile management API methods to FlaskApiService
  - Add `fetchSellerProfile()` calling GET `/api/seller/profile`
  - Add `updateSellerProfile(SellerProfile profile)` calling PUT `/api/seller/profile`
  - Add `changePassword(String currentPassword, String newPassword)` calling POST `/api/seller/profile/change-password`
  - Handle validation errors from backend
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

- [x] 20. Implement ProfileProvider for profile state management
  - Create `lib/providers/profile_provider.dart` extending ChangeNotifier
  - Add state fields: `SellerProfile? profile`, `bool isLoading`, `String? error`, `bool isEditing`
  - Implement `fetchProfile()`, `updateProfile(SellerProfile profile)`, `changePassword()` methods
  - Implement `toggleEditMode()` for enabling/disabling form editing
  - Call `notifyListeners()` after state changes
  - _Requirements: 7.1, 7.5, 7.9_

- [ ]* 20.1 Write unit tests for ProfileProvider
  - Test profile fetching and updating
  - Test password change
  - Test edit mode toggling
  - Test error handling
  - Mock FlaskApiService
  - _Requirements: 7.1, 7.5, 7.9_

- [x] 21. Create Profile tab UI screen
  - Create `lib/screens/seller/profile_tab.dart`
  - Display profile fields: name, email, phone, business name, business address
  - Add edit button to enable form editing
  - Add save button (visible only in edit mode) to save changes
  - Add change password button that navigates to password change screen
  - Show loading indicator and error states
  - Use `context.watch<ProfileProvider>()` to consume state
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.11, 7.12_

- [x] 22. Create password change screen
  - Create `lib/screens/seller/change_password_screen.dart`
  - Add form fields: current password, new password, confirm new password
  - Implement client-side validation (password match, minimum length)
  - Add submit button that calls ProfileProvider.changePassword()
  - Show success message and navigate back on successful change
  - Show validation errors from backend
  - _Requirements: 7.6, 7.7, 7.8, 7.9, 7.10_

- [ ]* 22.1 Write widget tests for profile screens
  - Test profile display and editing
  - Test password change flow
  - Test validation errors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_

- [x] 23. Wire Profile tab into seller dashboard
  - Update seller dashboard navigation to include Profile tab
  - Register ProfileProvider in main.dart provider list
  - _Requirements: 7.1_

- [x] 24. Checkpoint - Phase 3 validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 4: Real-Time Chat Functionality

### Tasks

- [ ] 25. Integrate Socket.IO client library
  - Add `socket_io_client` package to pubspec.yaml
  - Create `lib/services/socket_service.dart` as a singleton
  - Implement Socket.IO connection initialization with Flask backend URL
  - Implement JWT authentication on connection
  - Implement automatic reconnection logic
  - Implement connection state management (connected, disconnected, reconnecting)
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.8_

- [ ]* 25.1 Write unit tests for SocketService
  - Test connection initialization
  - Test authentication
  - Test reconnection logic
  - Mock Socket.IO client
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 26. Create data models for chat
  - Create `lib/models/chat_conversation.dart` with fields: customerId, customerName, lastMessage, lastMessageTime, unreadCount
  - Create `lib/models/chat_message.dart` with fields: id, senderId, senderName, message, timestamp, deliveryStatus
  - Implement `fromJson()` and `toJson()` methods
  - _Requirements: 9.1, 9.2, 10.1, 10.2_

- [ ]* 26.1 Write unit tests for chat models
  - Test JSON serialization and deserialization
  - Test timestamp parsing
  - _Requirements: 9.1, 9.2, 10.1, 10.2_

- [ ] 27. Add chat API methods to FlaskApiService
  - Add `fetchChatConversations()` calling GET `/api/seller/chats`
  - Add `fetchChatMessages(String customerId)` calling GET `/api/seller/chats/{customer_id}/messages`
  - Add `markMessagesAsRead(String customerId)` calling PUT `/api/seller/chats/{customer_id}/read`
  - _Requirements: 9.1, 10.1, 10.8_

- [ ] 28. Implement ChatProvider for chat state management
  - Create `lib/providers/chat_provider.dart` extending ChangeNotifier
  - Add state fields: `List<ChatConversation> conversations`, `Map<String, List<ChatMessage>> messagesByCustomer`, `bool isLoading`, `String? error`
  - Implement `fetchConversations()`, `fetchMessages(String customerId)`, `sendMessage(String customerId, String message)` methods
  - Integrate SocketService for real-time message sending and receiving
  - Listen to Socket.IO events for incoming messages and update state
  - Implement `markAsRead(String customerId)` method
  - Sort conversations by most recent message
  - Call `notifyListeners()` after state changes
  - _Requirements: 9.1, 9.2, 9.3, 9.5, 10.1, 10.4, 10.5, 10.8_

- [ ]* 28.1 Write unit tests for ChatProvider
  - Test conversation fetching and sorting
  - Test message fetching
  - Test message sending via Socket.IO
  - Test real-time message receiving
  - Test mark as read functionality
  - Mock FlaskApiService and SocketService
  - _Requirements: 9.1, 9.2, 9.3, 9.5, 10.1, 10.4, 10.5, 10.8_

- [ ] 29. Create Chat tab UI screen
  - Create `lib/screens/seller/chat_tab.dart`
  - Display list of conversations with customer name, last message preview, timestamp
  - Display unread count badge for conversations with unread messages
  - Sort conversations by most recent message first
  - Implement navigation to chat screen on tap
  - Show loading indicator and error states
  - Use `context.watch<ChatProvider>()` to consume state
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ] 30. Create chat screen for messaging
  - Create `lib/screens/seller/chat_screen.dart`
  - Display message history in chronological order with sender name and timestamp
  - Add text input field and send button at bottom
  - Implement message sending via ChatProvider
  - Listen to real-time message events and append to conversation
  - Auto-scroll to newest message when new message arrives
  - Display message delivery status (sending, sent, delivered)
  - Mark messages as read when screen is active
  - Show loading indicator while fetching message history
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_

- [ ]* 30.1 Write widget tests for chat screens
  - Test conversation list display
  - Test message display and ordering
  - Test message sending
  - Test real-time message receiving
  - Test unread badge display
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [ ] 31. Wire Chat tab into seller dashboard
  - Update seller dashboard navigation to include Chat tab
  - Register ChatProvider in main.dart provider list
  - Initialize SocketService when app starts
  - Dispose SocketService when app terminates
  - _Requirements: 8.1, 8.4, 8.5_

- [ ] 32. Checkpoint - Phase 4 validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Phase 5: Notifications System

### Tasks

- [ ] 33. Create data models for notifications
  - Create `lib/models/seller_notification.dart` with fields: id, type, title, message, timestamp, isRead, relatedEntityId
  - Implement `fromJson()` and `toJson()` methods
  - Add enum for notification types (order, product, chat, system)
  - _Requirements: 11.4, 12.4_

- [ ]* 33.1 Write unit tests for notification model
  - Test JSON serialization and deserialization
  - Test notification type enum
  - _Requirements: 11.4, 12.4_

- [ ] 34. Add notifications API methods to FlaskApiService
  - Add `fetchNotifications()` calling GET `/api/seller/notifications`
  - Add `markNotificationAsRead(String notificationId)` calling PUT `/api/seller/notifications/{id}/read`
  - Add `markAllNotificationsAsRead()` calling PUT `/api/seller/notifications/read-all`
  - _Requirements: 12.1, 12.2, 12.3, 12.6_

- [ ] 35. Implement NotificationsProvider for notification state management
  - Create `lib/providers/notifications_provider.dart` extending ChangeNotifier
  - Add state fields: `List<SellerNotification> notifications`, `int unreadCount`, `bool isLoading`, `String? error`
  - Implement `fetchNotifications()`, `markAsRead(String id)`, `markAllAsRead()` methods
  - Calculate unread count from notification list
  - Sort notifications with unread first
  - Call `notifyListeners()` after state changes
  - _Requirements: 11.3, 11.5, 11.6, 11.8, 12.5_

- [ ]* 35.1 Write unit tests for NotificationsProvider
  - Test notification fetching and sorting
  - Test mark as read functionality
  - Test mark all as read functionality
  - Test unread count calculation
  - Mock FlaskApiService
  - _Requirements: 11.3, 11.5, 11.6, 11.8, 12.5_

- [ ] 36. Create notifications screen
  - Create `lib/screens/seller/notifications_screen.dart`
  - Display list of notifications with title, message, timestamp
  - Display unread indicator for unread notifications
  - Implement tap handler to mark notification as read and navigate to related screen
  - Add "Mark all as read" button in app bar
  - Show loading indicator and error states
  - Use `context.watch<NotificationsProvider>()` to consume state
  - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.9_

- [ ]* 36.1 Write widget tests for notifications screen
  - Test notification list display
  - Test unread indicator
  - Test mark as read on tap
  - Test mark all as read
  - Test navigation to related screens
  - _Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [ ] 37. Add notifications icon to seller dashboard app bar
  - Update seller dashboard app bar to include notifications icon button
  - Display unread count badge on notifications icon
  - Implement navigation to notifications screen on tap
  - Update badge count reactively using `context.watch<NotificationsProvider>()`
  - _Requirements: 11.1, 11.2, 11.8_

- [ ] 38. Wire notifications into seller dashboard
  - Register NotificationsProvider in main.dart provider list
  - Fetch notifications when seller dashboard loads
  - Periodically refresh notification count in background
  - _Requirements: 11.1, 11.3_

- [ ] 39. Checkpoint - Phase 5 validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Final Integration and Testing

- [ ] 40. Integration testing across all phases
  - [ ] 40.1 Test complete seller dashboard navigation flow
    - Verify all tabs are accessible
    - Verify navigation between screens works correctly
    - _Requirements: All phases_

  - [ ]* 40.2 Write integration tests for critical user flows
    - Test product creation and order management flow
    - Test chat and notification interaction
    - Test profile update flow
    - _Requirements: All phases_

- [ ] 41. Final checkpoint - Complete feature validation
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- **Optional Tasks**: Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- **Requirements Traceability**: Each task explicitly references the requirements it implements
- **Incremental Validation**: Checkpoints ensure each phase is validated before moving to the next
- **Testing Strategy**: Unit tests for models and providers, widget tests for UI components, integration tests for end-to-end flows
- **Existing Patterns**: Follow the existing codebase patterns seen in ProductsProvider, FlaskApiService, and main.dart provider setup
- **Authentication**: All API calls automatically include JWT token via ApiClient's tokenProvider
- **Error Handling**: All providers should handle errors gracefully and expose error state to UI
- **Loading States**: All screens should display loading indicators during async operations
