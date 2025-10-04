import json
import random
import re
import math
import requests
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import pyttsx3
from textblob import TextBlob
from datetime import datetime

# Configuration
with open("config.json") as f:
    config = json.load(f)

bot_name = config.get("bot_name", "ChatGenie")
voice_enabled = config.get("voice_enabled", True)
weather_api_key = config.get("weather_api_key", "")

# Audio Settings
SAMPLE_RATE = 16000  # Optimal for speech recognition
CHANNELS = 1
DTYPE = 'int16'
sd.default.device = 1  # Use your working microphone

# Initialize TTS Engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# Mood Tracking
mood_history = []

# Enhanced Responses
RESPONSES = {
    "greeting": [
        f"Hello! I'm {bot_name}, your personal assistant! 👋",
        f"Hi there! I'm {bot_name}, ready to help! 💬"
    ],
    "capabilities": [
        "I can: Check weather, do math, tell jokes, and chat! 🌦️➕😂",
        "Features: Weather, calculations, mood analysis, humor"
    ],
    "creator": [
        "I was created by a talented developer using Python 🐍",
        "A programmer built me to be your helpful assistant 💻"
    ],
    "goodbye": [
        "Goodbye! Have a wonderful day! 🌟",
        "See you later! Come back anytime! 👋"
    ],
    "math_help": [
        "Math examples: '2+2', '5*3', 'sqrt(16)', '2^3' ➗",
        "Try: '10 plus 5', 'square root of 25', '3 cubed'"
    ],
    "weather_help": [
        "Ask: 'weather in London' or 'what's the weather in Paris?' 🌤️",
        "Try: 'weather Tokyo' or 'how's the weather in New York?'"
    ],
    "jokes": [
        "Why don't scientists trust atoms? Because they make up everything! 🤓",
        "I'm reading a book about anti-gravity. It's impossible to put down! 📚",
        "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾"
    ],
    "mood_suggestions": {
        "positive": [
            "You're radiating positivity! Maybe spread some joy today! 🌈",
            "Your good mood is contagious! Consider sharing it with someone! 💌"
        ],
        "neutral": [
            "Everything seems balanced. A short walk might be nice! 🚶‍♂️",
            "Feeling centered? Try some mindful breathing. 🌿"
        ],
        "negative": [
            "I sense you're feeling down. A 5-minute meditation might help. 🧘‍♀️",
            "When I feel low, I remember: this too shall pass. 💛"
        ],
        "stress": [
            "Stressful day? Try box breathing: Inhale 4s, Hold 4s, Exhale 4s. 🌬️",
            "Emergency hack: Name 5 things you can see around you. 👀"
        ]
    },
    "emergency": [
        "If you need help, please contact: 1-800-XXX-XXXX 🆘",
        "You're not alone. Reach out to a trusted friend or counselor. 🤝"
    ],
    "default": [
        "I'm not sure I understand. Could you rephrase? 🤔",
        "Let's try a different question? 💭",
        "I'm still learning. Ask me something else? 📚"
    ]
}

def speak(text):
    """Improved text-to-speech with emoji handling"""
    print(f"{bot_name}: {text}")
    try:
        # Remove emojis for speech
        clean_text = ''.join(char for char in text if ord(char) < 65536)
        engine.say(clean_text)
        engine.runAndWait()
    except Exception as e:
        print(f"Speech error: {e}")

def listen():
    """Robust voice recording without temporary files"""
    recognizer = sr.Recognizer()
    try:
        print("\nListening... (Speak now)")
        recording = sd.rec(int(5 * SAMPLE_RATE),
                          samplerate=SAMPLE_RATE,
                          channels=CHANNELS,
                          dtype=DTYPE)
        sd.wait()
        
        audio_data = sr.AudioData(
            recording.tobytes(),
            sample_rate=SAMPLE_RATE,
            sample_width=2  # 16-bit = 2 bytes
        )
        
        text = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"You said: {text}")
        return text.lower()
        
    except sr.UnknownValueError:
        print("Couldn't understand audio")
        return ""
    except sr.RequestError as e:
        print(f"API Error: {e}")
        return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

def calculate_expression(expression):
    """Handles math calculations"""
    try:
        expression = expression.lower().replace('x', '*').replace('×', '*')
        expression = re.sub(r'what is|what\'s|calculate|compute|how much is', '', expression)
        
        if 'square of' in expression:
            num = re.search(r'square of\s*(\d+)', expression)
            if num:
                return f"The result is: {int(num.group(1))**2}"
        
        if 'cube of' in expression:
            num = re.search(r'cube of\s*(\d+)', expression)
            if num:
                return f"The result is: {int(num.group(1))**3}"
        
        if 'square root of' in expression:
            num = re.search(r'square root of\s*(\d+)', expression)
            if num:
                return f"The result is: {math.sqrt(int(num.group(1)))}"
        
        math_expr = re.sub(r'[^0-9+\-*/().^%]', '', expression)
        if not math_expr:
            return None
            
        result = eval(math_expr, {'__builtins__': None}, {})
        return f"The result is: {result}"
    except Exception as e:
        print(f"Math error: {e}")
        return None

def get_weather(city_name):
    """Fetches weather data"""
    try:
        if not weather_api_key:
            return "Weather service not configured. Please set API key."
            
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}q={city_name}&appid={weather_api_key}&units=metric"
        
        response = requests.get(complete_url, timeout=10)
        data = response.json()
        
        if data.get("cod") != 200:
            return f"Couldn't get weather: {data.get('message', 'Unknown error')}"
            
        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "city": data["name"]
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return None

def analyze_mood(text):
    """Advanced sentiment analysis with stress detection"""
    if not text:
        return "neutral"
    
    analysis = TextBlob(text).sentiment
    stress_words = ["stress", "overwhelmed", "anxious", "pressure", "tired"]
    
    if any(word in text.lower() for word in stress_words):
        mood = "stress"
    elif analysis.polarity > 0.3:
        mood = "positive"
    elif analysis.polarity < -0.3:
        mood = "negative"
    else:
        mood = "neutral"
    
    # Track mood history
    mood_history.append({
        "time": datetime.now().strftime("%H:%M"),
        "mood": mood,
        "text": text[:50] + ("..." if len(text) > 50 else "")
    })
    
    return mood

def get_mood_suggestion(mood):
    """Returns personalized wellness suggestion"""
    if mood == "negative" and len(mood_history) > 0:
        if TextBlob(mood_history[-1]["text"]).polarity < -0.7:
            return random.choice(RESPONSES["emergency"])
    return random.choice(RESPONSES["mood_suggestions"].get(mood, ""))

def get_response(user_input):
    """Enhanced response handler with all features"""
    if not user_input:
        return random.choice(RESPONSES["default"])
    
    # Mood analysis
    mood = analyze_mood(user_input)
    mood_suggestion = get_mood_suggestion(mood)
    
    # Jokes
    if "joke" in user_input.lower():
        return f"{random.choice(RESPONSES['jokes'])}\n\n{mood_suggestion}"
    
    # Weather queries
    weather_match = re.search(r'weather (?:in|for|at)?\s*([a-zA-Z\s]+)', user_input.lower())
    if weather_match:
        city = weather_match.group(1).strip()
        weather = get_weather(city)
        if isinstance(weather, str):  # Error message
            return f"{weather}\n\n{mood_suggestion}"
        elif weather:
            return f"""🌤️ Weather in {weather['city']}:
{weather['description'].capitalize()}
🌡️ Temp: {weather['temperature']}°C
💧 Humidity: {weather['humidity']}%

{mood_suggestion}"""
        return f"Sorry, couldn't fetch weather data.\n\n{mood_suggestion}"
    
    # Math calculations
    math_result = calculate_expression(user_input)
    if math_result:
        return f"{math_result}\n\n{mood_suggestion}"
    
    # Mood check
    if "how are you" in user_input.lower() or "feeling" in user_input.lower():
        if mood_history:
            last_mood = mood_history[-1]["mood"]
            return f"I sense you've been feeling {last_mood} recently. {mood_suggestion}"
        return "I'm here to listen. How are you really feeling today?"
    
    # Command responses
    user_input_lower = user_input.lower()
    if any(word in user_input_lower for word in ["hi", "hello", "hey"]):
        return f"{random.choice(RESPONSES['greeting'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["what can you do", "help"]):
        return f"{random.choice(RESPONSES['capabilities'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["who made you", "creator"]):
        return f"{random.choice(RESPONSES['creator'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["bye", "exit", "quit"]):
        return f"{random.choice(RESPONSES['goodbye'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["math help"]):
        return f"{random.choice(RESPONSES['math_help'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["weather help"]):
        return f"{random.choice(RESPONSES['weather_help'])}\n\n{mood_suggestion}"
    
    # Default
    return f"{random.choice(RESPONSES['default'])}\n\n{mood_suggestion}"

def main():
    global voice_enabled
    
    speak(random.choice(RESPONSES["greeting"]))
    print("\nVOICE COMMANDS:")
    print("- Say 'text mode' to switch to keyboard")
    print("- Say 'help' for features overview")
    print("- Say 'exit' to quit")
    
    while True:
        if voice_enabled:
            print("\nListening... (say 'text mode' or press Ctrl+C)")
            user_input = listen()
            
            if user_input and "text mode" in user_input:
                voice_enabled = False
                print("\nTEXT MODE: Type 'voice mode' to switch back")
                continue
        else:
            user_input = input("\nYou: ").strip().lower()
            if user_input == "voice mode":
                voice_enabled = True
                print("\nVOICE MODE: Say 'text mode' to switch back")
                continue
        
        if not user_input:
            continue
            
        if "exit" in user_input or "quit" in user_input:
            # Show mood history before exiting
            if mood_history:
                print("\n📊 Your Mood History:")
                for entry in mood_history[-3:]:  # Show last 3 entries
                    print(f"{entry['time']}: {entry['mood'].upper()} - {entry['text']}")
            speak(random.choice(RESPONSES["goodbye"]))
            break
            
        response = get_response(user_input)
        speak(response)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak("Goodbye! Remember to check in with your feelings. 💙")
    import pyttsx3
engine = pyttsx3.init()
engine.say("Test")
engine.runAndWait()
engine.stop() 
import random
import re
import math
import requests
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import pyttsx3
from textblob import TextBlob
from datetime import datetime

# Configuration
with open("config.json") as f:
    config = json.load(f)

bot_name = config.get("bot_name", "ChatGenie")
voice_enabled = config.get("voice_enabled", True)
weather_api_key = config.get("weather_api_key", "")

# Audio Settings
SAMPLE_RATE = 16000  # Optimal for speech recognition
CHANNELS = 1
DTYPE = 'int16'
sd.default.device = 1  # Use your working microphone

# Initialize TTS Engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

# Mood Tracking
mood_history = []

# Enhanced Responses
RESPONSES = {
    "greeting": [
        f"Hello! I'm {bot_name}, your personal assistant! 👋",
        f"Hi there! I'm {bot_name}, ready to help! 💬"
    ],
    "capabilities": [
        "I can: Check weather, do math, tell jokes, and chat! 🌦️➕😂",
        "Features: Weather, calculations, mood analysis, humor"
    ],
    "creator": [
        "I was created by a talented developer using Python 🐍",
        "A programmer built me to be your helpful assistant 💻"
    ],
    "goodbye": [
        "Goodbye! Have a wonderful day! 🌟",
        "See you later! Come back anytime! 👋"
    ],
    "math_help": [
        "Math examples: '2+2', '5*3', 'sqrt(16)', '2^3' ➗",
        "Try: '10 plus 5', 'square root of 25', '3 cubed'"
    ],
    "weather_help": [
        "Ask: 'weather in London' or 'what's the weather in Paris?' 🌤️",
        "Try: 'weather Tokyo' or 'how's the weather in New York?'"
    ],
    "jokes": [
        "Why don't scientists trust atoms? Because they make up everything! 🤓",
        "I'm reading a book about anti-gravity. It's impossible to put down! 📚",
        "Why did the scarecrow win an award? Because he was outstanding in his field! 🌾"
    ],
    "mood_suggestions": {
        "positive": [
            "You're radiating positivity! Maybe spread some joy today! 🌈",
            "Your good mood is contagious! Consider sharing it with someone! 💌"
        ],
        "neutral": [
            "Everything seems balanced. A short walk might be nice! 🚶‍♂️",
            "Feeling centered? Try some mindful breathing. 🌿"
        ],
        "negative": [
            "I sense you're feeling down. A 5-minute meditation might help. 🧘‍♀️",
            "When I feel low, I remember: this too shall pass. 💛"
        ],
        "stress": [
            "Stressful day? Try box breathing: Inhale 4s, Hold 4s, Exhale 4s. 🌬️",
            "Emergency hack: Name 5 things you can see around you. 👀"
        ]
    },
    "emergency": [
        "If you need help, please contact: 1-800-XXX-XXXX 🆘",
        "You're not alone. Reach out to a trusted friend or counselor. 🤝"
    ],
    "default": [
        "I'm not sure I understand. Could you rephrase? 🤔",
        "Let's try a different question? 💭",
        "I'm still learning. Ask me something else? 📚"
    ]
}

def speak(text):
    """Improved text-to-speech with emoji handling"""
    print(f"{bot_name}: {text}")
    try:
        # Remove emojis for speech
        clean_text = ''.join(char for char in text if ord(char) < 65536)
        engine.say(clean_text)
        engine.runAndWait()
    except Exception as e:
        print(f"Speech error: {e}")

def listen():
    """Robust voice recording without temporary files"""
    recognizer = sr.Recognizer()
    try:
        print("\nListening... (Speak now)")
        recording = sd.rec(int(5 * SAMPLE_RATE),
                          samplerate=SAMPLE_RATE,
                          channels=CHANNELS,
                          dtype=DTYPE)
        sd.wait()
        
        audio_data = sr.AudioData(
            recording.tobytes(),
            sample_rate=SAMPLE_RATE,
            sample_width=2  # 16-bit = 2 bytes
        )
        
        text = recognizer.recognize_google(audio_data, language="en-IN")
        print(f"You said: {text}")
        return text.lower()
        
    except sr.UnknownValueError:
        print("Couldn't understand audio")
        return ""
    except sr.RequestError as e:
        print(f"API Error: {e}")
        return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

def calculate_expression(expression):
    """Handles math calculations"""
    try:
        expression = expression.lower().replace('x', '*').replace('×', '*')
        expression = re.sub(r'what is|what\'s|calculate|compute|how much is', '', expression)
        
        if 'square of' in expression:
            num = re.search(r'square of\s*(\d+)', expression)
            if num:
                return f"The result is: {int(num.group(1))**2}"
        
        if 'cube of' in expression:
            num = re.search(r'cube of\s*(\d+)', expression)
            if num:
                return f"The result is: {int(num.group(1))**3}"
        
        if 'square root of' in expression:
            num = re.search(r'square root of\s*(\d+)', expression)
            if num:
                return f"The result is: {math.sqrt(int(num.group(1)))}"
        
        math_expr = re.sub(r'[^0-9+\-*/().^%]', '', expression)
        if not math_expr:
            return None
            
        result = eval(math_expr, {'__builtins__': None}, {})
        return f"The result is: {result}"
    except Exception as e:
        print(f"Math error: {e}")
        return None

def get_weather(city_name):
    """Fetches weather data"""
    try:
        if not weather_api_key:
            return "Weather service not configured. Please set API key."
            
        base_url = "http://api.openweathermap.org/data/2.5/weather?"
        complete_url = f"{base_url}q={city_name}&appid={weather_api_key}&units=metric"
        
        response = requests.get(complete_url, timeout=10)
        data = response.json()
        
        if data.get("cod") != 200:
            return f"Couldn't get weather: {data.get('message', 'Unknown error')}"
            
        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "city": data["name"]
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return None

def analyze_mood(text):
    """Advanced sentiment analysis with stress detection"""
    if not text:
        return "neutral"
    
    analysis = TextBlob(text).sentiment
    stress_words = ["stress", "overwhelmed", "anxious", "pressure", "tired"]
    
    if any(word in text.lower() for word in stress_words):
        mood = "stress"
    elif analysis.polarity > 0.3:
        mood = "positive"
    elif analysis.polarity < -0.3:
        mood = "negative"
    else:
        mood = "neutral"
    
    # Track mood history
    mood_history.append({
        "time": datetime.now().strftime("%H:%M"),
        "mood": mood,
        "text": text[:50] + ("..." if len(text) > 50 else "")
    })
    
    return mood

def get_mood_suggestion(mood):
    """Returns personalized wellness suggestion"""
    if mood == "negative" and len(mood_history) > 0:
        if TextBlob(mood_history[-1]["text"]).polarity < -0.7:
            return random.choice(RESPONSES["emergency"])
    return random.choice(RESPONSES["mood_suggestions"].get(mood, ""))

def get_response(user_input):
    """Enhanced response handler with all features"""
    if not user_input:
        return random.choice(RESPONSES["default"])
    
    # Mood analysis
    mood = analyze_mood(user_input)
    mood_suggestion = get_mood_suggestion(mood)
    
    # Jokes
    if "joke" in user_input.lower():
        return f"{random.choice(RESPONSES['jokes'])}\n\n{mood_suggestion}"
    
    # Weather queries
    weather_match = re.search(r'weather (?:in|for|at)?\s*([a-zA-Z\s]+)', user_input.lower())
    if weather_match:
        city = weather_match.group(1).strip()
        weather = get_weather(city)
        if isinstance(weather, str):  # Error message
            return f"{weather}\n\n{mood_suggestion}"
        elif weather:
            return f"""🌤️ Weather in {weather['city']}:
{weather['description'].capitalize()}
🌡️ Temp: {weather['temperature']}°C
💧 Humidity: {weather['humidity']}%

{mood_suggestion}"""
        return f"Sorry, couldn't fetch weather data.\n\n{mood_suggestion}"
    
    # Math calculations
    math_result = calculate_expression(user_input)
    if math_result:
        return f"{math_result}\n\n{mood_suggestion}"
    
    # Mood check
    if "how are you" in user_input.lower() or "feeling" in user_input.lower():
        if mood_history:
            last_mood = mood_history[-1]["mood"]
            return f"I sense you've been feeling {last_mood} recently. {mood_suggestion}"
        return "I'm here to listen. How are you really feeling today?"
    
    # Command responses
    user_input_lower = user_input.lower()
    if any(word in user_input_lower for word in ["hi", "hello", "hey"]):
        return f"{random.choice(RESPONSES['greeting'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["what can you do", "help"]):
        return f"{random.choice(RESPONSES['capabilities'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["who made you", "creator"]):
        return f"{random.choice(RESPONSES['creator'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["bye", "exit", "quit"]):
        return f"{random.choice(RESPONSES['goodbye'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["math help"]):
        return f"{random.choice(RESPONSES['math_help'])}\n\n{mood_suggestion}"
    elif any(word in user_input_lower for word in ["weather help"]):
        return f"{random.choice(RESPONSES['weather_help'])}\n\n{mood_suggestion}"
    
    # Default
    return f"{random.choice(RESPONSES['default'])}\n\n{mood_suggestion}"

def main():
    global voice_enabled
    
    speak(random.choice(RESPONSES["greeting"]))
    print("\nVOICE COMMANDS:")
    print("- Say 'text mode' to switch to keyboard")
    print("- Say 'help' for features overview")
    print("- Say 'exit' to quit")
    
    while True:
        if voice_enabled:
            print("\nListening... (say 'text mode' or press Ctrl+C)")
            user_input = listen()
            
            if user_input and "text mode" in user_input:
                voice_enabled = False
                print("\nTEXT MODE: Type 'voice mode' to switch back")
                continue
        else:
            user_input = input("\nYou: ").strip().lower()
            if user_input == "voice mode":
                voice_enabled = True
                print("\nVOICE MODE: Say 'text mode' to switch back")
                continue
        
        if not user_input:
            continue
            
        if "exit" in user_input or "quit" in user_input:
            # Show mood history before exiting
            if mood_history:
                print("\n📊 Your Mood History:")
                for entry in mood_history[-3:]:  # Show last 3 entries
                    print(f"{entry['time']}: {entry['mood'].upper()} - {entry['text']}")
            speak(random.choice(RESPONSES["goodbye"]))
            break
            
        response = get_response(user_input)
        speak(response)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak("Goodbye! Remember to check in with your feelings. 💙")
    finally:
        engine.stop()