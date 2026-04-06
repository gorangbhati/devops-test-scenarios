from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return {"status": "ok", "scenario": "11-resource-quota"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
