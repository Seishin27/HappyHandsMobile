enum AppRole {
  user,
  seller,
  rider,
}

extension AppRoleX on AppRole {
  String get key => switch (this) {
        AppRole.user => 'user',
        AppRole.seller => 'seller',
        AppRole.rider => 'rider',
      };

  static AppRole? fromKey(String key) {
    switch (key) {
      case 'user':
        return AppRole.user;
      case 'seller':
        return AppRole.seller;
      case 'rider':
        return AppRole.rider;
      default:
        return null;
    }
  }
}

