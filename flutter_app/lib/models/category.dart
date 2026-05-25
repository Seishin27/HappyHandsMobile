class Category {
  final String slug;
  final String name;

  const Category({required this.slug, required this.name});

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      slug: (json['slug'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
    );
  }
}

