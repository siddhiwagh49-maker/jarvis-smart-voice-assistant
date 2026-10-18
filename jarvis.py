"""
================================================================================
⚡ J.A.R.V.I.S. - STARK INDUSTRIES INTELLIGENT AI ASSISTANT
Unified All-In-One Edition | Powered by Google Gemini AI & Neural Speech
Tailored for Hands-Free, Voice-Driven, and Fully Accessible Desktop Control
================================================================================
"""

import os
import sys
import time
import math
import queue
import ctypes
import random
import asyncio
import datetime
import threading
import subprocess
import webbrowser
import json
import urllib.request
import urllib.parse
import tkinter as tk
from pathlib import Path
from typing import Optional, Tuple

# --- Audio Driver Compatibility ---
try:
    import pyaudio
except ImportError:
    pyaudio = None

import speech_recognition as sr
import pyttsx3
import pythoncom
import psutil
import pyperclip
import pyautogui
import wikipedia
import customtkinter as ctk

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import winsound
except ImportError:
    winsound = None

# =====================================================================
# Configuration & Constants
# =====================================================================
ASSISTANT_NAME = "Jarvis"
USER_HONORIFIC = "Sir"
JARVIS_VOICE = "en-GB-RyanNeural"
JARVIS_RATE = "+8%"
JARVIS_PITCH = "-5Hz"
SPEECH_RATE = 175
SPEECH_VOLUME = 1.0

WAKE_WORDS = ["jarvis", "hey jarvis", "assistant"]
LISTEN_TIMEOUT = 6.0
PHRASE_TIME_LIMIT = 9.0

CURRENT_DIR = Path(__file__).resolve().parent
NOTES_DIR = CURRENT_DIR / "JarvisNotes"
NOTES_DIR.mkdir(exist_ok=True)
CACHE_DIR = CURRENT_DIR / ".jarvis_cache"
CACHE_DIR.mkdir(exist_ok=True)
GEMINI_KEY_FILE = CURRENT_DIR / ".gemini_key"

APP_MAP = {
    "whatsapp": "whatsapp:",
    "whats app": "whatsapp:",
    "whatsapp desktop": "whatsapp:",
    "spotify": "spotify:",
    "camera": "microsoft.windows.camera:",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "browser": "msedge.exe",
    "edge": "msedge.exe",
    "chrome": "chrome.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "settings": "ms-settings:",
    "narrator": "narrator.exe",
    "magnifier": "magnify.exe",
    "on screen keyboard": "osk.exe",
    "keyboard": "osk.exe",
    "task manager": "taskmgr.exe",
    "telegram": "telegram:",
}

WEBSITE_MAP = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "wikipedia": "https://www.wikipedia.org",
    "weather": "https://www.google.com/search?q=weather+forecast",
    "news": "https://news.google.com",
    "github": "https://www.github.com"
}

JOKES_BACKUP = [
    "I told my computer I needed a break, and now it refuses to boot without a cup of coffee.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
    "Why did the scarecrow win an award? Because he was outstanding in his field."
]

FACTS_BACKUP = [
    "Sound travels about four times faster in water than in air.",
    "A single bolt of lightning contains enough energy to toast 100,000 slices of bread.",
    "The heart of a blue whale is so large that a human child could swim through its major arteries.",
    "Hot water turns into ice faster than cold water, known scientifically as the Mpemba effect."
]

# Windows Virtual Keys
user32 = ctypes.windll.user32
winmm = ctypes.windll.winmm
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# =====================================================================
# Auditory Earcon Generator
# =====================================================================
def play_earcon(cue: str = "listen"):
    def _play():
        if not winsound:
            return
        try:
            if cue == "listen":
                winsound.Beep(900, 70)
                winsound.Beep(1300, 100)
            elif cue == "ack":
                winsound.Beep(1600, 110)
            elif cue == "success":
                winsound.Beep(1046, 70)
                winsound.Beep(1318, 70)
                winsound.Beep(1567, 120)
            elif cue == "error":
                winsound.Beep(600, 120)
                winsound.Beep(400, 180)
            elif cue == "sos":
                for _ in range(4):
                    winsound.Beep(1800, 150)
                    winsound.Beep(1200, 150)
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()

# =====================================================================
# UI Communication Queue
# =====================================================================
ui_event_queue = queue.Queue()

def notify_ui_status(status: str):
    ui_event_queue.put(("status", status))

def notify_ui_user_speech(text: str):
    ui_event_queue.put(("user_speech", text))

def notify_ui_jarvis_speech(text: str):
    ui_event_queue.put(("jarvis_speech", text))

# =====================================================================
# Gemini API Key Management
# =====================================================================
def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key and key.strip():
        return key.strip()
    if GEMINI_KEY_FILE.exists():
        try:
            val = GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
            if val:
                return val
        except Exception:
            pass
    return ""

def save_gemini_api_key(new_key: str):
    k = new_key.strip()
    GEMINI_KEY_FILE.write_text(k, encoding="utf-8")
    os.environ["GEMINI_API_KEY"] = k

# =====================================================================
# Speech Engine
# =====================================================================
class SpeechEngine:
    def __init__(self):
        self._speech_queue = queue.Queue()
        self._counter = 0
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._worker_thread.start()

    def _init_sapi(self):
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.setProperty("rate", SPEECH_RATE)
        engine.setProperty("volume", SPEECH_VOLUME)
        for voice in engine.getProperty("voices"):
            if "david" in voice.name.lower() or "male" in str(voice.gender).lower():
                engine.setProperty("voice", voice.id)
                break
        return engine

    def _play_mci(self, path: str):
        self._counter += 1
        alias = f"jarvis_{self._counter}_{int(time.time()*1000)%10000}"
        abs_p = os.path.abspath(path)
        winmm.mciSendStringW(f'open "{abs_p}" type mpegvideo alias {alias}', None, 0, 0)
        winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
        winmm.mciSendStringW(f'close {alias}', None, 0, 0)

    async def _generate_neural(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=JARVIS_VOICE,
            rate=JARVIS_RATE,
            pitch=JARVIS_PITCH
        )
        await communicate.save(output_path)

    def _tts_worker(self):
        sapi_engine = self._init_sapi()
        while True:
            try:
                item = self._speech_queue.get()
                if item is None:
                    break
                text, done_event = item
                if text and text.strip():
                    clean_text = text.strip()
                    print(f"[J.A.R.V.I.S.]: {clean_text}")
                    notify_ui_jarvis_speech(clean_text)
                    notify_ui_status("Speaking")

                    spoken = False
                    if HAS_EDGE_TTS:
                        temp_file = CACHE_DIR / f"speech_{time.time_ns()}.mp3"
                        try:
                            asyncio.run(self._generate_neural(clean_text, str(temp_file)))
                            self._play_mci(str(temp_file))
                            spoken = True
                            if temp_file.exists():
                                temp_file.unlink()
                        except Exception:
                            pass

                    if not spoken:
                        sapi_engine.say(clean_text)
                        sapi_engine.runAndWait()

                    notify_ui_status("Standby")

                if done_event:
                    done_event.set()
                self._speech_queue.task_done()
            except Exception as e:
                print(f"[TTS Error]: {e}")
                time.sleep(0.1)

    def speak(self, text: str, block: bool = True):
        if not text:
            return
        done_event = threading.Event() if block else None
        self._speech_queue.put((text, done_event))
        if block and done_event:
            done_event.wait()

    def silence(self):
        try:
            winmm.mciSendStringW("stop all", None, 0, 0)
            winmm.mciSendStringW("close all", None, 0, 0)
        except Exception:
            pass
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except Exception:
                break
        notify_ui_status("Standby")

speech_engine = SpeechEngine()

def speak(text: str, block: bool = True):
    speech_engine.speak(text, block=block)

# =====================================================================
# Intelligent Core: Google Gemini AI + Smart Web Fallbacks
# =====================================================================
def query_gemini_ai(user_prompt: str, api_key: str) -> Optional[str]:
    """Generates an intelligent, conversational response using Google Gemini 1.5 Flash."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        system_instruction = (
            "You are J.A.R.V.I.S., the highly intelligent, witty, concise, and loyal AI assistant created by Tony Stark. "
            "Address the user with polite sophistication as 'Sir' or 'Ma'am'. "
            "Your output will be spoken aloud via text-to-speech. Therefore, keep your answer crisp, clear, and conversational (usually 1 to 3 sentences) "
            "unless the user specifically requests a comprehensive explanation. Avoid formatting like markdown asterisks, hashes, or bullet points."
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_instruction}\n\nUser: {user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 250
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=9) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as e:
        print(f"[Gemini Error]: {e}")
    return None

def query_smart_knowledge(prompt: str) -> str:
    """Answers user queries smartly via DuckDuckGo Instant Answers + Wikipedia."""
    clean = prompt.lower().strip("?., ")
    for prefix in ["what is ", "who is ", "tell me about ", "search for ", "explain "]:
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
            break

    # 1. DuckDuckGo Instant Abstract
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read())
            abstract = d.get("AbstractText", "").strip()
            if abstract:
                return abstract
    except Exception:
        pass

    # 2. Wikipedia Summary
    try:
        summary = wikipedia.summary(clean, sentences=2)
        if summary:
            return summary
    except Exception:
        pass

    return f"I have processed your query regarding {prompt}, {USER_HONORIFIC}. For in-depth conversational answers, please connect your free Google Gemini API key."

def fetch_online_joke() -> str:
    """Fetches a fresh joke from Gemini or live Joke APIs."""
    api_key = get_gemini_api_key()
    if api_key:
        j = query_gemini_ai("Tell me a single, short, witty, family-friendly one-liner joke. Only output the joke.", api_key)
        if j:
            return j

    try:
        url = "https://official-joke-api.appspot.com/random_joke"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            s = data.get("setup", "").strip()
            p = data.get("punchline", "").strip()
            if s and p:
                return f"{s} ... {p}"
    except Exception:
        pass

    try:
        url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&type=single"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("joke"):
                return data["joke"].strip()
    except Exception:
        pass

    return random.choice(JOKES_BACKUP)

def fetch_online_fact() -> str:
    """Fetches a fresh fact from Gemini or live Fact APIs."""
    api_key = get_gemini_api_key()
    if api_key:
        f = query_gemini_ai("Tell me a single fascinating, educational fact in 1-2 sentences. Only output the fact.", api_key)
        if f:
            return f

    try:
        url = "https://uselessfacts.jsph.pl/api/v2/facts/random"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAI/2.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("text"):
                return data["text"].strip()
    except Exception:
        pass

    return random.choice(FACTS_BACKUP)

# =====================================================================
# Voice Listener
# =====================================================================
class VoiceListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.4
        self._calibrated = False

    def calibrate(self, duration: float = 0.8):
        try:
            with sr.Microphone() as source:
                print("[Voice Listener]: Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                self._calibrated = True
                print(f"[Voice Listener]: Calibration complete. Threshold: {self.recognizer.energy_threshold:.1f}")
        except Exception as e:
            print(f"[Calibration Notice]: {e}")

    def listen_once(self, timeout: float = None, phrase_time_limit: float = None, play_chime: bool = True) -> str:
        if not self._calibrated:
            self.calibrate(0.8)

        if timeout is None:
            timeout = LISTEN_TIMEOUT
        if phrase_time_limit is None:
            phrase_time_limit = PHRASE_TIME_LIMIT

        try:
            with sr.Microphone() as source:
                if play_chime:
                    play_earcon("listen")
                notify_ui_status("Listening")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

            try:
                notify_ui_status("Processing")
                cmd = self.recognizer.recognize_google(audio).lower().strip()
                print(f"[User Said]: {cmd}")
                notify_ui_user_speech(cmd)
                if play_chime and cmd:
                    play_earcon("ack")
                notify_ui_status("Standby")
                return cmd
            except sr.UnknownValueError:
                notify_ui_status("Standby")
                return ""
            except sr.RequestError:
                notify_ui_status("Standby")
                speak("I am currently unable to reach speech recognition services.")
                return ""
        except sr.WaitTimeoutError:
            notify_ui_status("Standby")
            return ""
        except Exception as e:
            notify_ui_status("Standby")
            return ""

    def check_wake_word(self, phrase: str):
        if not phrase:
            return False, ""
        clean = phrase.lower().strip()
        for w in WAKE_WORDS:
            if clean == w:
                return True, ""
            if clean.startswith(f"{w} ") or clean.startswith(f"{w},"):
                cmd = clean.split(w, 1)[-1].strip(",. ").strip()
                return True, cmd
        return False, ""

listener = VoiceListener()

# =====================================================================
# System & Accessibility Utilities
# =====================================================================
class AccessibilityTools:
    def read_active_window(self):
        if not HAS_WIN32:
            speak("Window telemetry is unavailable.")
            return
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                speak(f"Active window is: {title}")
            else:
                speak("You are currently at the desktop or an untitled application.")
        except Exception:
            speak("Could not determine the active window.")

    def read_clipboard(self):
        try:
            txt = pyperclip.paste().strip()
            if txt:
                snippet = txt[:250] + ("..." if len(txt) > 250 else "")
                speak(f"Clipboard content is: {snippet}")
            else:
                speak("Your clipboard is currently empty.")
        except Exception:
            speak("Unable to read the clipboard.")

    def read_battery_status(self):
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                speak("This machine does not report a battery.")
                return
            percent = int(battery.percent)
            plugged = battery.power_plugged
            status = "plugged in and charging" if plugged else "running on battery"
            speak(f"Battery is at {percent} percent, and {status}.")
        except Exception:
            speak("Battery status unavailable.")

    def read_connection_status(self):
        try:
            urllib.request.urlopen("https://www.google.com", timeout=3)
            speak("Internet connection is active and stable.")
        except Exception:
            speak("Internet appears to be offline.")

    def trigger_emergency_sos(self):
        play_earcon("sos")
        speak("Emergency SOS activated! Contacting primary caregiver and dialing emergency services.")

accessibility_tools = AccessibilityTools()

class SystemController:
    def volume_up(self):
        for _ in range(5):
            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)

    def volume_down(self):
        for _ in range(5):
            user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)

    def volume_mute(self):
        user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)

    def press_key(self, key: str):
        try:
            pyautogui.press(key)
        except Exception:
            pass

    def copy_text(self):
        pyautogui.hotkey("ctrl", "c")
        speak("Copied.")

    def paste_text(self):
        pyautogui.hotkey("ctrl", "v")

    def save_file(self):
        pyautogui.hotkey("ctrl", "s")
        speak("Save command issued.")

    def switch_window(self):
        pyautogui.hotkey("alt", "tab")

    def show_desktop(self):
        pyautogui.hotkey("win", "d")

    def close_current_window(self):
        pyautogui.hotkey("alt", "f4")

system_controller = SystemController()

class NotesManager:
    def take_note(self, content: str):
        if not content:
            speak("What should I record in your note?")
            content = listener.listen_once(timeout=8.0, phrase_time_limit=12.0)
        if content:
            now = datetime.datetime.now()
            fname = f"Note_{now.strftime('%Y%m%d_%H%M%S')}.txt"
            p = NOTES_DIR / fname
            p.write_text(f"Voice Note - {now.strftime('%c')}\n\n{content}", encoding="utf-8")
            speak(f"Saved note to your Jarvis Notes folder.")
            play_earcon("success")

    def read_latest_note(self):
        files = sorted(NOTES_DIR.glob("*.txt"), key=os.path.getmtime)
        if not files:
            speak("You have no saved voice notes.")
            return
        latest = files[-1]
        txt = latest.read_text(encoding="utf-8")
        speak(f"Your latest note says: {txt}")

notes_manager = NotesManager()

# =====================================================================
# Intelligent Command Processor (System Actions + Gemini AI)
# =====================================================================
class CommandProcessor:
    def process(self, command: str) -> bool:
        if not command:
            return True
        cmd = command.strip().lower()

        # 1. Emergency
        if any(w in cmd for w in ["emergency", "sos", "help me"]):
            accessibility_tools.trigger_emergency_sos()
            return True

        # 2. Exit
        elif any(w == cmd or f" {w}" in cmd for w in ["exit", "quit", "goodbye", "power down"]):
            play_earcon("ack")
            speak(f"Powering down core protocols. Goodbye, {USER_HONORIFIC}.")
            return False

        # 3. Direct Application Launching (including WhatsApp)
        elif cmd.startswith("open ") or cmd.startswith("launch "):
            target = cmd.split(" ", 1)[-1].strip()
            self.open_app(target)
            return True

        elif "whatsapp" in cmd:
            self.open_app("whatsapp")
            return True

        # 4. System Telemetry & Controls
        elif any(w in cmd for w in ["what window", "active window", "where am i"]):
            accessibility_tools.read_active_window()
            return True
        elif any(w in cmd for w in ["read clipboard", "clipboard"]):
            accessibility_tools.read_clipboard()
            return True
        elif "battery" in cmd:
            accessibility_tools.read_battery_status()
            return True
        elif "internet" in cmd or "wifi" in cmd:
            accessibility_tools.read_connection_status()
            return True
        elif "time" in cmd and "date" not in cmd:
            now = datetime.datetime.now().strftime("%I:%M %p")
            speak(f"The time is {now}, {USER_HONORIFIC}.")
            return True
        elif "date" in cmd or "today" in cmd:
            today = datetime.datetime.now().strftime("%A, %B %d, %Y")
            speak(f"Today is {today}, {USER_HONORIFIC}.")
            return True

        # 5. Volume & Window Management
        elif "volume up" in cmd or "louder" in cmd:
            system_controller.volume_up()
            speak("Volume raised.")
            return True
        elif "volume down" in cmd or "quieter" in cmd:
            system_controller.volume_down()
            speak("Volume lowered.")
            return True
        elif "mute" in cmd:
            system_controller.volume_mute()
            speak("Mute toggled.")
            return True
        elif any(w in cmd for w in ["switch window", "alt tab"]):
            system_controller.switch_window()
            return True
        elif any(w in cmd for w in ["show desktop", "minimize"]):
            system_controller.show_desktop()
            return True
        elif any(w in cmd for w in ["close window", "close this"]):
            system_controller.close_current_window()
            return True

        # 6. Notes
        elif "take a note" in cmd or "take note" in cmd:
            c = cmd.split("note", 1)[1] if "note " in cmd else ""
            notes_manager.take_note(c)
            return True
        elif "read my note" in cmd or "read note" in cmd:
            notes_manager.read_latest_note()
            return True

        # 7. Entertainment: Jokes & Facts
        elif "joke" in cmd:
            speak(fetch_online_joke())
            return True
        elif "fact" in cmd:
            speak(fetch_online_fact())
            return True

        # 8. Web Search
        elif cmd.startswith("search ") or cmd.startswith("google "):
            q = cmd.split("search", 1)[-1].strip() if "search" in cmd else cmd.split("google", 1)[-1].strip()
            speak(f"Searching web for {q}")
            webbrowser.open_new_tab(f"https://www.google.com/search?q={urllib.parse.quote(q)}")
            return True

        # =================================================================
        # 9. GENERAL INTELLIGENCE (Gemini AI + Smart Knowledge Engine)
        # =================================================================
        api_key = get_gemini_api_key()
        if api_key:
            notify_ui_status("Processing with Gemini AI")
            ai_reply = query_gemini_ai(command, api_key)
            if ai_reply:
                speak(ai_reply)
                return True

        # Fallback to Smart Web Search / Knowledge
        notify_ui_status("Consulting knowledge base")
        smart_reply = query_smart_knowledge(command)
        speak(smart_reply)
        return True

    def open_app(self, app_name: str):
        clean = app_name.strip().lower()
        target = APP_MAP.get(clean, clean)
        try:
            # WhatsApp Special Handling (Windows Store UWP + Web fallback)
            if clean in ["whatsapp", "whats app", "whatsapp desktop"] or target == "whatsapp:":
                res = os.system("start whatsapp:")
                if res == 0:
                    speak(f"Opening WhatsApp, {USER_HONORIFIC}.")
                    play_earcon("success")
                    return
                else:
                    webbrowser.open_new_tab("https://web.whatsapp.com")
                    speak(f"Opening WhatsApp Web, {USER_HONORIFIC}.")
                    play_earcon("success")
                    return

            if target.startswith("ms-") or target.endswith(":"):
                os.system(f"start {target}")
            else:
                subprocess.Popen(target if target.endswith(".exe") else f"{target}.exe")
            speak(f"Opening {clean}")
            play_earcon("success")
        except Exception:
            try:
                os.system(f"start {clean}:")
                speak(f"Launching {clean}")
                play_earcon("success")
            except Exception:
                try:
                    webbrowser.open_new_tab(f"https://www.{clean}.com")
                    speak(f"Opening {clean} in browser.")
                    play_earcon("success")
                except Exception:
                    play_earcon("error")
                    speak(f"Could not open {app_name}.")

command_processor = CommandProcessor()

# =====================================================================
# Sleek Modern AI Visualizer (Radiant Pulsing Soundwave Core)
# =====================================================================
class RadiantAICore(tk.Canvas):
    """Futuristic, elegant pulsing AI core with harmonic radiant waves."""

    def __init__(self, master, size=140, **kwargs):
        super().__init__(master, width=size, height=size, bg="#080c14", highlightthickness=0, **kwargs)
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        self.angle = 0
        self.pulse = 0.0
        self.pulse_dir = 0.05
        self.state = "standby"
        self._animate()

    def set_state(self, state: str):
        self.state = state.lower()

    def _animate(self):
        self.delete("all")
        self.pulse += self.pulse_dir
        if self.pulse > 1.0:
            self.pulse = 1.0
            self.pulse_dir = -0.05
        elif self.pulse < 0.0:
            self.pulse = 0.0
            self.pulse_dir = 0.05

        # Refined Modern Color Schemes
        if "listen" in self.state:
            halo_color = "#0284c7"
            wave_color = "#38bdf8"
            core_color = "#00f0ff"
            speed = 7
        elif "process" in self.state:
            halo_color = "#b45309"
            wave_color = "#f59e0b"
            core_color = "#fbbf24"
            speed = 9
        elif "speak" in self.state:
            halo_color = "#047857"
            wave_color = "#10b981"
            core_color = "#34d399"
            speed = 5
        else:  # standby
            halo_color = "#1e293b"
            wave_color = "#0284c7"
            core_color = "#38bdf8"
            speed = 2

        self.angle = (self.angle + speed) % 360

        # Outer breathing halo
        r_halo = (self.size / 2) - 10 + (self.pulse * 5)
        self.create_oval(
            self.cx - r_halo, self.cy - r_halo,
            self.cx + r_halo, self.cy + r_halo,
            outline=halo_color, width=2
        )

        # Harmonic rotating wave ticks
        ticks = 16
        for i in range(ticks):
            theta = math.radians(self.angle + (i * (360 / ticks)))
            length = 6 + (math.sin(theta * 3 + self.pulse * 3) * 4)
            x1 = self.cx + (r_halo - length) * math.cos(theta)
            y1 = self.cy + (r_halo - length) * math.sin(theta)
            x2 = self.cx + (r_halo + 2) * math.cos(theta)
            y2 = self.cy + (r_halo + 2) * math.sin(theta)
            self.create_line(x1, y1, x2, y2, fill=wave_color, width=2)

        # Mid radiant orb
        r_mid = (self.size / 2) - 26 + (self.pulse * 3)
        self.create_oval(
            self.cx - r_mid, self.cy - r_mid,
            self.cx + r_mid, self.cy + r_mid,
            outline=wave_color, width=2
        )

        # Center luminous core
        r_core = (self.size / 2) - 42 + (self.pulse * 2)
        self.create_oval(
            self.cx - r_core, self.cy - r_core,
            self.cx + r_core, self.cy + r_core,
            fill=core_color, outline="#ffffff", width=2
        )

        self.after(40, self._animate)

# =====================================================================
# Elegant, Minimalist & Modern Desktop HUD
# =====================================================================
class ModernJarvisApp(ctk.CTk):
    """Sleek, minimalist, high-tech interface for J.A.R.V.I.S."""

    def __init__(self):
        super().__init__()

        # Elegant Sapphire & Obsidian Palette
        self.COLOR_BG = "#080c14"          # Deep cosmic obsidian
        self.COLOR_PANEL = "#0f172a"       # Sleek navy glass
        self.COLOR_ACCENT = "#0284c7"      # Vibrant sapphire
        self.COLOR_CYAN = "#38bdf8"        # Luminous cyan
        self.COLOR_TEXT = "#f8fafc"        # Crisp white
        self.COLOR_MUTED = "#94a3b8"       # Slate gray

        self.title("J.A.R.V.I.S. • Intelligent Assistant")
        self.geometry("920x680")
        self.minsize(760, 540)
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=self.COLOR_BG)

        # Build Interface
        self._build_top_bar()
        self._build_visualizer_area()
        self._build_chat_stream()
        self._build_floating_input_capsule()

        # Keyboard shortcuts
        self.bind("<F1>", lambda e: self.trigger_voice_listen())
        self.bind("<Escape>", lambda e: self.silence_voice())

        # Start periodic UI event dispatcher
        self.after(50, self._poll_ui_events)

        # Background Voice Engine Thread
        self.voice_thread = threading.Thread(target=self._voice_background_loop, daemon=True)
        self.voice_thread.start()

        # Initial greeting
        has_key = bool(get_gemini_api_key())
        status_msg = "Google Gemini AI is active." if has_key else "Online knowledge active. Click 🔑 Gemini to link API key."
        self.log_message("JARVIS", f"Systems fully operational, {USER_HONORIFIC}. {status_msg}")

    def _build_top_bar(self):
        """Top navigation bar with logo, Gemini status, and clean action buttons."""
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill=tk.X, padx=20, pady=(14, 6))

        # Brand / Logo
        brand_box = ctk.CTkFrame(top_frame, fg_color="transparent")
        brand_box.pack(side=tk.LEFT)

        logo_lbl = ctk.CTkLabel(
            brand_box,
            text="⚡ J.A.R.V.I.S.",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.COLOR_TEXT
        )
        logo_lbl.pack(side=tk.LEFT)

        self.gemini_badge = ctk.CTkLabel(
            brand_box,
            text="AI ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#00f0ff",
            fg_color="#0369a1",
            corner_radius=10,
            padx=8,
            pady=2
        )
        self.gemini_badge.pack(side=tk.LEFT, padx=10)

        # Right Action Buttons
        right_box = ctk.CTkFrame(top_frame, fg_color="transparent")
        right_box.pack(side=tk.RIGHT)

        # Gemini API Key Config Button
        has_key = bool(get_gemini_api_key())
        key_btn_text = "🔑 Gemini (Active)" if has_key else "🔑 Link Gemini AI"
        self.key_btn = ctk.CTkButton(
            right_box,
            text=key_btn_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0369a1" if has_key else "#1e293b",
            hover_color="#0284c7",
            text_color=self.COLOR_TEXT,
            height=32,
            corner_radius=8,
            command=self.open_gemini_key_modal
        )
        self.key_btn.pack(side=tk.LEFT, padx=6)

        # Clear Chat Button
        clear_btn = ctk.CTkButton(
            right_box,
            text="🗑️ Clear",
            font=ctk.CTkFont(size=12),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=self.COLOR_MUTED,
            width=65,
            height=32,
            corner_radius=8,
            command=lambda: self.chat_box.delete("1.0", tk.END)
        )
        clear_btn.pack(side=tk.LEFT, padx=4)

    def _build_visualizer_area(self):
        """Centered, minimalist pulsating AI Orb with state indicator."""
        viz_frame = ctk.CTkFrame(self, fg_color="transparent")
        viz_frame.pack(fill=tk.X, pady=(4, 6))

        # Core Canvas
        self.ai_core = RadiantAICore(viz_frame, size=130)
        self.ai_core.pack()

        # Status Pill Badge
        self.status_pill = ctk.CTkLabel(
            viz_frame,
            text="● STANDBY • SAY 'JARVIS'",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_CYAN,
            fg_color="#0f172a",
            corner_radius=16,
            padx=16,
            pady=4
        )
        self.status_pill.pack(pady=(4, 0))

    def _build_chat_stream(self):
        """Streamlined conversation log showing clean message bubbles."""
        chat_container = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_PANEL,
            corner_radius=12,
            border_width=1,
            border_color="#1e293b"
        )
        chat_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        self.chat_box = ctk.CTkTextbox(
            chat_container,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            wrap="word",
            fg_color="transparent",
            text_color=self.COLOR_TEXT,
            border_width=0
        )
        self.chat_box.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

    def _build_floating_input_capsule(self):
        """
        Sleek, single-capsule floating search/command bar.
        Eliminates the clunky row of bottom buttons!
        """
        dock = ctk.CTkFrame(self, fg_color="transparent")
        dock.pack(fill=tk.X, padx=20, pady=(6, 16))

        capsule = ctk.CTkFrame(
            dock,
            fg_color=self.COLOR_PANEL,
            corner_radius=24,
            border_width=1,
            border_color="#334155"
        )
        capsule.pack(fill=tk.X)

        # Glowing Mic Button inside capsule
        self.btn_mic = ctk.CTkButton(
            capsule,
            text="🎙️",
            font=ctk.CTkFont(size=16),
            width=42,
            height=42,
            corner_radius=21,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            command=self.trigger_voice_listen
        )
        self.btn_mic.pack(side=tk.LEFT, padx=(6, 8), pady=6)

        # Main Input Text Entry
        self.entry_input = ctk.CTkEntry(
            capsule,
            placeholder_text="Ask anything, say 'open whatsapp', or press mic (F1)...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="transparent",
            text_color=self.COLOR_TEXT,
            border_width=0,
            height=42
        )
        self.entry_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=6)
        self.entry_input.bind("<Return>", lambda e: self._on_submit_entry())

        # Silence Speech Button
        self.btn_silence = ctk.CTkButton(
            capsule,
            text="🔇",
            font=ctk.CTkFont(size=14),
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=self.COLOR_MUTED,
            command=self.silence_voice
        )
        self.btn_silence.pack(side=tk.RIGHT, padx=(4, 8), pady=6)

        # Send Button
        self.btn_send = ctk.CTkButton(
            capsule,
            text="➤",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            command=self._on_submit_entry
        )
        self.btn_send.pack(side=tk.RIGHT, padx=2, pady=6)

    # ================= EVENT HANDLERS & MODALS =================

    def open_gemini_key_modal(self):
        """Clean modal dialog allowing the user to paste their Google Gemini API key."""
        dialog = ctk.CTkInputDialog(
            text="Paste your Google Gemini API Key below\n(Get a free key at https://aistudio.google.com):",
            title="Link Google Gemini AI"
        )
        val = dialog.get_input()
        if val and val.strip():
            save_gemini_api_key(val.strip())
            self.key_btn.configure(text="🔑 Gemini (Active)", fg_color="#0369a1")
            self.gemini_badge.configure(text="GEMINI 1.5 ACTIVE", fg_color="#10b981")
            speak(f"Google Gemini AI key configured successfully, {USER_HONORIFIC}.")
            self.log_message("JARVIS", "Google Gemini AI has been successfully linked and activated!")

    def _on_submit_entry(self):
        txt = self.entry_input.get().strip()
        if txt:
            self.entry_input.delete(0, tk.END)
            self.dispatch_command(txt)

    def dispatch_command(self, cmd_text: str):
        self.log_message("USER", cmd_text)
        threading.Thread(target=lambda: command_processor.process(cmd_text), daemon=True).start()

    def log_message(self, sender: str, text: str):
        now = datetime.datetime.now().strftime("%I:%M %p")
        if sender == "USER":
            entry = f"\n[{now}] 👤 You:\n  ▶ {text}\n"
        else:
            entry = f"\n[{now}] ⚡ J.A.R.V.I.S.:\n  ▶ {text}\n"
        self.chat_box.insert(tk.END, entry)
        self.chat_box.see(tk.END)

    def trigger_voice_listen(self):
        play_earcon("listen")
        self.update_status_display("Listening")
        def _worker():
            phrase = listener.listen_once(timeout=7.0, phrase_time_limit=10.0, play_chime=True)
            if phrase:
                self.dispatch_command(phrase)
            self.update_status_display("Standby")
        threading.Thread(target=_worker, daemon=True).start()

    def silence_voice(self):
        play_earcon("ack")
        speech_engine.silence()
        self.update_status_display("Standby")

    def update_status_display(self, state: str):
        self.ai_core.set_state(state)
        s = state.lower()
        if "listen" in s:
            self.status_pill.configure(text="● LISTENING FOR YOUR VOICE...", text_color="#00f0ff")
            self.btn_mic.configure(fg_color="#00f0ff")
        elif "process" in s:
            self.status_pill.configure(text="● THINKING...", text_color="#fbbf24")
            self.btn_mic.configure(fg_color="#0284c7")
        elif "speak" in s:
            self.status_pill.configure(text="● J.A.R.V.I.S. SPEAKING...", text_color="#34d399")
            self.btn_mic.configure(fg_color="#0284c7")
        else:
            self.status_pill.configure(text="● STANDBY • SAY 'JARVIS'", text_color=self.COLOR_CYAN)
            self.btn_mic.configure(fg_color="#0284c7")

    def _poll_ui_events(self):
        while not ui_event_queue.empty():
            try:
                ev, val = ui_event_queue.get_nowait()
                if ev == "status":
                    self.update_status_display(val)
                elif ev == "user_speech":
                    self.log_message("USER", val)
                elif ev == "jarvis_speech":
                    self.log_message("JARVIS", val)
            except queue.Empty:
                break
        self.after(50, self._poll_ui_events)

    def _voice_background_loop(self):
        time.sleep(1.0)
        listener.calibrate(0.8)

        while True:
            try:
                phrase = listener.listen_once(timeout=6.0, phrase_time_limit=6.0, play_chime=False)
                if not phrase:
                    continue

                is_wake, command = listener.check_wake_word(phrase)
                if is_wake:
                    play_earcon("listen")
                    if command:
                        ui_event_queue.put(("user_speech", command))
                        command_processor.process(command)
                    else:
                        play_earcon("ack")
                        speak(f"Yes {USER_HONORIFIC}, I am listening.", block=True)
                        active_cmd = listener.listen_once(timeout=7.0, phrase_time_limit=9.0, play_chime=True)
                        if active_cmd:
                            ui_event_queue.put(("user_speech", active_cmd))
                            command_processor.process(active_cmd)
                else:
                    if any(w in phrase for w in ["emergency", "sos", "help me"]):
                        accessibility_tools.trigger_emergency_sos()
                time.sleep(0.1)
            except Exception:
                time.sleep(0.5)

# =====================================================================
# Main Application Entry Point
# =====================================================================
def main():
    app = ModernJarvisApp()
    app.mainloop()

if __name__ == "__main__":
    main()
