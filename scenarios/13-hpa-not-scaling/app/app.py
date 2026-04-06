from flask import Flask
import time

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "ok", "scenario": "13-hpa"}

@app.route("/cpu")
def cpu():
    # simulate CPU work
    start = time.time()
    while time.time() - start < 2:
        pass
    return {"status": "cpu-load"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
