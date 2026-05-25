import 'package:flutter/foundation.dart'
    show kIsWeb, defaultTargetPlatform, TargetPlatform;

import '../models/product.dart';

/// Static mock products copied from the Happy Hands database.
/// Images reference the Flask backend's /uploads/ path.
class MockProducts {
  static String get _base {
    // Strip /api suffix from API_BASE_URL to get the server root, then append /uploads
    const apiUrl = String.fromEnvironment('API_BASE_URL');
    if (apiUrl.isNotEmpty) {
      final root = apiUrl.replaceAll(RegExp(r'/api/?$'), '');
      return '$root/uploads';
    }
    if (kIsWeb) return 'http://127.0.0.1:5500/uploads';
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5500/uploads';
    }
    return 'http://127.0.0.1:5500/uploads';
  }

  // ── Baby Clothes & Accessories ──────────────────────────────────────────
  static Product get babyCardigan => Product(
        id: 45,
        name: 'Soft Knit Baby Cardigan',
        price: 349.00,
        description: 'A cozy, soft-knit cardigan perfect for newborns and infants. '
            'Made from 100% organic cotton, gentle on delicate skin.',
        stock: 25,
        category: 'baby-clothes',
        imageUrls: [
          '$_base/prod_45_198f2529f68044bfac6d786d0a41a2a7_Baby_Cardigan.webp',
          '$_base/prod_45_618c3e6b3c784cf18c965172a0a5a0b6_Baby_Cardigan.webp',
          '$_base/prod_45_b3d9e9efa82c4825af697003b5a68310_Baby_Cardigan.webp',
        ],
      );

  static Product get babyRomper => Product(
        id: 46,
        name: 'Floral Baby Romper',
        price: 299.00,
        description: 'Adorable floral-print romper with snap buttons for easy dressing. '
            'Breathable fabric keeps baby comfortable all day.',
        stock: 30,
        category: 'baby-clothes',
        imageUrls: [
          '$_base/prod_45_24de85365e434d3b8d0365c0f883e67b_Baby_Romper.webp',
          '$_base/prod_45_b5484dc4235444df8f236c319364f2b8_Baby_Romper.webp',
        ],
      );

  static Product get babyPajama => Product(
        id: 47,
        name: 'Cozy Baby Pajama Set',
        price: 399.00,
        description: 'Two-piece pajama set with long sleeves and footed pants. '
            'Super soft fleece keeps your little one warm through the night.',
        stock: 20,
        category: 'baby-clothes',
        imageUrls: [
          '$_base/prod_45_77ac5685494a4fe1a3f598335212872d_Baby_Pajama.webp',
          '$_base/prod_45_d48279a2778b4baa8539383d52bdcac1_Baby_Pajama.webp',
        ],
      );

  static Product get babyBodysuit => Product(
        id: 48,
        name: 'Short-Sleeve Bodysuit 3-Pack',
        price: 450.00,
        description: 'Set of 3 short-sleeve bodysuits in assorted pastel colors. '
            'Envelope neckline for easy on/off. Machine washable.',
        stock: 40,
        category: 'baby-clothes',
        imageUrls: [
          '$_base/prod_45_101a1a3f87ab451494d78d9ae7587c11_Shortsleeve_Bodysuit.webp',
          '$_base/prod_45_7df0b2b7a20640cfbbc4685be1249c53_Shortsleeve_Bodysuit.webp',
          '$_base/prod_45_fe0ac357160b4e39853f65a5cf79c7ea_Shortsleeve_Bodysuit.webp',
        ],
      );

  static Product get babyTrousers => Product(
        id: 49,
        name: 'Elastic-Waist Baby Trousers',
        price: 249.00,
        description: 'Comfortable pull-on trousers with a soft elastic waistband. '
            'Available in neutral tones, pairs with any top.',
        stock: 35,
        category: 'baby-clothes',
        imageUrls: [
          '$_base/prod_45_64ebd153eef640e891aed97142c4a3f5_Baby_Trousers.jpg',
          '$_base/prod_64_48b5af3e83304b53967d1e43010d1f14_Baby_Trousers.jpg',
        ],
      );

  // ── Comfort Toys ────────────────────────────────────────────────────────
  static Product get turtleRattle => Product(
        id: 37,
        name: 'Turtle Rattle Toy',
        price: 199.00,
        description: 'Soft plush turtle rattle with gentle sound. Safe for newborns, '
            'BPA-free and machine washable. Stimulates sensory development.',
        stock: 50,
        category: 'comfort-toys',
        imageUrls: [
          '$_base/prod_45_864b60cd9201429f97a5d3f0e375ec47_Turtle_Rattle.webp',
          '$_base/prod_45_b55e0e70244242289575105266f11196_Turtle_Rattle.webp',
        ],
      );

  static Product get pullToy => Product(
        id: 38,
        name: 'Wooden Pull-Along Toy',
        price: 349.00,
        description: 'Classic wooden pull-along toy that encourages walking and motor '
            'skills. Non-toxic paint, smooth edges, safe for toddlers.',
        stock: 18,
        category: 'comfort-toys',
        imageUrls: [
          '$_base/prod_37_db3d002513a04b1681f8bb026728baf1_Pull_Toy.webp',
        ],
      );

  static Product get musicalApple => Product(
        id: 39,
        name: 'Musical Apple Toy',
        price: 279.00,
        description: 'Press the button to hear cheerful melodies! Bright colors and '
            'fun sounds keep babies entertained and engaged.',
        stock: 22,
        category: 'comfort-toys',
        imageUrls: [
          '$_base/prod_37_ee053f854400434faea00beb095928e2_Musical_Apple_Toy.webp',
        ],
      );

  static Product get rockingMoose => Product(
        id: 40,
        name: 'Rocking Moose Plush',
        price: 599.00,
        description: 'Adorable plush rocking moose with a gentle rocking motion. '
            'Perfect for toddlers 12 months and up. Soft and huggable.',
        stock: 12,
        category: 'comfort-toys',
        imageUrls: [
          '$_base/prod_37_f935709f08e04a07854fa7d7d29d2e29_Rocking_Moose.webp',
        ],
      );

  static Product get frogRattle => Product(
        id: 41,
        name: 'Frog Rattle Teether',
        price: 149.00,
        description: 'Dual-purpose frog rattle and teether. Soft silicone teething '
            'ring soothes sore gums while the rattle entertains.',
        stock: 45,
        category: 'comfort-toys',
        imageUrls: [
          '$_base/prod_37_0ecf138476184965b6c5ac7b84d1871d_Frog_rattle.webp',
        ],
      );

  // ── Educational Toys ────────────────────────────────────────────────────
  static Product get pusheenicornPlush => Product(
        id: 73,
        name: 'Pusheenicorn Soft Plush Toy',
        price: 499.00,
        description: 'Super soft Pusheenicorn stuffed toy. Great for imaginative play '
            'and cuddling. Suitable for ages 3 months and up.',
        stock: 15,
        category: 'educational-toys',
        imageUrls: [
          '$_base/prod_73_009e119efe04442aaca9c28c2bf77894_WK12_Pusheenicorn_13_1_161611740433.webp',
          '$_base/prod_73_3de43b01720247d482302f69b8e86061_WK12_Pusheenicorn_13_3_161611740444.webp',
          '$_base/prod_73_a4a98a5ed76c4a1ca93eb5e41abbde5c_WK12_Pusheenicorn_13_2_161611740448.webp',
        ],
      );

  static Product get educationalStencil => Product(
        id: 74,
        name: 'Educational Stencil Set',
        price: 329.00,
        description: 'Magic whiteboard stencil set with 20 reusable stencils. '
            'Encourages creativity, fine motor skills, and early learning.',
        stock: 28,
        category: 'educational-toys',
        imageUrls: [
          '$_base/prod_73_5810a3b4e33c4398ababd9aa1b0ed4a0_Educational_Stencil_Set_for_Magic_W.webp',
          '$_base/prod_73_a6832d85ed664be09906b14f06370150_Educational_Stencil_Set_for_Magic_W.webp',
          '$_base/prod_73_bfc90be1eff44780914fd48fbb537338_Educational_Stencil_Set_for_Magic_W.webp',
        ],
      );

  static Product get kaiBearPlush => Product(
        id: 75,
        name: 'Kai Bear Soft Plush Toy',
        price: 449.00,
        description: 'Cuddly Kai Bear plush toy, perfect for bedtime comfort. '
            'Hypoallergenic filling, machine washable cover.',
        stock: 20,
        category: 'educational-toys',
        imageUrls: [
          '$_base/prod_73_85347552339b46e4aa2af987378d9819_WK12_Kai_12_Bear_Soft_Plus_Toy_1_16.webp',
          '$_base/prod_73_1c49bc6a2c5f49ee8924923e929468b5_WK12_Kai_12_Bear_Soft_Plus_Toy_3_16.webp',
          '$_base/prod_73_f47ce5393d0c41c087134a0145191f3b_WK12_Kai_12_Bear_Soft_Plus_Toy_2_16.webp',
        ],
      );

  // ── Nursery Furniture ───────────────────────────────────────────────────
  static Product get babyCrib => Product(
        id: 71,
        name: 'Convertible Baby Crib',
        price: 4999.00,
        description: 'Solid wood convertible crib that grows with your child. '
            'Converts from crib to toddler bed. JPMA certified, lead-free finish.',
        stock: 8,
        category: 'nursery-furniture',
        imageUrls: [
          '$_base/prod_71_cb3ea86ebf814f059b594df0708c0510_crib1.webp',
          '$_base/prod_71_5826d5902c7c4f899e71b3b0bd23b901_crib2.webp',
          '$_base/prod_71_bf84fa64e14c4611b12385532292411f_crib3.webp',
          '$_base/prod_71_a90b55f987384f86914c52f9c2d4c015_crib4.webp',
        ],
      );

  static Product get highChair => Product(
        id: 72,
        name: 'Adjustable High Chair',
        price: 2499.00,
        description: 'Multi-position adjustable high chair with removable tray. '
            'Easy to clean, folds flat for storage. Suitable from 6 months.',
        stock: 10,
        category: 'nursery-furniture',
        imageUrls: [
          '$_base/prod_71_c39c2b19dce246f89ca1e8f5435af14f_highchair11.jpg',
          '$_base/prod_71_76ab97d985e849acb175fa3a4dc75368_highchair2.jpg',
          '$_base/prod_71_8bd5178aab504bd6bfcd520485c2c678_highchair3.jpg',
          '$_base/prod_71_797f70fd260b47788edf4cc8eb2f45d7_highchair4.jpg',
        ],
      );

  // ── Strollers & Gear ────────────────────────────────────────────────────
  static Product get babyStroller => Product(
        id: 23,
        name: 'UPPAbaby Vista Stroller',
        price: 12999.00,
        description: 'Premium full-size stroller with reversible seat, large storage '
            'basket, and all-terrain wheels. Suitable from birth.',
        stock: 5,
        category: 'stroller-gear',
        imageUrls: [
          '$_base/prod_23_0044fbb49ee84f3ba9e868d4f5d16100_uppababy-vista-mesa-stroller-car-se.webp',
          '$_base/prod_23_16d931172d614672a0061175afe7bb22_uppababy-vista-mesa-stroller-car-se.webp',
        ],
      );

  static Product get babyWalker => Product(
        id: 24,
        name: 'Baby Activity Walker',
        price: 1299.00,
        description: 'Interactive baby walker with activity panel, music, and lights. '
            'Adjustable speed resistance, non-slip base for safety.',
        stock: 14,
        category: 'stroller-gear',
        imageUrls: [
          '$_base/prod_23_07ad6f1755424d5ea703c6f67bcc5080_Baby-Walker.webp',
          '$_base/prod_23_6478a3ae171345bb84594f395285b756_Baby-Walkers-for-1-2-years.webp',
          '$_base/prod_23_d7b17683edd4469b92c51cddefbd77be_Baby-Walker.webp',
        ],
      );

  static Product get doubleStroller => Product(
        id: 33,
        name: 'Double Tandem Stroller',
        price: 8999.00,
        description: 'Spacious tandem double stroller for two children. '
            'Individual reclining seats, large canopies, and easy fold.',
        stock: 4,
        category: 'stroller-gear',
        imageUrls: [
          '$_base/prod_33_047175ff548b460fb0a1e0dce7d3840a_uppababy-vista-2015-double-stroller.webp',
        ],
      );

  // ── Safety & Health ─────────────────────────────────────────────────────
  static Product get cornerGuards => Product(
        id: 68,
        name: 'Corner & Edge Guard Set',
        price: 199.00,
        description: '20-piece corner and edge guard set. Self-adhesive, soft foam '
            'protects babies from sharp furniture corners. Easy to install.',
        stock: 60,
        category: 'safety-and-health',
        imageUrls: [
          '$_base/prod_68_c6bf540912164e33955e7f0ffe7df320_cornerrrrr.jpg',
          '$_base/prod_68_187ee7b54ed34472a9834756e2ed4371_corneyb.jpg',
          '$_base/prod_68_5dda427a7129495ebc1adc3f5e1f1ff2_corneybb.jpg',
          '$_base/prod_68_cd43376c22114b93b729db0de1aed27d_cornerbbb.jpg',
        ],
      );

  static Product get safetyPlugs => Product(
        id: 69,
        name: 'Electrical Outlet Safety Plugs',
        price: 149.00,
        description: '12-pack outlet safety plugs. Childproof design prevents '
            'accidental insertion. Fits standard outlets.',
        stock: 80,
        category: 'safety-and-health',
        imageUrls: [
          '$_base/prod_68_6655c39f3df14f98adcbeb55ad0ebcb0_safetyplug2.jpg',
          '$_base/prod_68_676447b59e23409f94db03035a50a8cd_safertyplug3.jpg',
          '$_base/prod_68_f8662cc97cba4300b90e0b11df755431_safetyplug1.jpg',
        ],
      );

  static Product get bedRail => Product(
        id: 76,
        name: 'Toddler Bed Safety Rail',
        price: 899.00,
        description: 'Foldable bed safety rail prevents toddlers from rolling out. '
            'Fits most standard and queen beds. Easy fold for adult access.',
        stock: 16,
        category: 'safety-and-health',
        imageUrls: [
          '$_base/prod_74_27c46e9e96b1425ca4119f4f14045a53_CHOC-CHICK-BED-RAIL-2-2_16009617922.webp',
          '$_base/prod_74_f71746b11da14f28b0bf4cf7944bf179_bed-rail-grey-200cm_1600961792242.webp',
          '$_base/prod_74_60e7d13cc7e74f42be1c25b8bf3d8b87_bedrailconnector_1600961792264.webp',
        ],
      );

  static Product get safetyGate => Product(
        id: 77,
        name: 'Pressure-Mounted Safety Gate',
        price: 1199.00,
        description: 'Easy-install pressure-mounted safety gate for stairs and doorways. '
            'One-hand operation, fits openings 60–90 cm wide.',
        stock: 9,
        category: 'safety-and-health',
        imageUrls: [
          '$_base/prod_74_ef551d9f7c15499baf0f6e519d9f2222_safety_gate_desc.png_1736777236050.webp',
          '$_base/prod_74_8c4e9e677d054c28b099cbee145cb1e3_edge_grey1_1626080989683.webp',
        ],
      );

  // ── Lists ────────────────────────────────────────────────────────────────
  static List<Product> get all => [
        babyCardigan,
        babyRomper,
        babyPajama,
        babyBodysuit,
        babyTrousers,
        turtleRattle,
        pullToy,
        musicalApple,
        rockingMoose,
        frogRattle,
        pusheenicornPlush,
        educationalStencil,
        kaiBearPlush,
        babyCrib,
        highChair,
        babyStroller,
        babyWalker,
        doubleStroller,
        cornerGuards,
        safetyPlugs,
        bedRail,
        safetyGate,
      ];

  static List<Product> get featured => [
        babyCardigan,
        turtleRattle,
        babyCrib,
        babyStroller,
        pusheenicornPlush,
        cornerGuards,
        babyRomper,
        musicalApple,
      ];

  static List<Product> byCategory(String slug) =>
      all.where((p) => p.category == slug).toList();
}
