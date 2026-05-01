from flask import Flask

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    return "ok"


@app.get("/status")
def status():
    return "ok"
