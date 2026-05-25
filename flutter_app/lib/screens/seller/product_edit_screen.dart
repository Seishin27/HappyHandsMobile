import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../../models/seller_product.dart';
import '../../providers/products_provider.dart';
import '../../widgets/cross_platform_image.dart';

/// Product edit/create screen for seller dashboard.
///
/// Supports both creating new products and editing existing products.
/// Pass a product ID to edit an existing product, or null to create a new one.
///
/// Features:
/// - Form fields for name, description, price, category, and stock quantity
/// - Multiple image picker for product images
/// - Save button that calls ProductsProvider methods
/// - Delete button for existing products with confirmation dialog
/// - Validation error display from backend
/// - Navigation back on successful save/delete
///
/// Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10
class ProductEditScreen extends StatefulWidget {
  final String? productId;

  const ProductEditScreen({
    super.key,
    this.productId,
  });

  @override
  State<ProductEditScreen> createState() => _ProductEditScreenState();
}

class _ProductEditScreenState extends State<ProductEditScreen> {
  final _formKey = GlobalKey<FormState>();

  // Form controllers
  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  late TextEditingController _priceController;
  late TextEditingController _categoryController;
  late TextEditingController _stockController;

  // State
  final List<PlatformFile> _selectedImages = [];
  List<String> _existingImageUrls = [];
  bool _isLoading = false;
  String? _errorMessage;
  SellerProduct? _existingProduct;

  bool get _isEditMode => widget.productId != null;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _descriptionController = TextEditingController();
    _priceController = TextEditingController();
    _categoryController = TextEditingController();
    _stockController = TextEditingController();

    // Fetch seller categories so the dropdown can be populated
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProductsProvider>().fetchSellerCategories();
    });

    // Load existing product data if in edit mode
    if (_isEditMode) {
      _loadExistingProduct();
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _priceController.dispose();
    _categoryController.dispose();
    _stockController.dispose();
    super.dispose();
  }

  void _loadExistingProduct() {
    final productsProvider = context.read<ProductsProvider>();
    _existingProduct = productsProvider.sellerProducts.firstWhere(
      (p) => p.id.toString() == widget.productId,
      orElse: () => const SellerProduct(
        id: 0,
        name: '',
        description: '',
        price: 0.0,
        category: '',
        stockQuantity: 0,
      ),
    );

    if (_existingProduct != null && _existingProduct!.id != 0) {
      _nameController.text = _existingProduct!.name;
      _descriptionController.text = _existingProduct!.description;
      _priceController.text = _existingProduct!.price.toString();
      _categoryController.text = _existingProduct!.category;
      _stockController.text = _existingProduct!.stockQuantity.toString();
      _existingImageUrls = List.from(_existingProduct!.images);
    }
  }

  Future<void> _pickImages() async {
    final int currentTotal = _existingImageUrls.length + _selectedImages.length;
    if (currentTotal >= 4) {
      _showErrorSnackBar('You can only upload up to 4 images.');
      return;
    }
    
    try {
      FilePickerResult? result = await FilePicker.pickFiles(
        type: FileType.image,
        allowMultiple: true,
        withData: true,
      );
      if (result != null) {
        setState(() {
          int allowed = 4 - currentTotal;
          if (result.files.length > allowed) {
            _showErrorSnackBar('Only the first $allowed selected images were added to reach the maximum of 4.');
            _selectedImages.addAll(result.files.take(allowed));
          } else {
            _selectedImages.addAll(result.files);
          }
        });
      }
    } catch (e) {
      _showErrorSnackBar('Failed to pick images: $e');
    }
  }



  void _removeSelectedImage(int index) {
    setState(() {
      _selectedImages.removeAt(index);
    });
  }

  void _removeExistingImage(int index) {
    setState(() {
      _existingImageUrls.removeAt(index);
    });
  }

  Future<void> _saveProduct() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    // Check if at least one image is provided (either existing or new)
    if (_existingImageUrls.isEmpty && _selectedImages.isEmpty) {
      _showErrorSnackBar('Please add at least one product image');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final product = SellerProduct(
        id: _existingProduct?.id ?? 0,
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim(),
        price: double.parse(_priceController.text.trim()),
        category: _categoryController.text.trim(),
        stockQuantity: int.parse(_stockController.text.trim()),
        images: _existingImageUrls,
      );

      final productsProvider = context.read<ProductsProvider>();

      if (_isEditMode) {
        await productsProvider.updateProduct(
          widget.productId!,
          product,
          _selectedImages.isNotEmpty ? _selectedImages : null,
        );
      } else {
        await productsProvider.createProduct(
          product,
          _selectedImages.isNotEmpty ? _selectedImages : null,
        );
      }

      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _isEditMode
                  ? 'Product updated successfully'
                  : 'Product created successfully',
            ),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
      _showErrorSnackBar(_errorMessage!);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _deleteProduct() async {
    if (!_isEditMode) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Product'),
        content: const Text(
          'Are you sure you want to delete this product? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: TextButton.styleFrom(
              foregroundColor: Colors.red,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    // Capture context-dependent objects before async operation
    // ignore: use_build_context_synchronously
    final navigator = Navigator.of(context);
    // ignore: use_build_context_synchronously
    final scaffoldMessenger = ScaffoldMessenger.of(context);
    // ignore: use_build_context_synchronously
    final productsProvider = context.read<ProductsProvider>();

    try {
      await productsProvider.deleteProduct(widget.productId!);

      if (!mounted) return;
      
      navigator.pop();
      scaffoldMessenger.showSnackBar(
        const SnackBar(
          content: Text('Product deleted successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      
      setState(() {
        _errorMessage = e.toString();
      });
      _showErrorSnackBar(_errorMessage!);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }



  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: Text(_isEditMode ? 'Edit Product' : 'Create Product'),
        actions: [
          if (_isEditMode)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: _isLoading ? null : _deleteProduct,
              tooltip: 'Delete Product',
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Error message display
                    if (_errorMessage != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.red.shade200),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.error_outline, color: Colors.red.shade700),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: TextStyle(color: Colors.red.shade700),
                              ),
                            ),
                          ],
                        ),
                      ),

                    // Product Images Section
                    _buildImagesSection(),
                    const SizedBox(height: 24),

                    // Product Name
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Product Name *',
                        hintText: 'Enter product name',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Product name is required';
                        }
                        if (value.trim().length < 3) {
                          return 'Product name must be at least 3 characters';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Description
                    TextFormField(
                      controller: _descriptionController,
                      decoration: const InputDecoration(
                        labelText: 'Description *',
                        hintText: 'Enter product description',
                        border: OutlineInputBorder(),
                      ),
                      maxLines: 4,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Description is required';
                        }
                        if (value.trim().length < 10) {
                          return 'Description must be at least 10 characters';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Price
                    TextFormField(
                      controller: _priceController,
                      decoration: const InputDecoration(
                        labelText: 'Price *',
                        hintText: 'Enter price',
                        border: OutlineInputBorder(),
                        prefixText: '₱ ',
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(RegExp(r'^\d+\.?\d{0,2}')),
                      ],
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Price is required';
                        }
                        final price = double.tryParse(value.trim());
                        if (price == null) {
                          return 'Please enter a valid price';
                        }
                        if (price <= 0) {
                          return 'Price must be greater than 0';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Category
                    Consumer<ProductsProvider>(
                      builder: (context, productsProvider, child) {
                        final categories = productsProvider.sellerCategories;
                        
                        // If categories aren't loaded yet, show a loading indicator
                        if (categories.isEmpty) {
                          return DropdownButtonFormField<String>(
                            initialValue: null,
                            decoration: const InputDecoration(
                              labelText: 'Category *',
                              hintText: 'Loading categories...',
                              border: OutlineInputBorder(),
                            ),
                            items: const [],
                            onChanged: null,
                          );
                        }

                        // Make sure the current value is actually in the list of items
                        String? selectedValue = _categoryController.text;
                        if (selectedValue.isNotEmpty) {
                          final exists = categories.any((c) => c['id'].toString() == selectedValue);
                          if (!exists) {
                            selectedValue = null; // Reset if invalid
                          }
                        } else {
                          selectedValue = null;
                        }

                        return DropdownButtonFormField<String>(
                          initialValue: selectedValue,
                          decoration: const InputDecoration(
                            labelText: 'Category *',
                            hintText: 'Select product category',
                            border: OutlineInputBorder(),
                          ),
                          items: categories.map((cat) {
                            return DropdownMenuItem<String>(
                              value: cat['id'].toString(),
                              child: Text(cat['name']?.toString() ?? 'Unknown'),
                            );
                          }).toList(),
                          onChanged: (value) {
                            if (value != null) {
                              _categoryController.text = value;
                            }
                          },
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Category is required';
                            }
                            return null;
                          },
                        );
                      },
                    ),
                    const SizedBox(height: 16),

                    // Stock Quantity
                    TextFormField(
                      controller: _stockController,
                      decoration: const InputDecoration(
                        labelText: 'Stock Quantity *',
                        hintText: 'Enter stock quantity',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                      ],
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Stock quantity is required';
                        }
                        final stock = int.tryParse(value.trim());
                        if (stock == null) {
                          return 'Please enter a valid number';
                        }
                        if (stock < 0) {
                          return 'Stock quantity cannot be negative';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 32),

                    // Save Button
                    ElevatedButton(
                      onPressed: _isLoading ? null : _saveProduct,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        backgroundColor: Theme.of(context).primaryColor,
                        foregroundColor: Colors.white,
                      ),
                      child: Text(
                        _isEditMode ? 'Update Product' : 'Create Product',
                        style: const TextStyle(fontSize: 16),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildImagesSection() {
    final totalImages = _existingImageUrls.length + _selectedImages.length;

    List<Widget> slots = [];
    int existingCount = _existingImageUrls.length;
    int selectedCount = _selectedImages.length;

    for (int i = 0; i < 4; i++) {
      if (i < existingCount) {
        slots.add(_buildExistingImageThumbnail(_existingImageUrls[i], i));
      } else if (i < existingCount + selectedCount) {
        slots.add(_buildSelectedImageThumbnail(_selectedImages[i - existingCount], i - existingCount));
      } else {
        slots.add(
          GestureDetector(
            onTap: _pickImages,
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey.shade300, style: BorderStyle.solid),
                borderRadius: BorderRadius.circular(8),
                color: Colors.grey.shade50,
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_photo_alternate, color: Colors.grey.shade400, size: 32),
                    const SizedBox(height: 4),
                    Text(
                      'Add',
                      style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'Product Images (Max 4) *',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            if (totalImages < 4)
              TextButton.icon(
                onPressed: _pickImages,
                icon: const Icon(Icons.add_photo_alternate),
                label: const Text('Add Images'),
              ),
          ],
        ),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1,
          children: slots,
        ),
      ],
    );
  }

  Widget _buildExistingImageThumbnail(String url, int index) {
    return Stack(
      children: [
        Positioned.fill(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: CrossPlatformNetworkImage(
              imageUrl: url,
              fit: BoxFit.cover,
              placeholder: Container(
                color: Colors.grey.shade200,
                child: const Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              ),
              errorWidget: Container(
                color: Colors.grey.shade200,
                child: Icon(Icons.broken_image, color: Colors.grey.shade400),
              ),
            ),
          ),
        ),
        Positioned(
          top: 4,
          right: 4,
          child: GestureDetector(
            onTap: () => _removeExistingImage(index),
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.close,
                size: 16,
                color: Colors.white,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSelectedImageThumbnail(PlatformFile file, int index) {
    return Stack(
      children: [
        Positioned.fill(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: file.bytes != null
                ? Image.memory(
                    file.bytes!,
                    fit: BoxFit.cover,
                  )
                : Image.file(
                    File(file.path!),
                    fit: BoxFit.cover,
                  ),
          ),
        ),
        Positioned(
          top: 4,
          right: 4,
          child: GestureDetector(
            onTap: () => _removeSelectedImage(index),
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.close,
                size: 16,
                color: Colors.white,
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 4,
          left: 4,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.6),
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Text(
              'New',
              style: TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
