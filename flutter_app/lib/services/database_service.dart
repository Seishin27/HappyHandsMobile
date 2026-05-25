import 'package:firebase_database/firebase_database.dart';

class DatabaseService {
  final DatabaseReference _db = FirebaseDatabase.instance.ref();

  // Fetch all categories
  Stream<DatabaseEvent> getCategories() {
    return _db.child('categories').onValue;
  }

  // Fetch all products
  Stream<DatabaseEvent> getProducts() {
    return _db.child('products').onValue;
  }
}