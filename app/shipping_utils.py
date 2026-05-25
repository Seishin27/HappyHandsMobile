from __future__ import annotations

import re
from typing import Any, Mapping


DEFAULT_SHIPPING_FEE = 36.0
_SURCHARGE_PER_STEP = 18.0  # 50% of ₱36 added per region step of distance

# ---------------------------------------------------------------------------
# PSGC code → human-readable name lookup
# Sellers registered via the old form stored PSGC numeric codes.
# Buyers always store human-readable names (from the checkout address picker).
# This mapping lets us normalise both sides to names before comparing.
# ---------------------------------------------------------------------------
_PSGC_CODE_TO_NAME: dict[str, str] = {
    # Regions
    "010000000": "Ilocos Region",
    "020000000": "Cagayan Valley",
    "030000000": "Central Luzon",
    "040000000": "CALABARZON",
    "175000000": "MIMAROPA Region",
    "050000000": "Bicol Region",
    "060000000": "Western Visayas",
    "070000000": "Central Visayas",
    "080000000": "Eastern Visayas",
    "090000000": "Zamboanga Peninsula",
    "100000000": "Northern Mindanao",
    "110000000": "Davao Region",
    "120000000": "SOCCSKSARGEN",
    "130000000": "NCR",
    "140000000": "CAR",
    "160000000": "Caraga",
    "170000000": "BARMM",
    # Provinces (common ones)
    "012800000": "Ilocos Norte",
    "012900000": "Ilocos Sur",
    "013300000": "La Union",
    "015500000": "Pangasinan",
    "020900000": "Batanes",
    "021500000": "Cagayan",
    "023100000": "Isabela",
    "025000000": "Nueva Vizcaya",
    "026700000": "Quirino",
    "030800000": "Bataan",
    "031400000": "Bulacan",
    "034900000": "Nueva Ecija",
    "035400000": "Pampanga",
    "036900000": "Tarlac",
    "037100000": "Zambales",
    "037700000": "Aurora",
    "041000000": "Batangas",
    "042100000": "Cavite",
    "043400000": "Laguna",
    "045600000": "Quezon",
    "045800000": "Rizal",
    "174000000": "Marinduque",
    "175100000": "Occidental Mindoro",
    "175200000": "Oriental Mindoro",
    "175300000": "Palawan",
    "175900000": "Romblon",
    "050500000": "Albay",
    "051600000": "Camarines Norte",
    "051700000": "Camarines Sur",
    "052000000": "Catanduanes",
    "054100000": "Masbate",
    "056200000": "Sorsogon",
    "060400000": "Aklan",
    "060600000": "Antique",
    "061900000": "Capiz",
    "063000000": "Iloilo",
    "064500000": "Negros Occidental",
    "079700000": "Guimaras",
    "070300000": "Bohol",
    "072200000": "Cebu",
    "074600000": "Negros Oriental",
    "078000000": "Siquijor",
    "080800000": "Biliran",
    "081100000": "Eastern Samar",
    "082600000": "Leyte",
    "084800000": "Northern Samar",
    "086000000": "Samar",
    "086400000": "Southern Leyte",
    "097200000": "Zamboanga del Norte",
    "097300000": "Zamboanga del Sur",
    "098300000": "Zamboanga Sibugay",
    "100700000": "Bukidnon",
    "101800000": "Camiguin",
    "103500000": "Lanao del Norte",
    "104200000": "Misamis Occidental",
    "104300000": "Misamis Oriental",
    "112300000": "Davao de Oro",
    "112400000": "Davao del Norte",
    "112500000": "Davao del Sur",
    "118200000": "Davao Occidental",
    "118600000": "Davao Oriental",
    "124700000": "Cotabato",
    "126300000": "Sarangani",
    "126500000": "South Cotabato",
    "127900000": "Sultan Kudarat",
    "140100000": "Abra",
    "141100000": "Benguet",
    "142700000": "Ifugao",
    "143200000": "Kalinga",
    "144400000": "Mountain Province",
    "148100000": "Apayao",
    "160200000": "Agusan del Norte",
    "160300000": "Agusan del Sur",
    "166700000": "Dinagat Islands",
    "168500000": "Surigao del Norte",
    "168600000": "Surigao del Sur",
    # Cities / Municipalities (add as needed)
    "043430000": "Pinamalayan",
    "043413000": "Calapan City",
    "043413012": "Barangay 12",
    "043430004": "Inclanay",
}

# Regex to detect a PSGC-style numeric code (9+ digits, possibly with leading zeros)
_PSGC_CODE_RE = re.compile(r'^\d{9,}$')


def _resolve_psgc(value: str) -> str:
    """If value looks like a PSGC code, return the mapped name; otherwise return as-is."""
    clean = value.strip()
    if _PSGC_CODE_RE.match(clean):
        return _PSGC_CODE_TO_NAME.get(clean, clean)
    return clean


def normalize_location_value(value: Any) -> str:
    text = str(value or '').strip()
    # Resolve PSGC code to name first, then lowercase
    resolved = _resolve_psgc(text)
    return ' '.join(resolved.lower().split())


def build_location_key(location: Mapping[str, Any] | None) -> tuple[str, str, str, str]:
    location = location or {}
    return (
        normalize_location_value(location.get('region')),
        normalize_location_value(location.get('province')),
        normalize_location_value(location.get('city')),
        normalize_location_value(location.get('barangay')),
    )


# ---------------------------------------------------------------------------
# Region name → PSGC numeric prefix (two-digit int) for distance calculation.
# Built from _PSGC_CODE_TO_NAME at import time.
# MIMAROPA (175000000) uses prefix 17 → treated as region 17 in the sequence.
# NCR (130000000) uses prefix 13.
# ---------------------------------------------------------------------------
_REGION_NAME_TO_PREFIX: dict[str, int] = {}


def _build_region_prefix_map() -> dict[str, int]:
    result: dict[str, int] = {}
    for code, name in _PSGC_CODE_TO_NAME.items():
        # Only region-level codes: 9 digits, last 7 are zeros
        if len(code) == 9 and code[2:] == '0000000':
            try:
                prefix = int(code[:2])
                result[normalize_location_value(name)] = prefix
            except ValueError:
                pass
    return result


_REGION_NAME_TO_PREFIX.update(_build_region_prefix_map())

# PSGC API returns full region names; map them alongside the short abbreviations
# that may already be in _PSGC_CODE_TO_NAME. Also add MIMAROPA whose code
# (175000000) does not match the code[2:]=='0000000' filter so it is skipped by
# _build_region_prefix_map(); give it a distinct pseudo-prefix (15) so the
# distance formula still orders it correctly between region 14 and 16.
_REGION_NAME_TO_PREFIX.update({
    normalize_location_value('national capital region'): 13,
    normalize_location_value('national capital region (ncr)'): 13,
    normalize_location_value('cordillera administrative region'): 14,
    normalize_location_value('cordillera administrative region (car)'): 14,
    normalize_location_value('bangsamoro autonomous region in muslim mindanao'): 17,
    normalize_location_value('bangsamoro autonomous region in muslim mindanao (barmm)'): 17,
    normalize_location_value('bangsamoro'): 17,
    normalize_location_value('mimaropa'): 15,
    normalize_location_value('mimaropa region'): 15,
})


def _region_prefix_int(region_value: str) -> int | None:
    """
    Return the two-digit numeric prefix for a region.
    Accepts a PSGC code (any length) or a human-readable region name.
    Returns None if the region cannot be identified.
    """
    clean = str(region_value or '').strip()
    if not clean:
        return None

    # PSGC code: extract first two digits as the region prefix
    if _PSGC_CODE_RE.match(clean):
        try:
            return int(clean[:2])
        except ValueError:
            return None

    # Human-readable name: look up in the reverse map
    return _REGION_NAME_TO_PREFIX.get(normalize_location_value(clean))


def _region_distance(region_a: str, region_b: str) -> int | None:
    """
    Return the number of region steps between two regions using PSGC prefix difference.
    Returns None if either region cannot be identified (triggers 1-step fallback).
    """
    pa = _region_prefix_int(region_a)
    pb = _region_prefix_int(region_b)
    if pa is None or pb is None:
        return None
    return abs(pa - pb)


def estimate_shipping_fee(pickup_location: Mapping[str, Any] | None, delivery_location: Mapping[str, Any] | None) -> float:
    """
    Calculate shipping fee based on address proximity.

    Fee formula:
      - Same province:          ₱36  (base)
      - Cross-province:         ₱36 + N × ₱18
        where N = region distance (abs difference of PSGC region prefixes),
        minimum N=1 for any cross-province delivery.

    Examples:
      - Same province:                    ₱36
      - Neighbour region (diff=1):        ₱54
      - 2 regions apart (diff=2):         ₱72
      - 3 regions apart (diff=3):         ₱90
      - NCR (13) ↔ Davao (11), diff=2:   ₱72

    Falls back to N=1 (₱54) when region cannot be determined.
    Returns ₱36 when either address is missing/empty.
    """
    pickup = build_location_key(pickup_location)
    delivery = build_location_key(delivery_location)

    # Can't estimate without a delivery address
    if not any(delivery):
        return DEFAULT_SHIPPING_FEE

    p_region, p_province, p_city, _ = pickup
    d_region, d_province, d_city, _ = delivery

    # Same province → base fee (only when seller has province data to compare)
    if p_province and p_province == d_province:
        return DEFAULT_SHIPPING_FEE

    # Different province (or seller location unknown) → distance-based surcharge.
    # When seller has no region data, dist resolves to None → 1-step fallback (₱54).
    dist = _region_distance(p_region, d_region)
    if dist is None:
        dist = 1  # unknown region — conservative 1-step fallback (₱54)

    # Minimum 1 step for any cross-province delivery
    steps = max(dist, 1)
    return DEFAULT_SHIPPING_FEE + steps * _SURCHARGE_PER_STEP

