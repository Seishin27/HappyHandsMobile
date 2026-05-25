import sys
import os
import traceback

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(root, '.env'))
except ImportError:
    pass

_startup_error = None
_app = None

try:
    from app import authentication

    try:
        from app.seller_api import seller_api_bp
        if 'seller_api' not in authentication.app.blueprints:
            authentication.app.register_blueprint(seller_api_bp)
    except Exception:
        pass

    try:
        from app.reports_api import reports_bp
        if 'reports' not in authentication.app.blueprints:
            authentication.app.register_blueprint(reports_bp)
    except ImportError as e:
        print(f"[startup] reports_api unavailable: {e}", file=sys.stderr)

    _app = authentication.app

except Exception:
    _startup_error = traceback.format_exc()


def _error_app(environ, start_response):
    body = f"Startup failed:\n\n{_startup_error}".encode()
    start_response("500 Internal Server Error", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


app = _app if _app is not None else _error_app
