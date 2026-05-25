# Navigation Flow Diagram - Seller Login Redirect

## Complete Login & Navigation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APP STARTUP                                     │
│                                                                         │
│  main.dart → App() → MaterialApp with routes                           │
│                                                                         │
│  Routes:                                                                │
│  - '/' → HomeScreen                                                     │
│  - '/seller-dashboard' → SellerShell                                    │
│  - '/rider-dashboard' → RiderShell                                      │
│  - '/auth' → AuthScreen                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      USER NAVIGATES TO LOGIN                            │
│                                                                         │
│  HomeScreen → Tap "Seller Portal" button                               │
│           ↓                                                             │
│  SellerAuthScreen (with tabs: Login | Register)                        │
│           ↓                                                             │
│  User clicks "Login" tab                                                │
│           ↓                                                             │
│  AuthForm widget displays with:                                         │
│  - Email input field                                                    │
│  - Password input field                                                 │
│  - "Login as Seller" button                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    USER ENTERS CREDENTIALS                              │
│                                                                         │
│  User enters:                                                           │
│  - Email: seller@example.com                                            │
│  - Password: password123                                                │
│                                                                         │
│  User taps "Login as Seller" button                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    FORM VALIDATION (AuthForm)                           │
│                                                                         │
│  _handleLogin() called:                                                 │
│                                                                         │
│  1. Validate email format                                               │
│     ✓ Valid email format                                                │
│                                                                         │
│  2. Validate password length                                            │
│     ✓ Password >= 6 characters                                          │
│                                                                         │
│  3. Set loading state                                                   │
│     _isLoading = true                                                   │
│     Show loading spinner                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION (AuthProvider)                          │
│                                                                         │
│  AuthProvider.login(                                                    │
│    email: 'seller@example.com',                                         │
│    password: 'password123',                                             │
│    role: 'seller'                                                       │
│  )                                                                      │
│                                                                         │
│  Sets: _activeRole = 'seller'                                           │
│                                                                         │
│  Calls: MysqlAuthService.loginAsSeller()                                │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                   BACKEND AUTHENTICATION                                │
│                                                                         │
│  Flask Backend:                                                         │
│                                                                         │
│  POST /api/seller/login                                                 │
│  {                                                                      │
│    "email": "seller@example.com",                                       │
│    "password": "password123"                                            │
│  }                                                                      │
│                                                                         │
│  Database lookup:                                                       │
│  - Find seller by email                                                 │
│  - Verify password hash                                                 │
│  - Generate JWT token                                                   │
│                                                                         │
│  Response:                                                              │
│  {                                                                      │
│    "success": true,                                                     │
│    "token": "eyJhbGciOiJIUzI1NiIs...",                                  │
│    "seller": {                                                          │
│      "id": 1,                                                           │
│      "email": "seller@example.com",                                     │
│      "name": "John Seller"                                              │
│    }                                                                    │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                   STORE AUTHENTICATION DATA                             │
│                                                                         │
│  AuthProvider stores:                                                   │
│  - _user = MysqlUser(...)                                               │
│  - _backendAccessToken = "eyJhbGciOiJIUzI1NiIs..."                      │
│  - _activeRole = 'seller'                                               │
│                                                                         │
│  Calls: notifyListeners()                                               │
│                                                                         │
│  AuthForm detects success:                                              │
│  - _isLoading = false                                                   │
│  - _errorMessage = null                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    SHOW SUCCESS MESSAGE                                 │
│                                                                         │
│  ScaffoldMessenger shows SnackBar:                                      │
│  ┌─────────────────────────────────────┐                               │
│  │ ✓ Welcome back, Seller!             │                               │
│  │ (Green background, 1 second)        │                               │
│  └─────────────────────────────────────┘                               │
│                                                                         │
│  Duration: 1 second                                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                  NAVIGATE TO DASHBOARD (NEW!)                           │
│                                                                         │
│  _navigateToDashboard(authProvider) called:                             │
│                                                                         │
│  1. Check authProvider.activeRole                                       │
│     activeRole = 'seller'                                               │
│                                                                         │
│  2. Determine route                                                     │
│     route = '/seller-dashboard'                                         │
│                                                                         │
│  3. Navigate with stack cleanup                                         │
│     Navigator.pushNamedAndRemoveUntil(                                  │
│       '/seller-dashboard',                                              │
│       (route) => route.isFirst                                          │
│     )                                                                   │
│                                                                         │
│  Navigation Stack Before:                                               │
│  [HomeScreen] ← base                                                    │
│  [SellerAuthScreen] ← current                                           │
│                                                                         │
│  Navigation Stack After:                                                │
│  [HomeScreen] ← base                                                    │
│  [SellerShell] ← current                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    SELLER DASHBOARD DISPLAYS                            │
│                                                                         │
│  SellerShell widget builds:                                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │ Seller Dashboard                                            │       │
│  ├─────────────────────────────────────────────────────────────┤       │
│  │ [Dashboard] [Orders] [Products] [Chat] [Profile]           │       │
│  ├─────────────────────────────────────────────────────────────┤       │
│  │                                                             │       │
│  │  Dashboard Tab (default):                                   │       │
│  │  - Sales Statistics                                         │       │
│  │  - Order Statistics                                         │       │
│  │  - Recent Orders                                            │       │
│  │                                                             │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  User can now:                                                          │
│  - View dashboard statistics                                            │
│  - Click "Orders" tab                                                   │
│  - Click "Products" tab                                                 │
│  - Click "Chat" tab                                                     │
│  - Click "Profile" tab                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORDERS TAB LOADS DATA                                │
│                                                                         │
│  User taps "Orders" tab:                                                │
│                                                                         │
│  OrdersTab.initState() called:                                          │
│  - Calls OrdersProvider.fetchOrders()                                   │
│                                                                         │
│  OrdersProvider.fetchOrders():                                          │
│  - Sets _isLoading = true                                               │
│  - Calls FlaskApiService.fetchSellerOrders()                            │
│                                                                         │
│  FlaskApiService.fetchSellerOrders():                                   │
│  - Makes API call: GET /api/seller/orders?page=1&page_size=20           │
│  - Includes JWT token in Authorization header                           │
│                                                                         │
│  Backend processes request:                                             │
│  - Verifies JWT token                                                   │
│  - Extracts seller ID from token                                        │
│  - Queries database for seller's orders                                 │
│  - Returns orders list                                                  │
│                                                                         │
│  OrdersProvider receives response:                                      │
│  - Parses JSON into List<SellerOrder>                                   │
│  - Sets _orders = [...]                                                 │
│  - Sets _isLoading = false                                              │
│  - Calls notifyListeners()                                              │
│                                                                         │
│  OrdersTab rebuilds:                                                    │
│  - Displays orders list                                                 │
│  - Shows order number, customer name, amount, status                    │
│  - Allows filtering by status                                           │
│  - Allows tapping to see order details                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Navigation Stack Visualization

### Before Login
```
Navigation Stack:
┌──────────────────┐
│  HomeScreen      │ ← Base (first route)
└──────────────────┘
```

### During Login
```
Navigation Stack:
┌──────────────────┐
│  HomeScreen      │ ← Base
├──────────────────┤
│ SellerAuthScreen │ ← Current
└──────────────────┘
```

### After Login (with pushNamedAndRemoveUntil)
```
Navigation Stack:
┌──────────────────┐
│  HomeScreen      │ ← Base (kept)
├──────────────────┤
│  SellerShell     │ ← Current (new)
└──────────────────┘

SellerAuthScreen is removed from stack!
```

### After Tapping Back Button
```
Navigation Stack:
┌──────────────────┐
│  HomeScreen      │ ← Current (goes back here)
└──────────────────┘

User is back at home, NOT at login screen!
```

## Role-Based Routing Decision Tree

```
                    ┌─────────────────┐
                    │  Login Success  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Check activeRole│
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
         │   'seller'  │ │ 'rider' │ │  'user' │
         └──────┬──────┘ └──┬──────┘ └──┬──────┘
                │           │           │
         ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
         │   Navigate  │ │ Navigate│ │ Navigate│
         │     to      │ │   to    │ │   to    │
         │   /seller-  │ │ /rider- │ │  /home  │
         │  dashboard  │ │dashboard│ │         │
         └──────┬──────┘ └──┬──────┘ └──┬──────┘
                │           │           │
         ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
         │ SellerShell │ │RiderShell│ │HomeScreen
         │             │ │          │ │(logged in)
         │ - Dashboard │ │- Orders  │ │
         │ - Orders    │ │- Delivery│ │
         │ - Products  │ │- Profile │ │
         │ - Chat      │ │          │ │
         │ - Profile   │ │          │ │
         └─────────────┘ └──────────┘ └──────────┘
```

## Error Handling Flow

```
                    ┌─────────────────┐
                    │  User Submits   │
                    │  Login Form     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Validate Input  │
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────▼──────┐ ┌──▼──────┐ ┌──▼──────┐
         │   Invalid   │ │  Valid  │ │  Valid  │
         │   Format    │ │ Format  │ │ Format  │
         │             │ │         │ │         │
         │ Show Error: │ │ Call    │ │ Call    │
         │ "Enter a    │ │ Backend │ │ Backend │
         │  valid      │ │         │ │         │
         │  email"     │ │         │ │         │
         └──────┬──────┘ └──┬──────┘ └──┬──────┘
                │           │           │
                │      ┌────▼────┐      │
                │      │ Backend  │      │
                │      │ Response │      │
                │      └────┬─────┘      │
                │           │            │
                │    ┌──────┼──────┐     │
                │    │             │     │
                │ ┌──▼──┐      ┌──▼──┐  │
                │ │Error│      │Success
                │ │     │      │      │
                │ │Show │      │Show  │
                │ │Error│      │Success
                │ │Msg  │      │Msg   │
                │ │     │      │      │
                │ │Stay │      │Navigate
                │ │on   │      │to    │
                │ │Form │      │Dashboard
                │ └─────┘      └──────┘
                │                      │
                └──────────┬───────────┘
                           │
                    ┌──────▼──────┐
                    │ User can    │
                    │ retry or    │
                    │ continue    │
                    └─────────────┘
```

## Summary

The navigation flow is now:

1. **User logs in** → AuthForm validates
2. **Backend authenticates** → Returns JWT token
3. **AuthProvider stores** → Sets activeRole
4. **AuthForm detects success** → Shows snackbar
5. **AuthForm navigates** → Calls _navigateToDashboard()
6. **Route determined** → Based on activeRole
7. **Navigation executed** → pushNamedAndRemoveUntil
8. **Dashboard displays** → User sees their dashboard
9. **Orders load** → API call to /api/seller/orders
10. **User can interact** → Manage orders, products, etc.

✅ **Complete and working!**
