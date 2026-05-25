String formatMoney(double value) {
  // Keep it simple for prototype; swap to intl later if needed.
  return '₱${value.toStringAsFixed(2)}';
}

