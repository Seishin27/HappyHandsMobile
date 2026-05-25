"""
PDF report generation for Happy Hands.

Three public builders, each returning a ``bytes`` payload suitable for a Flask
``send_file`` / ``Response`` body:

* :func:`build_seller_sales_pdf`   — per-seller sales report
* :func:`build_admin_sales_pdf`    — platform-wide sales / commission report
* :func:`build_rider_deliveries_pdf` — per-rider completed deliveries

All currency is rendered as ``PHP 1,234.56`` because ReportLab's bundled
Helvetica font does not contain the Philippine peso glyph (``₱``).

The module is intentionally self-contained: it only depends on ``reportlab``
and ``app.db.get_db`` so the same builders can run from either the web
session-authenticated routes or the mobile JWT routes.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple

import mysql.connector

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db import get_db as _get_db_connection


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
BRAND_BLUE = colors.HexColor("#1976D2")
BRAND_BLUE_DARK = colors.HexColor("#0D47A1")
ROW_STRIPE = colors.HexColor("#F5F7FA")
TEXT_MUTED = colors.HexColor("#555555")
CARD_BG = colors.HexColor("#EAF2FB")

ALLOWED_PERIODS = ("today", "week", "month")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _money(value) -> str:
    """Format a number as ``PHP 1,234.56`` (Helvetica lacks the ₱ glyph)."""
    try:
        return f"PHP {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "PHP 0.00"


def _period_range(period: str) -> Tuple[datetime, datetime, str]:
    """Convert a period keyword to ``(start_dt, end_dt, human_label)``.

    Periods are UTC and inclusive of "today" through end-of-day.
    """
    period = (period or "today").lower().strip()
    if period not in ALLOWED_PERIODS:
        period = "today"

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)

    if period == "today":
        start = today_start
        end = today_end
        label = f"Today — {today_start.strftime('%b %d, %Y')}"
    elif period == "week":
        start = today_start - timedelta(days=6)
        end = today_end
        label = (
            f"Last 7 Days — {start.strftime('%b %d, %Y')} "
            f"to {today_start.strftime('%b %d, %Y')}"
        )
    else:  # month
        start = today_start - timedelta(days=29)
        end = today_end
        label = (
            f"Last 30 Days — {start.strftime('%b %d, %Y')} "
            f"to {today_start.strftime('%b %d, %Y')}"
        )

    return start, end, label


def _styles():
    """Return cached paragraph styles."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "HH_Title",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=BRAND_BLUE_DARK,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "HH_Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=TEXT_MUTED,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "HH_Section",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=BRAND_BLUE_DARK,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "HH_Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
        ),
        "muted": ParagraphStyle(
            "HH_Muted",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=10,
            leading=13,
            textColor=TEXT_MUTED,
        ),
        "card_label": ParagraphStyle(
            "HH_CardLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=TEXT_MUTED,
        ),
        "card_value": ParagraphStyle(
            "HH_CardValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=BRAND_BLUE_DARK,
        ),
    }


def _pdf_header(canvas, doc, title: str, subtitle: str) -> None:
    """Draw the Happy Hands brand strip + title + subtitle on a page."""
    canvas.saveState()
    width, height = A4
    # Brand strip
    canvas.setFillColor(BRAND_BLUE)
    canvas.rect(0, height - 14 * mm, width, 14 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(15 * mm, height - 9.5 * mm, "Happy Hands")
    canvas.setFont("Helvetica", 9)
    generated_label = "Generated " + datetime.utcnow().strftime("%b %d, %Y %H:%M UTC")
    canvas.drawRightString(width - 15 * mm, height - 9.5 * mm, generated_label)

    # Title block under the strip
    canvas.setFillColor(BRAND_BLUE_DARK)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(15 * mm, height - 24 * mm, title)
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(15 * mm, height - 30 * mm, subtitle)

    canvas.restoreState()


def _pdf_footer(canvas, doc) -> None:
    """Draw a page number + tagline at the bottom of each page."""
    canvas.saveState()
    width, _ = A4
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(15 * mm, 10 * mm, "Generated by Happy Hands")
    canvas.drawRightString(width - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _make_doc(buf: io.BytesIO) -> SimpleDocTemplate:
    """Build a doc template with consistent margins."""
    return SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        # Top margin must clear the brand strip + title block.
        topMargin=36 * mm,
        bottomMargin=18 * mm,
        title="Happy Hands Report",
        author="Happy Hands",
    )


def _summary_row(items: Sequence[Tuple[str, str]]):
    """Return a 2x2 KPI card grid.

    ``items`` is a sequence of ``(label, value)`` tuples. Anything beyond four
    items is ignored. Missing slots are padded with blank cards.
    """
    s = _styles()
    cards: List[List[Paragraph]] = []
    pairs = list(items)[:4]
    while len(pairs) < 4:
        pairs.append(("", ""))

    def _cell(label: str, value: str):
        return [
            Paragraph(label or "&nbsp;", s["card_label"]),
            Spacer(1, 2),
            Paragraph(value or "&nbsp;", s["card_value"]),
        ]

    # 2 rows x 2 cols
    grid = [
        [_cell(*pairs[0]), _cell(*pairs[1])],
        [_cell(*pairs[2]), _cell(*pairs[3])],
    ]
    col_width = (A4[0] - 30 * mm) / 2
    tbl = Table(grid, colWidths=[col_width, col_width])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tbl


def _data_table(headers: Sequence[str], rows: Sequence[Sequence[str]], col_widths=None):
    """Striped table with brand-blue header band."""
    s = _styles()
    if not rows:
        return Paragraph("No data for this period.", s["muted"])

    # Convert all cells to Paragraphs so long text wraps cleanly.
    body_style = s["body"]
    header_style = ParagraphStyle(
        "HH_TableHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    table_data = [[Paragraph(str(h), header_style) for h in headers]]
    for r in rows:
        table_data.append([Paragraph(str(c) if c is not None else "", body_style) for c in r])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_BLUE_DARK),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.lightgrey),
        ]
    )
    # Zebra-stripe body rows.
    for idx in range(1, len(table_data)):
        if idx % 2 == 0:
            style.add("BACKGROUND", (0, idx), (-1, idx), ROW_STRIPE)
    tbl.setStyle(style)
    return tbl


def _render(
    title: str,
    subtitle: str,
    story: List,
) -> bytes:
    """Build a PDF from a story list and return the raw bytes."""
    buf = io.BytesIO()
    doc = _make_doc(buf)

    def _on_page(canvas, doc_):
        _pdf_header(canvas, doc_, title, subtitle)
        _pdf_footer(canvas, doc_)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def _error_pdf(title: str, subtitle: str, message: str) -> bytes:
    """Render a fallback PDF when a DB query fails."""
    s = _styles()
    story = [
        Paragraph(message, s["muted"]),
    ]
    return _render(title, subtitle, story)


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------
def build_seller_sales_pdf(seller_id: int, period: str) -> bytes:
    """Render the per-seller sales report as a PDF (bytes)."""
    start, end, label = _period_range(period)
    s = _styles()

    storename = f"Seller #{seller_id}"
    summary_items: List[Tuple[str, str]] = []
    table_rows: List[List[str]] = []
    fallback_msg: Optional[str] = None

    conn = None
    cur = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Resolve store name
        try:
            cur.execute(
                "SELECT storename, sellername FROM sellers WHERE sellerID = %s LIMIT 1",
                (seller_id,),
            )
            row = cur.fetchone() or {}
            storename = (
                row.get("storename")
                or row.get("sellername")
                or f"Seller #{seller_id}"
            )
        except mysql.connector.Error:
            logger.exception("Failed to load seller %s", seller_id)

        # Itemised orders + items count + total
        cur.execute(
            """
            SELECT
                so.sellerOrderID,
                so.order_number,
                so.created_at,
                so.status,
                so.total_amount,
                COALESCE(u.username, 'Customer') AS customer_name,
                COALESCE(SUM(soi.quantity), 0) AS items_count
            FROM seller_orders so
            LEFT JOIN seller_order_items soi
                ON so.sellerOrderID = soi.sellerOrderID
            LEFT JOIN users u ON so.userID = u.userID
            WHERE so.sellerID = %s
              AND so.created_at >= %s
              AND so.created_at < %s
            GROUP BY so.sellerOrderID
            ORDER BY so.created_at DESC
            """,
            (seller_id, start, end),
        )
        orders = cur.fetchall() or []

        total_revenue = 0.0
        for o in orders:
            try:
                total_revenue += float(o.get("total_amount") or 0)
            except (TypeError, ValueError):
                pass
            order_no = o.get("order_number") or f"#{o.get('sellerOrderID')}"
            created = o.get("created_at")
            created_s = (
                created.strftime("%Y-%m-%d %H:%M") if isinstance(created, datetime) else str(created or "")
            )
            table_rows.append(
                [
                    str(order_no),
                    created_s,
                    str(o.get("customer_name") or ""),
                    str(int(o.get("items_count") or 0)),
                    str(o.get("status") or ""),
                    _money(o.get("total_amount")),
                ]
            )

        total_orders = len(orders)
        avg_order = (total_revenue / total_orders) if total_orders else 0.0

        # Top product (by quantity) for this seller in window
        top_product = "—"
        try:
            cur.execute(
                """
                SELECT p.name AS pname, SUM(soi.quantity) AS qty
                FROM seller_order_items soi
                JOIN seller_orders so ON so.sellerOrderID = soi.sellerOrderID
                LEFT JOIN products p ON p.productID = soi.productID
                WHERE so.sellerID = %s
                  AND so.created_at >= %s
                  AND so.created_at < %s
                GROUP BY soi.productID
                ORDER BY qty DESC
                LIMIT 1
                """,
                (seller_id, start, end),
            )
            tp = cur.fetchone()
            if tp and tp.get("pname"):
                top_product = f"{tp['pname']} ({int(tp.get('qty') or 0)})"
        except mysql.connector.Error:
            logger.exception("Top product lookup failed for seller %s", seller_id)

        summary_items = [
            ("Total Revenue", _money(total_revenue)),
            ("Total Orders", str(total_orders)),
            ("Average Order Value", _money(avg_order)),
            ("Top Product", top_product),
        ]
    except mysql.connector.Error as e:
        logger.exception("Seller sales PDF DB error: %s", e)
        fallback_msg = "Unable to load data at this time. Please try again later."
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    title = f"Sales Report — {storename}"
    if fallback_msg:
        return _error_pdf(title, label, fallback_msg)

    story = [
        _summary_row(summary_items),
        Spacer(1, 10),
        Paragraph("Orders in this period", s["section"]),
        _data_table(
            ["Order #", "Date", "Customer", "Items", "Status", "Total"],
            table_rows,
            col_widths=[28 * mm, 30 * mm, 36 * mm, 14 * mm, 24 * mm, 28 * mm],
        ),
    ]
    return _render(title, label, story)


def build_admin_sales_pdf(period: str) -> bytes:
    """Render the platform-wide sales / commission report as a PDF (bytes)."""
    start, end, label = _period_range(period)
    s = _styles()

    summary_items: List[Tuple[str, str]] = []
    top_sellers_rows: List[List[str]] = []
    fallback_msg: Optional[str] = None

    conn = None
    cur = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Aggregate platform totals from financial_transactions
        cur.execute(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS gross,
                COALESCE(SUM(admin_share), 0)  AS admin_share,
                COUNT(*) AS tx_count,
                COUNT(DISTINCT seller_id) AS active_sellers
            FROM financial_transactions
            WHERE created_at >= %s AND created_at < %s
            """,
            (start, end),
        )
        agg = cur.fetchone() or {}
        gross_revenue = float(agg.get("gross") or 0)
        admin_share = float(agg.get("admin_share") or 0)
        active_sellers = int(agg.get("active_sellers") or 0)

        # Delivered orders in window (from seller_orders, by updated_at)
        delivered_orders = 0
        try:
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM seller_orders
                WHERE LOWER(IFNULL(status, '')) = 'delivered'
                  AND updated_at >= %s AND updated_at < %s
                """,
                (start, end),
            )
            row = cur.fetchone() or {}
            delivered_orders = int(row.get("c") or 0)
        except mysql.connector.Error:
            logger.exception("Delivered-orders count failed")

        summary_items = [
            ("Total Platform Revenue", _money(gross_revenue)),
            ("Admin Share", _money(admin_share)),
            ("Delivered Orders", str(delivered_orders)),
            ("Active Sellers", str(active_sellers)),
        ]

        # Top 10 sellers by gross revenue in the window
        cur.execute(
            """
            SELECT
                ft.seller_id,
                COALESCE(s.storename, s.sellername, CONCAT('Seller #', ft.seller_id)) AS seller_label,
                COUNT(*)                              AS order_count,
                COALESCE(SUM(ft.total_amount), 0)     AS gross,
                COALESCE(SUM(ft.admin_share), 0)      AS admin_share
            FROM financial_transactions ft
            LEFT JOIN sellers s ON s.sellerID = ft.seller_id
            WHERE ft.created_at >= %s AND ft.created_at < %s
            GROUP BY ft.seller_id
            ORDER BY gross DESC
            LIMIT 10
            """,
            (start, end),
        )
        for r in cur.fetchall() or []:
            top_sellers_rows.append(
                [
                    str(r.get("seller_label") or ""),
                    str(int(r.get("order_count") or 0)),
                    _money(r.get("gross")),
                    _money(r.get("admin_share")),
                ]
            )
    except mysql.connector.Error as e:
        logger.exception("Admin sales PDF DB error: %s", e)
        fallback_msg = "Unable to load data at this time. Please try again later."
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    title = "Platform Sales Report"
    if fallback_msg:
        return _error_pdf(title, label, fallback_msg)

    story = [
        _summary_row(summary_items),
        Spacer(1, 10),
        Paragraph("Top sellers in this period", s["section"]),
        _data_table(
            ["Seller", "Orders", "Gross Revenue", "Admin Share"],
            top_sellers_rows,
            col_widths=[72 * mm, 22 * mm, 42 * mm, 42 * mm],
        ),
    ]
    return _render(title, label, story)


def build_rider_deliveries_pdf(rider_id: int, period: str) -> bytes:
    """Render the per-rider deliveries report as a PDF (bytes)."""
    start, end, label = _period_range(period)
    s = _styles()

    rider_name = f"Rider #{rider_id}"
    summary_items: List[Tuple[str, str]] = []
    table_rows: List[List[str]] = []
    fallback_msg: Optional[str] = None

    conn = None
    cur = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor(dictionary=True)

        # Resolve rider name
        try:
            cur.execute(
                "SELECT ridername FROM riders WHERE riderID = %s LIMIT 1",
                (rider_id,),
            )
            row = cur.fetchone() or {}
            rider_name = row.get("ridername") or rider_name
        except mysql.connector.Error:
            logger.exception("Failed to load rider %s", rider_id)

        # Completed deliveries in window
        cur.execute(
            """
            SELECT
                so.sellerOrderID,
                so.order_number,
                so.updated_at AS completed_at,
                so.total_amount,
                COALESCE(u.username, 'Customer') AS customer_name,
                COALESCE(s.storename, s.sellername, 'Store') AS store_name,
                COALESCE(ft.rider_commission, 0) AS rider_earnings
            FROM seller_orders so
            LEFT JOIN users   u ON so.userID   = u.userID
            LEFT JOIN sellers s ON so.sellerID = s.sellerID
            LEFT JOIN financial_transactions ft ON ft.order_id = so.sellerOrderID
            WHERE so.riderID = %s
              AND LOWER(IFNULL(so.status, '')) = 'delivered'
              AND so.updated_at >= %s
              AND so.updated_at < %s
            ORDER BY so.updated_at DESC
            """,
            (rider_id, start, end),
        )
        rows = cur.fetchall() or []

        total_earnings = 0.0
        per_day_counts = {}
        for r in rows:
            try:
                total_earnings += float(r.get("rider_earnings") or 0)
            except (TypeError, ValueError):
                pass
            completed = r.get("completed_at")
            completed_s = (
                completed.strftime("%Y-%m-%d %H:%M")
                if isinstance(completed, datetime)
                else str(completed or "")
            )
            if isinstance(completed, datetime):
                day_key = completed.strftime("%a %b %d")
                per_day_counts[day_key] = per_day_counts.get(day_key, 0) + 1

            table_rows.append(
                [
                    str(r.get("order_number") or f"#{r.get('sellerOrderID')}"),
                    completed_s,
                    str(r.get("customer_name") or ""),
                    str(r.get("store_name") or ""),
                    _money(r.get("rider_earnings")),
                ]
            )

        total_deliveries = len(rows)
        avg_per = (total_earnings / total_deliveries) if total_deliveries else 0.0
        if per_day_counts:
            most_active_day = max(per_day_counts.items(), key=lambda kv: kv[1])
            most_active_label = f"{most_active_day[0]} ({most_active_day[1]})"
        else:
            most_active_label = "—"

        summary_items = [
            ("Total Deliveries", str(total_deliveries)),
            ("Total Earnings", _money(total_earnings)),
            ("Average per Delivery", _money(avg_per)),
            ("Most Active Day", most_active_label),
        ]
    except mysql.connector.Error as e:
        logger.exception("Rider deliveries PDF DB error: %s", e)
        fallback_msg = "Unable to load data at this time. Please try again later."
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    title = f"Delivery Report — {rider_name}"
    if fallback_msg:
        return _error_pdf(title, label, fallback_msg)

    story = [
        _summary_row(summary_items),
        Spacer(1, 10),
        Paragraph("Completed deliveries in this period", s["section"]),
        _data_table(
            ["Order #", "Completed On", "Customer", "Store", "Earnings"],
            table_rows,
            col_widths=[28 * mm, 32 * mm, 36 * mm, 44 * mm, 30 * mm],
        ),
    ]
    return _render(title, label, story)
