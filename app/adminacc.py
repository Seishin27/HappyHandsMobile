"""
Simple admin credential holder and checker.

Configure ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD (or set ADMIN_PASSWORD via env)
in a secure way for your environment. This module exposes `is_admin_credentials` which
authentication code can call to determine whether a login belongs to the admin.
"""
import os
from werkzeug.security import generate_password_hash, check_password_hash

# You can set these via environment variables or edit below (not recommended for prod).
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'babybloomph@gmail.com')
# It's strongly recommended to set ADMIN_PASSWORD in the environment. If set, we'll hash it here.
_env_pass = os.environ.get('ADMIN_PASSWORD', 'babybloomph123')
if _env_pass:
    ADMIN_PASSWORD_HASH = generate_password_hash(_env_pass)
else:
    # Default placeholder password hash (change immediately).
    # If you want to set the password directly in this file (not recommended), replace the string
    # below with generate_password_hash('your-password') and keep the file out of source control.
    ADMIN_PASSWORD_HASH = generate_password_hash('admin')


def is_admin_credentials(username: str, email: str | None, password: str) -> bool:
    """Return True if the provided credentials match the configured admin.

    This checks username or email, and verifies the password using the stored hash.
    """
    if not username and not email:
        return False

    # Match on username
    if ADMIN_USERNAME and username == ADMIN_USERNAME:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)

    # Match on email
    if ADMIN_EMAIL and email and email == ADMIN_EMAIL:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)

    return False
