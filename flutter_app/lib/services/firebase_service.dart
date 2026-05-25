import 'package:firebase_database/firebase_database.dart';
import 'dart:developer' as developer;

class FirebaseDatabaseService {
  final DatabaseReference _dbRef = FirebaseDatabase.instance.ref();

  // 1. Fetch Categories
  // Returns a List of Maps for your CategoryProvider
  Future<List<Map<String, dynamic>>> getCategories() async {
    try {
      final snapshot = await _dbRef.child('categories').get();
      if (snapshot.exists) {
        final data = snapshot.value as Map<dynamic, dynamic>;
        return data.entries.map((e) {
          return Map<String, dynamic>.from(e.value as Map);
        }).toList();
      }
      return [];
    } catch (e) {
      developer.log("Error fetching categories: $e");
      return [];
    }
  }

  // 2. Fetch Products
  // This will pull all products under the 'products' node
  Future<List<Map<String, dynamic>>> getProducts() async {
    try {
      final snapshot = await _dbRef.child('products').get();
      if (snapshot.exists) {
        final data = snapshot.value as Map<dynamic, dynamic>;
        return data.entries.map((e) {
          return Map<String, dynamic>.from(e.value as Map);
        }).toList();
      }
      return [];
    } catch (e) {
      developer.log("Error fetching products: $e");
      return [];
    }
  }

  // 3. Live Stream (Optional but Recommended)
  // Use this if you want the app to update instantly when you change data in Firebase
  Stream<DatabaseEvent> getProductsStream() {
    return _dbRef.child('products').onValue;
  }
}