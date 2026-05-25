import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/seller_profile.dart';
import '../../providers/profile_provider.dart';

/// Profile tab screen for seller dashboard.
///
/// Displays seller profile information with options to:
/// - View profile details
/// - Edit profile information
/// - Change password
/// - Save changes
class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab> {
  late TextEditingController _nameController;
  late TextEditingController _emailController;
  late TextEditingController _phoneController;
  late TextEditingController _businessNameController;
  late TextEditingController _businessAddressController;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _emailController = TextEditingController();
    _phoneController = TextEditingController();
    _businessNameController = TextEditingController();
    _businessAddressController = TextEditingController();

    // Fetch profile on first load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProfileProvider>().fetchProfile();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _businessNameController.dispose();
    _businessAddressController.dispose();
    super.dispose();
  }

  void _updateControllers(SellerProfile profile) {
    _nameController.text = profile.name;
    _emailController.text = profile.email;
    _phoneController.text = profile.phone;
    _businessNameController.text = profile.businessName;
    _businessAddressController.text = profile.businessAddress;
  }

  void _handleSave(ProfileProvider provider) {
    if (_nameController.text.isEmpty ||
        _emailController.text.isEmpty ||
        _phoneController.text.isEmpty ||
        _businessNameController.text.isEmpty ||
        _businessAddressController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all fields')),
      );
      return;
    }

    final updatedProfile = SellerProfile(
      id: provider.profile?.id ?? '',
      name: _nameController.text,
      email: _emailController.text,
      phone: _phoneController.text,
      businessName: _businessNameController.text,
      businessAddress: _businessAddressController.text,
    );

    provider.updateProfile(updatedProfile).then((_) {
      if (!mounted) return;
      if (provider.error == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated successfully')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${provider.error}')),
        );
      }
    });
  }

  void _handleChangePassword() {
    Navigator.of(context).pushNamed('/seller/change-password');
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ProfileProvider>(
      builder: (context, provider, _) {
        // Update controllers when profile is loaded
        if (provider.profile != null && _nameController.text.isEmpty) {
          _updateControllers(provider.profile!);
        }

        if (provider.isLoading && provider.profile == null) {
          return const Center(child: CircularProgressIndicator());
        }

        if (provider.error != null && provider.profile == null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Error: ${provider.error}'),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => provider.fetchProfile(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (provider.profile == null) {
          return const Center(child: Text('No profile data'));
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Profile header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Profile Information',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (!provider.isEditing)
                    ElevatedButton.icon(
                      onPressed: () => provider.enableEditMode(),
                      icon: const Icon(Icons.edit),
                      label: const Text('Edit'),
                    ),
                ],
              ),
              const SizedBox(height: 24),

              // Name field
              TextField(
                controller: _nameController,
                enabled: provider.isEditing,
                decoration: InputDecoration(
                  labelText: 'Full Name',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  prefixIcon: const Icon(Icons.person),
                ),
              ),
              const SizedBox(height: 16),

              // Email field
              TextField(
                controller: _emailController,
                enabled: provider.isEditing,
                decoration: InputDecoration(
                  labelText: 'Email',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  prefixIcon: const Icon(Icons.email),
                ),
              ),
              const SizedBox(height: 16),

              // Phone field
              TextField(
                controller: _phoneController,
                enabled: provider.isEditing,
                decoration: InputDecoration(
                  labelText: 'Phone',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  prefixIcon: const Icon(Icons.phone),
                ),
              ),
              const SizedBox(height: 16),

              // Business name field
              TextField(
                controller: _businessNameController,
                enabled: provider.isEditing,
                decoration: InputDecoration(
                  labelText: 'Business Name',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  prefixIcon: const Icon(Icons.business),
                ),
              ),
              const SizedBox(height: 16),

              // Business address field
              TextField(
                controller: _businessAddressController,
                enabled: provider.isEditing,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: 'Business Address',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  prefixIcon: const Icon(Icons.location_on),
                ),
              ),
              const SizedBox(height: 24),

              // Error message
              if (provider.error != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade100,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error, color: Colors.red.shade700),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          provider.error!,
                          style: TextStyle(color: Colors.red.shade700),
                        ),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 24),

              // Action buttons
              if (provider.isEditing)
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: provider.isLoading
                            ? null
                            : () => _handleSave(provider),
                        child: provider.isLoading
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text('Save Changes'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          _updateControllers(provider.profile!);
                          provider.disableEditMode();
                        },
                        child: const Text('Cancel'),
                      ),
                    ),
                  ],
                )
              else
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _handleChangePassword,
                    icon: const Icon(Icons.lock),
                    label: const Text('Change Password'),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
