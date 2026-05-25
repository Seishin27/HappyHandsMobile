import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../../core/utils/money.dart';
import '../../models/cart_item.dart';
import '../../providers/auth_provider.dart';
import '../../providers/cart_provider.dart';
import '../../widgets/error_view.dart';
import '../../widgets/loading_widget.dart';

class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartProvider>();
    final authToken = context.watch<AuthProvider>().backendAccessToken;

    void reloadCart() {
      context.read<CartProvider>().loadCart(authToken);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cart'),
        actions: [
          IconButton(
            onPressed: cart.isLoading ? null : reloadCart,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Builder(
        builder: (context) {
          if (cart.isLoading) {
            return const LoadingWidget(label: 'Loading cart...');
          }
          if (cart.error != null) {
            return ErrorView(message: cart.error!, onRetry: reloadCart);
          }

          final items = cart.cartItems;
          if (items.isEmpty) {
            return const Center(child: Text('Your cart is empty.'));
          }

          return RefreshIndicator(
            onRefresh: () => context.read<CartProvider>().loadCart(authToken),
            child: ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: items.length + 1,
              separatorBuilder: (context, index) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                if (index == items.length) {
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Total',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
                          Text(
                            formatMoney(cart.total),
                            style: TextStyle(
                              fontWeight: FontWeight.w900,
                              color: Theme.of(context).colorScheme.primary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                final item = items[index];
                return Dismissible(
                  key: ValueKey('cart-dismiss-${item.id}'),
                  direction: DismissDirection.endToStart,
                  background: Container(
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 20),
                    margin: const EdgeInsets.symmetric(vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.red.shade400,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.delete_outline, color: Colors.white, size: 24),
                  ),
                  confirmDismiss: (_) => context.read<CartProvider>().removeFromCart(
                    cartItem: item,
                    authToken: authToken,
                  ),
                  child: _CartItemCard(
                    key: ValueKey('cart-item-${item.id}'),
                    item: item,
                    authToken: authToken,
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _CartItemCard extends StatefulWidget {
  final CartItem item;
  final String? authToken;

  const _CartItemCard({super.key, required this.item, this.authToken});

  @override
  State<_CartItemCard> createState() => _CartItemCardState();
}

class _CartItemCardState extends State<_CartItemCard> {
  late final TextEditingController _qtyController;

  @override
  void initState() {
    super.initState();
    _qtyController = TextEditingController(text: widget.item.quantity.toString());
  }

  @override
  void didUpdateWidget(covariant _CartItemCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Keep the field in sync if the quantity changed elsewhere.
    if (widget.item.quantity.toString() != _qtyController.text) {
      _qtyController.text = widget.item.quantity.toString();
      _qtyController.selection = TextSelection.fromPosition(
        TextPosition(offset: _qtyController.text.length),
      );
    }
  }

  @override
  void dispose() {
    _qtyController.dispose();
    super.dispose();
  }

  Future<void> _setQuantity(int newQty) async {
    final cart = context.read<CartProvider>();
    final stock = widget.item.product.stock ?? 0;
    if (newQty < 1) newQty = 1;
    if (stock > 0 && newQty > stock) {
      newQty = stock;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Only $stock in stock')),
      );
    }
    if (newQty == widget.item.quantity) {
      _qtyController.text = newQty.toString();
      return;
    }
    final ok = await cart.updateItemQuantity(
      cartItem: widget.item,
      quantity: newQty,
      authToken: widget.authToken,
    );
    if (!mounted) return;
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(cart.error ?? 'Could not update quantity')),
      );
      _qtyController.text = widget.item.quantity.toString();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartProvider>();
    final item = widget.item;
    final stock = item.product.stock ?? 0;
    final canIncrement = !cart.isUpdating && (stock <= 0 || item.quantity < stock);
    final canDecrement = !cart.isUpdating && item.quantity > 1;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    item.product.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                Text(
                  formatMoney(item.totalPrice),
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${formatMoney(item.unitPrice)} each${stock > 0 ? ' • $stock in stock' : ''}',
              style: TextStyle(fontSize: 12, color: Colors.grey[700]),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                IconButton(
                  onPressed: canDecrement
                      ? () => _setQuantity(item.quantity - 1)
                      : null,
                  icon: const Icon(Icons.remove_circle_outline),
                ),
                SizedBox(
                  width: 64,
                  child: TextField(
                    controller: _qtyController,
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(5),
                    ],
                    decoration: const InputDecoration(
                      isDense: true,
                      contentPadding: EdgeInsets.symmetric(vertical: 8),
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (value) {
                      final parsed = int.tryParse(value);
                      if (parsed != null && parsed >= 1) {
                        _setQuantity(parsed);
                      } else {
                        _qtyController.text = item.quantity.toString();
                      }
                    },
                    onEditingComplete: () {
                      final parsed = int.tryParse(_qtyController.text);
                      if (parsed != null && parsed >= 1) {
                        _setQuantity(parsed);
                      } else {
                        _qtyController.text = item.quantity.toString();
                      }
                      FocusScope.of(context).unfocus();
                    },
                  ),
                ),
                IconButton(
                  onPressed: canIncrement
                      ? () => _setQuantity(item.quantity + 1)
                      : null,
                  icon: const Icon(Icons.add_circle_outline),
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Remove',
                  onPressed: cart.isUpdating
                      ? null
                      : () => context.read<CartProvider>().removeFromCart(
                            cartItem: item,
                            authToken: widget.authToken,
                          ),
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
