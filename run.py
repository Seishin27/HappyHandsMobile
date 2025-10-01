from app import authentication

if __name__ == '__main__':
    app = authentication.app
    app.run(debug=True, port=5500)
