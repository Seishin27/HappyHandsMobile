import sys
import os

# Add project root to path so `from app import authentication` resolves correctly
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)

# Load .env before importing authentication — it reads env vars at import time
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(root, '.env'))
except ImportError:
    pass

# Import the Flask app object (created at authentication.py:275)
from app import authentication

# Register blueprints that run.py normally registers inside __main__
try:
    from app.seller_api import seller_api_bp
    if 'seller_api' not in authentication.app.blueprints:
        authentication.app.register_blueprint(seller_api_bp)
except Exception:
    pass

# Expose module-level `app` — Vercel's WSGI handler looks for this name
app = authentication.app
