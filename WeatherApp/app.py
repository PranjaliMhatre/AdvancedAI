import textwrap

from flask import Flask, request, render_template
from weather_service import get_coordinates, get_weather, run_tool_loop, pretty_print

app = Flask(__name__, template_folder="templates")

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/weather/api/chat", methods=["POST"])
def chat():
    reply = ""
    pretty_print(f"\nEntered flask chat: {reply}")
    
    if request.method == "POST":
        #user_text = request.form["user_input"]
        data = request.get_json(silent=True) or {}
        user_text = (data.get("message") or "").strip()
    
        if not user_text:
            return "Please enter a message.", 400
        final = run_tool_loop(
            user_text
        )
        reply = final.output_text
        pretty_print(f"\nReply from service: {reply}")
        return reply, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return render_template("index.html")