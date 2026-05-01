from flask import Flask, request

app = Flask(__name__)

OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"


@app.route("/login", methods=["POST"])
def login(request):
    username = request.form["username"]
    return username
