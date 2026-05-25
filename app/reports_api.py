"""
Flask blueprint exposing the sales / delivery PDF reports.

Web endpoints rely on Flask session auth (seller) or the existing
``admin_required`` / ``rider_required`` decorators in
``app.authentication``. Mobile endpoints use JWT, mirroring the pattern from
``app.mobile_api`` (claims contain a ``"seller"`` or ``"rider"`` dict whose
``sellerID`` / ``riderID`` identifies the caller).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask import Blueprint, Response, jsonify, redirect, request, session, url_for
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.reports import (
    ALLOWED_PERIODS,
    build_admin_sales_pdf,
    build_rider_deliveries_pdf,
    build_seller_sales_pdf,
)


reports_bp = Blueprint("reports", __name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _validated_period() -> Optional[str]:
    """Return the ``period`` query param if valid, else None (caller -> 400).

    Strict: missing, empty/whitespace, or unknown values all return ``None``.
    Callers are expected to pass an explicit ``?period=today|week|month``.
    """
    raw = request.args.get("period")
    if raw is None:
        return None
    period = raw.lower().strip()
    if not period or period not in ALLOWED_PERIODS:
        return None
    return period


def _bad_period():
    return jsonify({"success": False, "message": "Invalid period. Use today, week, or month."}), 400


def _pdf_response(pdf_bytes: bytes, filename: str) -> Response:
    resp = Response(pdf_bytes, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.headers["Content-Length"] = str(len(pdf_bytes))
    # PDFs include a timestamp in the header strip; discourage stale caches.
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _sales_filename(period: str) -> str:
    return f"happy-hands-sales-{period}-{datetime.utcnow().strftime('%Y%m%d')}.pdf"


def _deliveries_filename(period: str) -> str:
    return f"happy-hands-deliveries-{period}-{datetime.utcnow().strftime('%Y%m%d')}.pdf"


def _seller_id_from_session() -> Optional[int]:
    """Mirror the pattern used by /seller/dashboard."""
    seller = session.get("seller") or {}
    sid = seller.get("id") or seller.get("sellerID")
    if sid is None:
        return None
    try:
        return int(sid)
    except (TypeError, ValueError):
        return None


def _seller_id_from_jwt() -> Optional[int]:
    """Resolve the seller id from JWT claims (mobile login).

    Pattern mirrors ``app.mobile_api`` — claims include a ``"seller"`` dict
    with ``sellerID``, and the JWT identity falls back to ``str(seller_id)``.
    """
    try:
        claims = get_jwt() or {}
    except Exception:
        claims = {}
    seller_claim = claims.get("seller")
    if isinstance(seller_claim, dict):
        for key in ("sellerID", "sellerId", "seller_id", "id"):
            val = seller_claim.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    pass
    roles = claims.get("roles") or []
    if isinstance(roles, list) and "seller" in roles:
        try:
            identity = get_jwt_identity()
            return int(identity) if identity is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _rider_id_from_jwt() -> Optional[int]:
    """Resolve the rider id from JWT claims (mobile login)."""
    try:
        claims = get_jwt() or {}
    except Exception:
        claims = {}
    rider_claim = claims.get("rider")
    if isinstance(rider_claim, dict):
        for key in ("riderID", "riderId", "rider_id", "id"):
            val = rider_claim.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    pass
    roles = claims.get("roles") or []
    if isinstance(roles, list) and "rider" in roles:
        try:
            identity = get_jwt_identity()
            return int(identity) if identity is not None else None
        except (TypeError, ValueError):
            return None
    return None


# ---------------------------------------------------------------------------
# Web (session) endpoints
# ---------------------------------------------------------------------------
@reports_bp.get("/seller/reports/sales.pdf")
def seller_sales_pdf():
    """Per-seller sales report — Flask session auth."""
    seller_id = _seller_id_from_session()
    if not seller_id:
        # Match the seller_dashboard redirect-on-no-session behaviour.
        try:
            return redirect(url_for("seller_login"))
        except Exception:
            return Response("Unauthorized", status=401)

    period = _validated_period()
    if period is None:
        return _bad_period()

    pdf_bytes = build_seller_sales_pdf(seller_id, period)
    return _pdf_response(pdf_bytes, _sales_filename(period))


@reports_bp.get("/admin/reports/sales.pdf")
def admin_sales_pdf():
    """Platform sales report — admin only."""
    # Late import to avoid an import cycle: authentication imports this blueprint.
    from app.authentication import admin_required

    if not admin_required():
        try:
            return redirect(url_for("login"))
        except Exception:
            return Response("Unauthorized", status=401)

    period = _validated_period()
    if period is None:
        return _bad_period()

    pdf_bytes = build_admin_sales_pdf(period)
    return _pdf_response(pdf_bytes, _sales_filename(period))


@reports_bp.get("/rider/reports/deliveries.pdf")
def rider_deliveries_pdf():
    """Per-rider deliveries report — rider session auth."""
    from app.authentication import rider_required, _get_rider_id_from_session

    if not rider_required():
        try:
            return redirect(url_for("rider_login"))
        except Exception:
            return Response("Unauthorized", status=401)

    rider_id = _get_rider_id_from_session()
    if not rider_id:
        return Response("Unauthorized", status=401)

    period = _validated_period()
    if period is None:
        return _bad_period()

    pdf_bytes = build_rider_deliveries_pdf(rider_id, period)
    return _pdf_response(pdf_bytes, _deliveries_filename(period))


# ---------------------------------------------------------------------------
# Mobile (JWT) endpoints
# ---------------------------------------------------------------------------
@reports_bp.get("/api/mobile/seller/reports/sales.pdf")
@jwt_required()
def mobile_seller_sales_pdf():
    seller_id = _seller_id_from_jwt()
    if not seller_id:
        return jsonify({"success": False, "message": "Seller authentication required"}), 401

    period = _validated_period()
    if period is None:
        return _bad_period()

    pdf_bytes = build_seller_sales_pdf(seller_id, period)
    return _pdf_response(pdf_bytes, _sales_filename(period))


@reports_bp.get("/api/mobile/rider/reports/deliveries.pdf")
@jwt_required()
def mobile_rider_deliveries_pdf():
    rider_id = _rider_id_from_jwt()
    if not rider_id:
        return jsonify({"success": False, "message": "Rider authentication required"}), 401

    period = _validated_period()
    if period is None:
        return _bad_period()

    pdf_bytes = build_rider_deliveries_pdf(rider_id, period)
    return _pdf_response(pdf_bytes, _deliveries_filename(period))
