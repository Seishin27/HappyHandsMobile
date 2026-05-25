import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models/seller_profile.dart';

void main() {
  group('SellerProfile', () {
    group('fromJson', () {
      test('creates SellerProfile from valid JSON with camelCase keys', () {
        final json = {
          'id': 'seller123',
          'name': 'John Doe',
          'email': 'john@example.com',
          'phone': '+1234567890',
          'businessName': 'John\'s Shop',
          'businessAddress': '123 Main St, City, State',
        };

        final profile = SellerProfile.fromJson(json);

        expect(profile.id, 'seller123');
        expect(profile.name, 'John Doe');
        expect(profile.email, 'john@example.com');
        expect(profile.phone, '+1234567890');
        expect(profile.businessName, 'John\'s Shop');
        expect(profile.businessAddress, '123 Main St, City, State');
      });

      test('creates SellerProfile from JSON with snake_case keys', () {
        final json = {
          'id': 'seller456',
          'name': 'Jane Smith',
          'email': 'jane@example.com',
          'phone': '9876543210',
          'business_name': 'Jane\'s Store',
          'business_address': '456 Oak Ave, Town, State',
        };

        final profile = SellerProfile.fromJson(json);

        expect(profile.id, 'seller456');
        expect(profile.name, 'Jane Smith');
        expect(profile.email, 'jane@example.com');
        expect(profile.phone, '9876543210');
        expect(profile.businessName, 'Jane\'s Store');
        expect(profile.businessAddress, '456 Oak Ave, Town, State');
      });

      test('handles missing fields with empty strings', () {
        final json = {
          'id': 'seller789',
          'name': 'Bob Johnson',
        };

        final profile = SellerProfile.fromJson(json);

        expect(profile.id, 'seller789');
        expect(profile.name, 'Bob Johnson');
        expect(profile.email, '');
        expect(profile.phone, '');
        expect(profile.businessName, '');
        expect(profile.businessAddress, '');
      });

      test('handles sellerID key variant', () {
        final json = {
          'sellerID': 'seller999',
          'name': 'Alice Brown',
          'email': 'alice@example.com',
          'phone': '5555555555',
          'businessName': 'Alice\'s Business',
          'businessAddress': '789 Pine Rd, Village, State',
        };

        final profile = SellerProfile.fromJson(json);

        expect(profile.id, 'seller999');
        expect(profile.name, 'Alice Brown');
      });

      test('handles empty JSON', () {
        final json = <String, dynamic>{};

        final profile = SellerProfile.fromJson(json);

        expect(profile.id, '');
        expect(profile.name, '');
        expect(profile.email, '');
        expect(profile.phone, '');
        expect(profile.businessName, '');
        expect(profile.businessAddress, '');
      });
    });

    group('toJson', () {
      test('converts SellerProfile to JSON with camelCase keys', () {
        final profile = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final json = profile.toJson();

        expect(json['id'], 'seller123');
        expect(json['name'], 'John Doe');
        expect(json['email'], 'john@example.com');
        expect(json['phone'], '+1234567890');
        expect(json['businessName'], 'John\'s Shop');
        expect(json['businessAddress'], '123 Main St, City, State');
      });

      test('round-trip JSON serialization', () {
        final original = SellerProfile(
          id: 'seller456',
          name: 'Jane Smith',
          email: 'jane@example.com',
          phone: '9876543210',
          businessName: 'Jane\'s Store',
          businessAddress: '456 Oak Ave, Town, State',
        );

        final json = original.toJson();
        final restored = SellerProfile.fromJson(json);

        expect(restored.id, original.id);
        expect(restored.name, original.name);
        expect(restored.email, original.email);
        expect(restored.phone, original.phone);
        expect(restored.businessName, original.businessName);
        expect(restored.businessAddress, original.businessAddress);
      });
    });

    group('isValidEmail', () {
      test('returns true for valid email addresses', () {
        final validEmails = [
          'john@example.com',
          'jane.smith@company.co.uk',
          'user+tag@domain.org',
          'test123@test-domain.com',
        ];

        for (final email in validEmails) {
          final profile = SellerProfile(
            id: 'test',
            name: 'Test',
            email: email,
            phone: '1234567890',
            businessName: 'Test',
            businessAddress: 'Test',
          );
          expect(profile.isValidEmail(), true, reason: 'Email $email should be valid');
        }
      });

      test('returns false for invalid email addresses', () {
        final invalidEmails = [
          'notanemail',
          'missing@domain',
          '@nodomain.com',
          'spaces in@email.com',
          'double@@domain.com',
          'user@.com',
        ];

        for (final email in invalidEmails) {
          final profile = SellerProfile(
            id: 'test',
            name: 'Test',
            email: email,
            phone: '1234567890',
            businessName: 'Test',
            businessAddress: 'Test',
          );
          expect(profile.isValidEmail(), false, reason: 'Email $email should be invalid');
        }
      });

      test('returns false for empty email', () {
        final profile = SellerProfile(
          id: 'test',
          name: 'Test',
          email: '',
          phone: '1234567890',
          businessName: 'Test',
          businessAddress: 'Test',
        );
        expect(profile.isValidEmail(), false);
      });
    });

    group('isValidPhone', () {
      test('returns true for valid phone numbers', () {
        final validPhones = [
          '1234567890',
          '+1 (234) 567-8900',
          '123-456-7890',
          '+44 20 7946 0958',
          '9876543210',
        ];

        for (final phone in validPhones) {
          final profile = SellerProfile(
            id: 'test',
            name: 'Test',
            email: 'test@example.com',
            phone: phone,
            businessName: 'Test',
            businessAddress: 'Test',
          );
          expect(profile.isValidPhone(), true, reason: 'Phone $phone should be valid');
        }
      });

      test('returns false for phone numbers with less than 10 digits', () {
        final invalidPhones = [
          '123456789',
          '+1 (234) 567',
          '12345',
          '',
        ];

        for (final phone in invalidPhones) {
          final profile = SellerProfile(
            id: 'test',
            name: 'Test',
            email: 'test@example.com',
            phone: phone,
            businessName: 'Test',
            businessAddress: 'Test',
          );
          expect(profile.isValidPhone(), false, reason: 'Phone $phone should be invalid');
        }
      });
    });

    group('copyWith', () {
      test('creates a copy with all fields unchanged', () {
        final original = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final copy = original.copyWith();

        expect(copy.id, original.id);
        expect(copy.name, original.name);
        expect(copy.email, original.email);
        expect(copy.phone, original.phone);
        expect(copy.businessName, original.businessName);
        expect(copy.businessAddress, original.businessAddress);
      });

      test('creates a copy with some fields overridden', () {
        final original = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final copy = original.copyWith(
          name: 'Jane Doe',
          email: 'jane@example.com',
        );

        expect(copy.id, original.id);
        expect(copy.name, 'Jane Doe');
        expect(copy.email, 'jane@example.com');
        expect(copy.phone, original.phone);
        expect(copy.businessName, original.businessName);
        expect(copy.businessAddress, original.businessAddress);
      });

      test('creates a copy with all fields overridden', () {
        final original = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final copy = original.copyWith(
          id: 'seller456',
          name: 'Jane Smith',
          email: 'jane@example.com',
          phone: '9876543210',
          businessName: 'Jane\'s Store',
          businessAddress: '456 Oak Ave, Town, State',
        );

        expect(copy.id, 'seller456');
        expect(copy.name, 'Jane Smith');
        expect(copy.email, 'jane@example.com');
        expect(copy.phone, '9876543210');
        expect(copy.businessName, 'Jane\'s Store');
        expect(copy.businessAddress, '456 Oak Ave, Town, State');
      });
    });

    group('equality and hashing', () {
      test('two profiles with same data are equal', () {
        final profile1 = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final profile2 = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        expect(profile1, profile2);
        expect(profile1.hashCode, profile2.hashCode);
      });

      test('two profiles with different data are not equal', () {
        final profile1 = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final profile2 = SellerProfile(
          id: 'seller456',
          name: 'Jane Smith',
          email: 'jane@example.com',
          phone: '9876543210',
          businessName: 'Jane\'s Store',
          businessAddress: '456 Oak Ave, Town, State',
        );

        expect(profile1, isNot(profile2));
      });
    });

    group('toString', () {
      test('returns a string representation of the profile', () {
        final profile = SellerProfile(
          id: 'seller123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1234567890',
          businessName: 'John\'s Shop',
          businessAddress: '123 Main St, City, State',
        );

        final str = profile.toString();

        expect(str, contains('SellerProfile'));
        expect(str, contains('seller123'));
        expect(str, contains('John Doe'));
        expect(str, contains('john@example.com'));
      });
    });
  });
}
