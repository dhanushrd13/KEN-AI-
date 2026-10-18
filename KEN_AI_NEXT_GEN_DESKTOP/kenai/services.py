"""Local-first assistant services. Optional integrations fail with useful messages."""
from __future__ import annotations
import json, os, re, sqlite3, threading, urllib.error, urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

APP_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "KenAI"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "memory.sqlite3"

@contextmanager
def _database():
    connection=sqlite3.connect(DB_PATH)
    try:
        with connection: yield connection
    finally:
        connection.close()

class Memory:
    def __init__(self):
        with _database() as db:
            db.execute("CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT, content TEXT, created TEXT, session_id TEXT)")
            columns={row[1] for row in db.execute("PRAGMA table_info(messages)")}
            if "session_id" not in columns: db.execute("ALTER TABLE messages ADD COLUMN session_id TEXT")
    def create_session(self):
        session_id=str(uuid4())
        with _database() as db:
            db.execute("INSERT INTO conversations(id,title,created) VALUES(?,?,?)",(session_id,"New conversation",datetime.now().isoformat(timespec="seconds")))
        return session_id
    def add(self, role, content, session_id=None):
        with _database() as db:
            if session_id is None: session_id=self.create_session()
            db.execute("INSERT INTO messages(role,content,created,session_id) VALUES(?,?,?,?)", (role, content, datetime.now().isoformat(timespec="seconds"),session_id))
            if role=="user": db.execute("UPDATE conversations SET title=? WHERE id=? AND title='New conversation'",(content.replace("\n"," ")[:56],session_id))
    def recent(self, limit=80, session_id=None):
        with _database() as db:
            if session_id:
                rows=db.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",(session_id,limit)).fetchall()
            else:
                rows=db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return list(reversed(rows))
    def sessions(self, limit=80):
        with sqlite3.connect(DB_PATH) as db:
            return db.execute("SELECT c.id,c.title FROM conversations c WHERE EXISTS(SELECT 1 FROM messages m WHERE m.session_id=c.id) ORDER BY c.created DESC LIMIT ?",(limit,)).fetchall()
    def clear(self):
        with _database() as db: db.execute("DELETE FROM messages")

def ollama_chat(messages, model="qwen3:1.7b", base_url="http://localhost:11434"):
    payload = json.dumps({"model": model, "messages": messages, "stream": False, "think": False}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/api/chat", data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp: data=json.loads(resp.read())
        return data.get("message",{}).get("content", "No response returned by Ollama.")
    except urllib.error.URLError as e:
        raise RuntimeError("Ollama is not responding. Start Ollama and make sure qwen3:1.7b is installed.") from e

def search_web(query):
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=5)
        return [{"title":x.get("title","Result"), "url":x.get("href") or x.get("url"), "body":x.get("body","")} for x in results]
    except ImportError as e: raise RuntimeError("Web search needs the optional package: pip install ddgs") from e
    except Exception as e: raise RuntimeError(f"Web search failed: {e}") from e

def needs_web_lookup(query):
    """Route common time-sensitive questions to live search instead of guessing from a small local model."""
    text=" ".join(re.findall(r"[a-z0-9]+",query.lower()))
    current_terms=("current", "currently", "today", "latest", "right now", "as of", "this week", "this month", "this year", "weather", "news", "price", "score", "standings", "forecast")
    offices=("chief minister", "prime minister", "president", "governor", "mayor", "ceo", "chairman", "leader")
    asks_who=bool(re.search(r"\bwho\s+(is|are)\b",text))
    return any(term in text for term in current_terms) or (asks_who and any(office in text for office in offices))

def weather_for_location(city):
    """Fetch current modelled weather for an explicitly selected city."""
    city=city.strip()
    if len(city)<2: raise RuntimeError("Enter a city or postal code to look up weather.")
    def get_json(url):
        req=urllib.request.Request(url,headers={"User-Agent":"KEN-AI-NEXT-GEN/1.0"})
        with urllib.request.urlopen(req,timeout=15) as response: return json.loads(response.read())
    geo=get_json("https://geocoding-api.open-meteo.com/v1/search?"+urlencode({"name":city,"count":1,"language":"en","format":"json"}))
    places=geo.get("results") or []
    if not places: raise RuntimeError(f"I couldn't find a place matching {city!r}.")
    place=places[0]
    query=urlencode({"latitude":place["latitude"],"longitude":place["longitude"],"current":"temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m","timezone":"auto"})
    data=get_json("https://api.open-meteo.com/v1/forecast?"+query)
    current=data.get("current") or {}
    labels={0:"Clear",1:"Mostly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",56:"Freezing drizzle",57:"Dense freezing drizzle",61:"Light rain",63:"Rain",65:"Heavy rain",66:"Freezing rain",67:"Heavy freezing rain",71:"Light snow",73:"Snow",75:"Heavy snow",77:"Snow grains",80:"Rain showers",81:"Showers",82:"Heavy showers",85:"Snow showers",86:"Heavy snow showers",95:"Thunderstorm",96:"Thunderstorm with hail",99:"Severe thunderstorm with hail"}
    if not current: raise RuntimeError("The weather service returned no current conditions.")
    return {"location":", ".join(x for x in (place.get("name"),place.get("admin1"),place.get("country")) if x),"temperature":current.get("temperature_2m"),"feels_like":current.get("apparent_temperature"),"humidity":current.get("relative_humidity_2m"),"wind":current.get("wind_speed_10m"),"condition":labels.get(current.get("weather_code"),"Current conditions"),"updated":current.get("time"," ")}

def system_stats():
    try:
        import psutil
        return {"cpu": psutil.cpu_percent(interval=0.15), "memory": psutil.virtual_memory().percent, "disk": psutil.disk_usage(Path.home().anchor).percent, "battery": (psutil.sensors_battery().percent if psutil.sensors_battery() else None)}
    except ImportError: return None

_WHISPER_MODELS = {}
_WHISPER_LOCK = threading.Lock()

def audio_input_devices():
    """List available recording devices as (device id, name) pairs."""
    try:
        import sounddevice as sd
    except ImportError as e:
        raise RuntimeError("Voice input packages are missing. Run setup.bat or install_voice.bat.") from e
    try:
        return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d.get("max_input_channels", 0) > 0]
    except Exception as e:
        raise RuntimeError(f"Windows could not list microphone devices: {e}") from e

def format_microphone_error(error):
    message = str(error)
    lower = message.lower()
    if any(term in lower for term in ("microphone recording failed", "no default input", "invalid device", "device unavailable", "input overflow", "portaudio")):
        return ("KEN could not record from that microphone. Open Mic help, enable Microphone access and "
                "‘Let desktop apps access your microphone’ in Windows Privacy settings, then choose an input device and retry.\n\n"
                f"Audio detail: {message}")
    return message

def _whisper_model(size="base"):
    with _WHISPER_LOCK:
        if size not in _WHISPER_MODELS:
            from faster_whisper import WhisperModel
            _WHISPER_MODELS[size] = WhisperModel(size, device="cpu", compute_type="int8")
        return _WHISPER_MODELS[size]

def _record_clip(sd, seconds, rate, device=None):
    try:
        info = sd.query_devices(device, "input") if device is not None else sd.query_devices(kind="input")
        source_rate = int(info.get("default_samplerate") or rate)
        audio = sd.rec(seconds * source_rate, samplerate=source_rate, channels=1, dtype="float32", device=device)
        sd.wait()
        samples = audio.reshape(-1)
        if source_rate != rate:
            import numpy as np
            target_length = int(len(samples) * rate / source_rate)
            source_times = np.arange(len(samples), dtype="float32") / source_rate
            target_times = np.arange(target_length, dtype="float32") / rate
            samples = np.interp(target_times, source_times, samples).astype("float32")
        return samples
    except Exception as e:
        raise RuntimeError(f"Microphone recording failed: {e}") from e

def transcribe_bounded(seconds=8, device=None):
    """Record a finite clip from the chosen input, then transcribe it locally."""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError as e:
        raise RuntimeError("Voice input packages are missing. Close KEN AI, run setup.bat, then reopen the app.") from e
    seconds=max(1,min(8,int(seconds))); rate=16000
    devices = audio_input_devices()
    if not devices: raise RuntimeError("No microphone input devices are available. Check the microphone connection and Windows privacy settings.")
    audio=_record_clip(sd,seconds,rate,device)
    samples=np.asarray(audio,dtype="float32").reshape(-1)
    if not samples.size or float(np.max(np.abs(samples))) < 0.0005:
        return ""
    model=_whisper_model("base")
    segments,_=model.transcribe(samples,language="en",vad_filter=True,beam_size=1)
    return " ".join(s.text.strip() for s in segments).strip()

def listen_for_wake_word(stop_event, device=None):
    """Listen in stoppable 3-second clips for a spoken wake word, then capture a bounded command."""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError as e: raise RuntimeError("Wake-word packages are missing. Close KEN AI, run install_voice.bat, then reopen the app.") from e
    rate=16000
    if not audio_input_devices(): raise RuntimeError("No microphone input devices are available. Check the microphone connection and Windows privacy settings.")
    model=_whisper_model("tiny.en"); overlap=np.zeros(0,dtype="float32")
    while not stop_event.is_set():
        audio=_record_clip(sd,3,rate,device)
        if stop_event.is_set(): return ""
        clip=np.asarray(audio).reshape(-1); sample=np.concatenate((overlap,clip)); overlap=clip[-rate:]
        segments,_=model.transcribe(sample,language="en",vad_filter=True,beam_size=1)
        text=" ".join(s.text.strip() for s in segments).lower()
        normalized=" ".join("".join(ch if ch.isalnum() else " " for ch in text).split())
        words=set(normalized.split())
        if words.intersection({"hello","hi","ken"}) or "wake up" in normalized or "wake up world" in normalized:
            try:
                import winsound
                winsound.Beep(880,180)
            except Exception: pass
            trigger_words={"hello","hi","ken","wake","up","world"}
            remainder=" ".join(word for word in normalized.split() if word not in trigger_words).strip()
            if remainder: return remainder
            command=_record_clip(sd,8,rate,device)
            segments,_=model.transcribe(np.asarray(command).reshape(-1),language="en",vad_filter=True,beam_size=1)
            return " ".join(s.text.strip() for s in segments).strip()
    return ""

def speak(text):
    try: import pyttsx3
    except ImportError as e: raise RuntimeError("Speech output is missing. Close KEN AI, run install_voice.bat, then reopen the app.") from e
    def run():
        engine=pyttsx3.init(); engine.say(text[:2500]); engine.runAndWait()
    threading.Thread(target=run,daemon=True).start()

def summarize_file(path, history, model="qwen3:1.7b"):
    p=Path(path); ext=p.suffix.lower()
    try:
        if ext in (".txt", ".md", ".py", ".json", ".csv", ".log"):
            content=p.read_text(encoding="utf-8",errors="replace")[:18000]
        elif ext==".pdf":
            from pypdf import PdfReader
            content="\n".join(page.extract_text() or "" for page in PdfReader(str(p)).pages)[:18000]
        elif ext==".docx":
            from docx import Document
            content="\n".join(x.text for x in Document(str(p)).paragraphs)[:18000]
        else: raise RuntimeError("Supported documents: TXT, Markdown, PDF, DOCX, CSV, JSON, and source text files.")
    except ImportError as e: raise RuntimeError("PDF/DOCX support needs optional document packages. See README.") from e
    if not content.strip(): raise RuntimeError("No readable text was found in that document.")
    return ollama_chat([{"role":"system","content":"Summarize the supplied document accurately. Cite section names or page numbers when visible. Do not invent details."},{"role":"user","content":f"Summarize this local file ({p.name}):\n\n{content}"}],model)

