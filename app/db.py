"""Shared database connection factory used by all Flask modules."""

import os

import mysql.connector

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except Exception:
    pass

DB_HOST = os.environ.get("HH_DB_HOST", "localhost")
DB_PORT = int(os.environ.get("HH_DB_PORT", "3306"))
DB_USER = os.environ.get("HH_DB_USER", "root")
DB_PASSWORD = os.environ.get("HH_DB_PASSWORD", "")
DB_NAME = os.environ.get("HH_DB_NAME") or os.environ.get("BABYSTORE_DB") or "babystore"
DB_CONNECT_TIMEOUT = int(os.environ.get("HH_DB_CONNECT_TIMEOUT", "5"))


def get_db():
    """Return a new MySQL connection. Caller is responsible for closing it."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        connection_timeout=DB_CONNECT_TIMEOUT,
    )
