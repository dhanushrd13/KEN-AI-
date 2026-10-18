# KEN AI NEXT GEN

KEN AI is a local-first Windows desktop assistant with the dark navy and red-glow dashboard, animated central KEN core, chat history, computer stats, weather, file panel, voice input, and a bottom chat bar.

## What works

- Local chat and document summaries through Ollama using `qwen3:1.7b`.
- Type in the message box and press Enter or Send. Chat is not locked behind voice controls.
- Optional automatic wake listening while KEN is open. It listens in stoppable three-second microphone clips for **hello**, **hi**, **ken**, or **wake up**. After the wake phrase, say a request within the next bounded eight-second recording. If you say the request in the same phrase, KEN attempts to pass the words after the wake phrase as your request. Click the wake button to pause/resume.
- Manual **Speak** recording is limited to eight seconds and locally transcribed with faster-whisper. A microphone selector and Windows microphone privacy help are included.
- KEN says “Hi Chief, I am KEN. How could I assist you?” on launch and can speak replies when speech output is available.
- Current weather through Open-Meteo, live CPU/memory/storage/battery status, and local conversation history.
- Browse PC opens the Windows file picker from the drive root. KEN opens the selected file using its normal Windows app; Summarize sends supported selected document text to the local Ollama model. KEN does not scan your entire laptop automatically.
- WhatsApp Web opens inside KEN using Qt WebEngine. Sign in with WhatsApp there to see your live chat list and use WhatsApp. Its browser cookies are stored locally under `%LOCALAPPDATA%\KenAI\whatsapp-profile`. KEN does not copy WhatsApp messages into its own memory.
- Web search returns result titles, summaries, and source URLs.
- Questions about current officeholders and other time-sensitive topics (for example current news, prices, scores, weather, or “latest” facts) automatically show web result snippets and source URLs instead of asking the small local model to guess. Officeholder detection tolerates common spelling mistakes. If search fails, KEN reports that rather than silently making up an answer.
- Setup creates a **KEN AI** desktop shortcut with the KEN icon after dependencies install successfully.

Music playback, call history, screen recording, and device toggles are omitted because there is no connected implementation for them. KEN drafts nothing and sends no messages to WhatsApp on your behalf.

## Install and launch

1. Extract this folder somewhere you intend to keep it. The desktop shortcut points to this folder, so avoid moving it after setup.
2. Install Ollama for Windows and make sure it is running.
3. Double-click `setup.bat`. It reuses a working `.venv`, prefers Python 3.14, falls back to 3.11, then installs the requirements and creates the desktop shortcut.
4. In a terminal, run `ollama pull qwen3:1.7b` once if the model is not installed yet.
5. Double-click the **KEN AI** icon on the Desktop. You can also use `run.bat` inside the folder.

`setup.bat` is needed once for each extracted project folder. After it completes, use the desktop icon for normal launches.

## Voice troubleshooting

- In Windows **Settings → Privacy & security → Microphone**, enable **Microphone access** and **Let desktop apps access your microphone**.
- Open KEN and choose the microphone from the top selector. Use the refresh control if you just connected it.
- The first transcription may download a local Whisper model. Keep internet available for that first download.
- If automatic wake listening reports a microphone error, grant Windows permission and restart KEN. KEN pauses automatic wake mode after a microphone error rather than showing repeated popups.
- Wake listening runs only while KEN is open. It is not a background service and does not start with Windows.

## WhatsApp

Click **WhatsApp Web** in the shortcut panel or the phone icon in the left rail, then sign in inside KEN. If the sign-in page cannot be used in the embedded view on a particular machine, use **Open in browser** in the WhatsApp toolbar. WhatsApp account and network availability are controlled by WhatsApp.

## Notes

- Weather sends the city name you enter to Open-Meteo.
- Web search needs internet access.
- Summaries run through local Ollama; supported formats include TXT, Markdown, PDF, DOCX, CSV, JSON, logs, and source text.
- Windows controls microphone permissions. Hardware, Ollama, WhatsApp login, and external API access have not been runtime-tested on your computer.

## Files

```text
KEN_AI_NEXT_GEN_DESKTOP/
├── main.py
├── kenai/
│   ├── __init__.py
│   ├── app.py
│   └── services.py
├── requirements.txt
├── requirements-voice.txt
├── setup.bat
├── run.bat
├── install_voice.bat
├── create_desktop_shortcut.vbs
├── kenai.ico
└── README.md
```
