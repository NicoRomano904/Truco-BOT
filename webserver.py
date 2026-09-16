from flask import Flask
from threading import Thread

# Create the Flask application
app = Flask(__name__)


@app.route('/')
def index():
    return "Hello, World!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()


if __name__ == '__main__':
    run()
