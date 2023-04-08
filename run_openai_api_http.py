from app import app
from config import HOST, PORT_HTTP

if __name__ == '__main__':
    app.run(host=HOST, port=PORT_HTTP, debug=False)