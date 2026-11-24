import os, json, textwrap
from dotenv import load_dotenv


# Wrap long model output at 80 columns instead of one endless line.
def pretty_print(*args):
    text = " ".join(str(arg) for arg in args)
    print(textwrap.fill(text, width=80))


load_dotenv("/Users/pranjalimhatre/Scaler/AdvancedAI/openAIKey.env")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found! Check the path to your openai_key.env file.")

# pretty_print("API key loaded successfully.")

from openai import OpenAI

client = OpenAI(api_key=api_key)
MODEL = "gpt-5-nano"
# pretty_print("OpenAI client ready. Model:", MODEL)

import requests

SESSION = requests.Session()
SESSION.trust_env = False

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def get_coordinates(location):
    """Fetch latitude and longitude for a location name using the Open-Meteo Geocoding API.

    Args:
        location: City or place name to look up.

    Returns:
        A (latitude, longitude) tuple in decimal degrees.
    """
    response = SESSION.get(GEOCODE_URL, 
                           params={"name": location, "count": 1, "language": "en", "format": "json"  },
                           timeout=10)

    response.raise_for_status()
    results = response.json().get("results") or []  
    if not results:
        raise ValueError(f"No coordinates found for location: {location}")

    place = results[0]
    latitude = place.get("latitude")
    longitude = place.get("longitude")

    resolved = " ".join(filter(None, [place.get("name"), place.get("admin1"), place.get("country")]))
    #return (f"{resolved} : {latitude}, {longitude}")
    return {"latitude": latitude, "longitude": longitude}
          #  "place_name": place.get("name"), 
          #  "state": place.get("admin1"),
          #  "country": place.get("country")}



def get_weather(latitude, longitude):
    """Fetch current weather data for given latitude and longitude using the Open-Meteo Weather API.

    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.

    Returns:
        A dictionary containing current weather information.
    """

    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    # WMO weather codes -> human labels
    WEATHER_CODES = {
        0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "fog", 48: "depositing rime fog",
        51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
        61: "light rain", 63: "moderate rain", 65: "heavy rain",
        71: "light snow", 73: "moderate snow", 75: "heavy snow",
        80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
        95: "thunderstorm", 96: "thunderstorm w/ hail", 99: "severe thunderstorm w/ hail",
    }
    print(f"Fetching weather for coordinates: {latitude}, {longitude}")
    respose = SESSION.get(WEATHER_URL,
                          params={
                              "latitude": latitude,
                              "longitude": longitude,
                              "daily": "temperature_2m_max,temperature_2m_min",
                              "current" : "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m,apparent_temperature",
                              "timezone": "auto"
                          },
                          timeout=10)
    respose.raise_for_status()
    #pretty_print("Weather API response:", respose.json())
    current_details = respose.json().get("current") or {}

    current_forecast = {
        "temperature": current_details.get("temperature_2m"),
        "condition": WEATHER_CODES.get(current_details.get("weather_code"), "unknown"),
        "humidity": current_details.get("relative_humidity_2m"),
        "wind_speed": current_details.get("wind_speed_10m"),
        "high_temp": respose.json().get("daily", {}).get("temperature_2m_max", [None])[0],
        "low_temp": respose.json().get("daily", {}).get("temperature_2m_min", [None])[0]  
    }
    
    return current_forecast


#print(get_coordinates("Bengaluru"))
#get_weather(**get_coordinates("Bengaluru"))


geo_coordinate_tool = {
    "type": "function",
    "name": "get_coordinates",
    "description": "Fetch latitude and longitude for a location name using the Open-Meteo Geocoding API.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or place name to look up."
            }
        },
        "required": ["location"]
    }
}

weather_tool = {
    "type": "function",
    "name": "get_weather",
    "description": "Fetch current weather data for given latitude and longitude using the Open-Meteo Weather API.",
    "parameters": {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude in decimal degrees."
            },
            "longitude": {
                "type": "number",
                "description": "Longitude in decimal degrees."
            }
        },
        "required": ["latitude", "longitude"]
    }
}

TOOLS = [geo_coordinate_tool, weather_tool]
DISPATCHER = {
    "get_coordinates": get_coordinates,
    "get_weather": get_weather
}
DEV_POLICY = "Use the tools for fetching coordinates and weather information. Never compute or guess yourself."

def run_tool_loop(user_message, tools = TOOLS, dispatcher = DISPATCHER, instructions = DEV_POLICY, text_format = None):
    """
    Run a loop to process user messages, call tools, and generate responses.
    # Ask -> run whatever tools it asks for -> hand the results back -> repeat.

    Args:
        user_message: The initial message from the user.
        tools: A list of tool definitions.
        dispatcher: A dictionary mapping tool names to their corresponding functions.
        instructions: Instructions for the model on how to use the tools.
        text_format: Optional format for the output text.

    Returns:
        The final response from the model after processing the user message and tool outputs.
       
        # Returns the final response object:
        #   text_format given  ->  read response.output_parsed  (a validated Pydantic object)
        #   text_format None   ->  read response.output_text    (prose)
    """

    schema = {"text_format": text_format} if text_format else {}
    # pretty_print(
    #     f"User message type: {type(user_message)}, "
    #     f"model_type: {type(MODEL)}, "
    #     f"tools type: {type(tools)}, "
    #     f"dispatcher type: {type(dispatcher)}, "
    #     f"instructions type: {type(instructions)}, "
    #     f"schema type: {type(schema)}"
    # )
                 
    response = client.responses.parse(
        model=MODEL,
        input=[{"role" : "user", "content": user_message}],
        tools=tools,
        instructions=instructions,
        **schema
    )
    
    for round_no in range(1, 7):
        calls = [item for item in response.output if item.type == "function_call"]

        if not calls:
            return response
       
        tool_outputs = []
        for call in calls:
            tool_name = call.name
            tool_args = json.loads(call.arguments) if call.arguments else {}
            
            if tool_name in dispatcher:
                try:
                    result = dispatcher[tool_name](**tool_args)
                    #pretty_print(f"Tool '{tool_name}' called with arguments: {tool_args}. Result: {result}")
                    tool_outputs.append(
                        {"type" : "function_call_output",
                         "call_id" : call.call_id,
                         "output" : json.dumps(result)}
                    )
                except Exception as e:
                    tool_outputs.append({"name": tool_name, "output": f"Error: {str(e)}"})
            else:
                tool_outputs.append({"name": tool_name, 
                                     "output": f"Error: Tool '{tool_name}' not found."})

        # pretty_print(f"Round {round_no} tool outputs: {tool_outputs}")       
        response = client.responses.parse(
            model=MODEL,
            instructions=instructions,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools,
            **schema
        )

    still_wants = [item.name for item in response.output if item.type == "function_call"]
    raise RuntimeError(f"Still asking for tools after 6 rounds: {still_wants}. "
                       "Usually means a tool result didn't answer the question it was asked.")


# final = run_tool_loop(
#     "What is the weather like in Bengaluru?",
#     tools=TOOLS,
#     dispatcher=DISPATCHER,
#     instructions=DEV_POLICY,
# )
# print("\nFinal:", final.output_text)

