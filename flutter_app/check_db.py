import mysql.connector
import os

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='babystore'
    )
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT productID, name, image_path FROM products ORDER BY productID DESC LIMIT 10")
    for r in cur.fetchall():
        print(f"ID: {r['productID']}, Name: {r['name']}, Image: {r['image_path']}")
except Exception as e:
    print(f"Error: {e}")
