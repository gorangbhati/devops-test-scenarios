import os
from flask import Flask

app = Flask(__name__)

SECRET_KEY = os.getenv("API_KEY")

@app.route("/")
def home():
    if not SECRET_KEY:
        raise Exception("Missing API_KEY secret")
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
