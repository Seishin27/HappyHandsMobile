class AppConstants {
  // API Configuration
  static const String apiBaseUrl = 'http://localhost:5500';
  static const Duration apiTimeout = Duration(seconds: 30);
  
  // Categories matching web app
  static const List<Map<String, String>> categories = [
    {'id': 'baby-clothes', 'name': 'Baby Clothes & Accessories', 'icon': '👶'},
    {'id': 'comfort-toys', 'name': 'Comfort Toys', 'icon': '🧸'},
    {'id': 'educational-toys', 'name': 'Educational Toys', 'icon': '🎓'},
    {'id': 'nursery-furniture', 'name': 'Nursery Furniture', 'icon': '🪑'},
    {'id': 'stroller-gear', 'name': 'Strollers & Gear', 'icon': '🚗'},
    {'id': 'safety-and-health', 'name': 'Safety & Health', 'icon': '🩺'},
  ];
  
  // Hero carousel data matching web app
  static const List<Map<String, dynamic>> heroSlides = [
    {
      'title': 'Playful learning starts here',
      'subtitle': 'Hand-picked toys and essentials to spark imagination and comfort for little ones.',
      'gradient': 'gradient1',
      'image': 'photo1.png',
    },
    {
      'title': 'Cozy clothes & comfy cuddles',
      'subtitle': 'Soft, safe fabrics perfect for nap time and first steps.',
      'gradient': 'gradient2',
      'image': 'baby-carousel.png',
    },
    {
      'title': 'Safe & cheerful nursery furniture',
      'subtitle': 'Design-forward pieces that keep safety and smiles front-and-center.',
      'gradient': 'gradient3',
      'image': 'babyhero.jpg',
    },
  ];
  
  // Pagination
  static const int defaultPageSize = 12;
  static const int searchPageSize = 20;
  
  // Image dimensions
  static const double productImageAspectRatio = 1.0;
  static const double heroImageAspectRatio = 16.0 / 9.0;
  
  // Spacing constants matching web design
  static const double spacingXS = 4.0;
  static const double spacingSM = 8.0;
  static const double spacingMD = 16.0;
  static const double spacingLG = 24.0;
  static const double spacingXL = 32.0;
  static const double spacingXXL = 48.0;
  
  // Border radius
  static const double radiusSM = 8.0;
  static const double radiusMD = 12.0;
  static const double radiusLG = 20.0;
  static const double radiusXL = 24.0;
  static const double radiusFull = 999.0;
  
  // Font sizes
  static const double fontXS = 11.0;
  static const double fontSM = 12.0;
  static const double fontBase = 14.0;
  static const double fontLG = 16.0;
  static const double fontXL = 18.0;
  static const double font2XL = 20.0;
  static const double font3XL = 24.0;
  static const double font4XL = 28.0;
  static const double font5XL = 36.0;
  static const double font6XL = 48.0;
  
  // Animation durations
  static const Duration animationFast = Duration(milliseconds: 150);
  static const Duration animationNormal = Duration(milliseconds: 300);
  static const Duration animationSlow = Duration(milliseconds: 800);
  
  // Cache keys
  static const String cacheUserSession = 'user_session';
  static const String cacheCartItems = 'cart_items';
  static const String cacheFavorites = 'favorites';
  
  // Error messages
  static const String errorNetwork = 'Network error. Please check your connection.';
  static const String errorServer = 'Server error. Please try again later.';
  static const String errorAuth = 'Authentication failed. Please login again.';
  static const String errorNotFound = 'Product not found.';
  static const String errorGeneral = 'Something went wrong. Please try again.';
  
  // Success messages
  static const String successAddedToCart = 'Product added to cart successfully!';
  static const String successRemovedFromCart = 'Product removed from cart.';
  static const String successLogin = 'Login successful!';
  static const String successRegister = 'Registration successful!';
  
  // Feature highlights from web app
  static const List<Map<String, String>> features = [
    {'icon': '📞', 'title': 'Customer help', 'subtitle': 'Got help when you needed?'},
    {'icon': '🚚', 'title': 'Flat Rate Shipping', 'subtitle': 'Starting at ₱36.00'},
    {'icon': '↩️', 'title': 'Returns', 'subtitle': 'Within 7 days'},
    {'icon': '💳', 'title': 'Secure Payments', 'subtitle': 'Cash On Delivery Payments'},
  ];
}
