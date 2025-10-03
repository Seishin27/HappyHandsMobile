from flask import render_template, redirect, url_for

# Reuse the Flask app instance from authentication.py so routes register on the same app
from .authentication import app


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Basic admin dashboard placeholder. In production protect this route with proper auth.
    return render_template('admin.html')