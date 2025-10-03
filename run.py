from app import authentication
from app import admin

if __name__ == '__main__':
    app = admin.app
    app = authentication.app
    app.run(debug=True, port=5500)
