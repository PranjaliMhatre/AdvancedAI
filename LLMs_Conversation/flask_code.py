
import textwrap

from flask import Flask, request, render_template
from openai import OpenAI, AuthenticationError, RateLimitError
import os
import time

from dotenv import load_dotenv

load_dotenv(
    "/Users/pranjalimhatre/Scaler/AdvancedAI/openAIKey.env"
)  # reads .env file in the current directory


#flask --app flask_code.py run
#curl --location 'http://127.0.0.1:5000/'

def pretty_print(*args):
    text = " ".join(str(arg) for arg in args)
    try:
        print(textwrap.fill(text, width=80))
    except Exception as e:
        print(text)  # fallback to normal print if text is not a string
        

app = Flask(__name__)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError(
        "OPENAI_API_KEY not found! "
        "Make sure you have a .env file with: OPENAI_API_KEY=sk-..."
    )

pretty_print("API key loaded successfully.")

client = OpenAI(api_key=api_key)
#pretty_print("OpenAI client ready.")

# Shared conversation state (for demo only, reset on server restart)
messages = [
    {
        "role": "system",
        "content": "You are a friendly And neighborhood assistant who explains concepts clearly.",
    }
]	


def safe_chat_call(messages):
    try:
        return client.chat.completions.create(model="gpt-5-nano", messages=messages)
    except AuthenticationError:
        pretty_print("Authentication failed - check your API key.")
    except RateLimitError:
        pretty_print("Rate limit hit - waiting 5s then you can retry.")
        time.sleep(5)
    except Exception as e:
        pretty_print(f"Unexpected error: {e}")
    return None


@app.route("/", methods=["GET", "POST"])
def index():
    reply = ""
    usage_info = ""
    if request.method == "POST":
        user_text = request.form["user_input"]
        messages.append({"role": "user", "content": user_text})

        resp = safe_chat_call(messages)
        if resp:
            reply = resp.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})

            usage = resp.usage
            usage_info = f"Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            #pretty_print(f"\nReply: {reply}")
    return render_template("index.html", reply=reply, usage=usage_info)


# command to run flask app

# flask --app flask_code.py run --debug