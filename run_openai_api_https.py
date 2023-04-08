from app import app
from config import HOST, PORT_HTTPS

if __name__ == '__main__':
    context = ('ssl.cert', 'ssl.key')
    app.run(host=HOST, port=PORT_HTTPS, debug=False, ssl_context=context)