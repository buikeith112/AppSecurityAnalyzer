from flask import Flask, request

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login(request):
    username = request.form["username"]
    return username


@app.get("/users/<user_id>")
def get_user(user_id):
    if len(user_id) > 20:
        return "invalid"
    return user_id


def process_payload(payload):
    return payload["name"]


def process_checked_input(user_input):
    if not isinstance(user_input, str):
        return None
    return user_input.strip()
