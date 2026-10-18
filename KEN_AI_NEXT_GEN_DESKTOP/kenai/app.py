from __future__ import annotations
import os, re, sys, threading, webbrowser
from datetime import datetime
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSettings, QUrl, QRectF
from PySide6.QtGui import QFont, QDesktopServices, QPainter, QPen, QRadialGradient, QColor
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QLabel,QPushButton,QLineEdit,QTextEdit,QVBoxLayout,QHBoxLayout,QGridLayout,QListWidget,QListWidgetItem,QScrollArea,QProgressBar,QFileDialog,QMessageBox,QComboBox,QCheckBox,QDialog,QDialogButtonBox,QSizePolicy)
from . import services

STYLE='''
* {font-family:"Segoe UI";color:#f7edf0;} QWidget{background:#08080d;}
QFrame#sidebar{background:#0a090e;border-right:1px solid #28161d;}
QFrame#chatpanel,QFrame#card{background:#100d13;border:1px solid #38212a;border-radius:15px;}
QLabel#muted{color:#aa929b;} QLabel#tiny{color:#bf9fa8;font-size:11px;} QLabel#section{color:#fff0f2;font-size:15px;font-weight:600;}
QPushButton{background:#1b1117;border:1px solid #452530;border-radius:10px;padding:8px 11px;color:#fff0f2;}
QPushButton:hover{border-color:#fa5262;background:#29131a;} QPushButton#accent{background:#a9293c;border:1px solid #fa5867;font-weight:600;}
QPushButton#accent:hover{background:#c63549;} QPushButton#nav{background:transparent;border:1px solid transparent;color:#c6abb2;padding:7px;}
QPushButton#nav:hover,QPushButton#nav[active="true"]{background:#261018;border-color:#54232d;color:#fff;}
QLineEdit,QTextEdit,QComboBox{background:#0b090f;border:1px solid #452530;border-radius:10px;padding:9px 11px;selection-background-color:#b93649;}
QLineEdit:focus,QTextEdit:focus,QComboBox:focus{border:1px solid #ff5266;background:#110c12;} QLineEdit{min-height:24px;}
QListWidget{background:transparent;border:0;outline:0;} QListWidget::item{padding:9px 10px;border-radius:9px;}
QListWidget::item:selected,QListWidget::item:hover{background:#29151d;color:#fff;}
QProgressBar{background:#261b22;border:0;border-radius:5px;height:7px;text-align:center;} QProgressBar::chunk{background:#f04b5c;border-radius:5px;}
QScrollArea{border:0;background:transparent;}
'''

class Signals(QObject):
    done=Signal(object,object); stats=Signal(object); voice=Signal(object,object); weather=Signal(object,object)

class Core(QWidget):
    def __init__(self):
        super().__init__(); self.phase=0; self.setMinimumSize(250,230); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); c=self.rect().center(); radius=min(self.width(),self.height())*.39
        g=QRadialGradient(c,radius*1.5); g.setColorAt(0,QColor(205,27,52,65)); g.setColorAt(.55,QColor(83,13,26,20)); g.setColorAt(1,QColor(8,8,13,0)); p.fillRect(self.rect(),g)
        for i in range(5):
            r=radius*(.65+i*.105); p.setPen(QPen(QColor(250,69,87,(105,55,90,42,24)[i]),2 if i in (0,2) else 1)); p.drawEllipse(QRectF(c.x()-r,c.y()-r,r*2,r*2))
        p.setPen(QPen(QColor(255,88,105,220),2)); p.drawArc(QRectF(c.x()-radius,c.y()-radius,2*radius,2*radius),self.phase*16*8,112*16)
        p.setPen(QColor('#fff0e2')); f=p.font(); f.setPointSize(max(18,min(30,int(radius/7)))); f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,6); f.setBold(True); p.setFont(f); p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'KEN AI')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('KEN AI NEXT GEN'); self.resize(1580,940); self.setMinimumSize(1024,680)
        self.memory=services.Memory(); self.current_session=self.memory.create_session(); self.settings=QSettings('KEN AI','KEN AI NEXT GEN'); self.signals=Signals()
        self.signals.done.connect(self.on_done); self.signals.stats.connect(self.on_stats); self.signals.voice.connect(self.on_voice); self.signals.weather.connect(self.on_weather)
        self.busy=False; self.voice_active=False; self.wake_stop=None; self.wake_cancelled=False; self.auto_wake=True; self.tts=True
        self._build(); self._load_history()
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(75)
        self.stat_timer=QTimer(self); self.stat_timer.timeout.connect(self.refresh_stats); self.stat_timer.start(8000)
        self.clock_timer=QTimer(self); self.clock_timer.timeout.connect(self.update_clock); self.clock_timer.start(1000)
        self.refresh_stats(); self.update_clock(); QTimer.singleShot(850,self.startup_greeting); QTimer.singleShot(250,self.input.setFocus); QTimer.singleShot(5000,self.start_wake_word)
        city=self.settings.value('weather_city','')
        if city: self.city_input.setText(city); QTimer.singleShot(1300,self.load_weather)

    def card(self,title,subtitle=None):
        f=QFrame(objectName='card'); v=QVBoxLayout(f); v.setContentsMargins(13,11,13,12); v.setSpacing(7); h=QHBoxLayout(); t=QLabel(title,objectName='section'); h.addWidget(t); h.addStretch()
        if subtitle: h.addWidget(QLabel(subtitle,objectName='tiny'))
        v.addLayout(h); return f,v

    def _build(self):
        root=QWidget(); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(9,9,9,9); outer.setSpacing(9)
        nav=QFrame(objectName='sidebar'); nav.setFixedWidth(66); nv=QVBoxLayout(nav); nv.setContentsMargins(5,9,5,9); nv.setSpacing(6)
        logo=QPushButton('K'); logo.setObjectName('accent'); logo.setFixedSize(48,48); logo.setToolTip('KEN AI NEXT GEN'); nv.addWidget(logo,0,Qt.AlignmentFlag.AlignHCenter); nv.addSpacing(10)
        for icon,name in [('⌂','Home'),('◷','Chat'),('▤','Files'),('☏','WhatsApp'),('⚙','Settings')]:
            b=QPushButton(icon); b.setObjectName('nav'); b.setProperty('active',name=='Home'); b.setToolTip(name); b.setFixedSize(46,44); b.clicked.connect(lambda _,n=name:self.navigate(n)); nv.addWidget(b,0,Qt.AlignmentFlag.AlignHCenter)
        nv.addStretch(); nv.addWidget(QLabel('LOCAL',objectName='tiny'),0,Qt.AlignmentFlag.AlignHCenter); outer.addWidget(nav)
        chats=QFrame(objectName='chatpanel'); chats.setFixedWidth(260); cv=QVBoxLayout(chats); cv.setContentsMargins(13,13,13,13); cv.setSpacing(9)
        ch=QHBoxLayout(); ch.addWidget(QLabel('◌  Chat',objectName='section')); ch.addStretch(); plus=QPushButton('＋'); plus.setFixedSize(36,34); plus.setToolTip('Start a new chat'); plus.clicked.connect(self.new_chat); ch.addWidget(plus); cv.addLayout(ch)
        self.chat_search=QLineEdit(); self.chat_search.setPlaceholderText('⌕  Search conversations…'); self.chat_search.textChanged.connect(self.filter_sessions); cv.addWidget(self.chat_search)
        self.session_list=QListWidget(); self.session_list.itemClicked.connect(self.select_session); cv.addWidget(self.session_list,1)
        cv.addWidget(QLabel('Your chats stay on this computer.',objectName='tiny')); outer.addWidget(chats)
        page=QVBoxLayout(); page.setContentsMargins(1,0,0,0); page.setSpacing(8); outer.addLayout(page,1)
        header=QHBoxLayout(); header.addWidget(QLabel('KEN AI  /  NEXT GEN',objectName='muted')); header.addStretch(); header.addWidget(QLabel('MIC',objectName='tiny'))
        self.mic_devices=QComboBox(); self.mic_devices.setMinimumWidth(138); self.mic_devices.setMaximumWidth(200); self.mic_devices.setToolTip('Choose which microphone KEN records from'); self.refresh_microphones(True); header.addWidget(self.mic_devices)
        refresh_mic=QPushButton('↻'); refresh_mic.setToolTip('Refresh the list of connected microphones'); refresh_mic.clicked.connect(self.refresh_microphones); header.addWidget(refresh_mic)
        help_button=QPushButton('Mic help'); help_button.clicked.connect(self.open_microphone_settings); header.addWidget(help_button)
        self.time_label=QLabel(); self.time_label.setObjectName('tiny'); header.addWidget(self.time_label)
        self.model=QLabel('●  qwen3:1.7b · Ollama'); self.model.setStyleSheet('color:#ff6876'); header.addWidget(self.model); page.addLayout(header)
        content=QHBoxLayout(); content.setSpacing(9); page.addLayout(content,1)
        center=QVBoxLayout(); center.setSpacing(6); content.addLayout(center,3)
        greet=QLabel("Good to see you, Chief<br><span style='font-size:14px;color:#c2aab2'>Hi Chief, I am KEN. How could I assist you today?</span>"); greet.setAlignment(Qt.AlignmentFlag.AlignCenter); greet.setStyleSheet('font-size:23px;font-weight:500;padding-top:3px'); center.addWidget(greet)
        wave=QLabel('—   ·   ▂   ▄   ▇   ▄   ▂   ·   —   ·   ▃   ▆   ▃   ·   —'); wave.setAlignment(Qt.AlignmentFlag.AlignCenter); wave.setStyleSheet('color:#fb5265;font-size:19px;letter-spacing:4px'); center.addWidget(wave)
        self.core=Core(); center.addWidget(self.core,4)
        self.status=QLabel('Ready when you are · local assistant'); self.status.setObjectName('muted'); self.status.setAlignment(Qt.AlignmentFlag.AlignCenter); self.status.setMaximumHeight(22); center.addWidget(self.status)
        self.chatlog=QTextEdit(); self.chatlog.setReadOnly(True); self.chatlog.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.chatlog.setMinimumHeight(92); self.chatlog.setMaximumHeight(140); self.chatlog.setPlaceholderText('Your conversation will appear here…'); center.addWidget(self.chatlog)
        entry=QHBoxLayout(); entry.setSpacing(7); self.input=QLineEdit(); self.input.setMinimumHeight(48); self.input.setPlaceholderText('Ask KEN anything…  (press Enter to send)'); self.input.setFocusPolicy(Qt.FocusPolicy.StrongFocus); self.input.returnPressed.connect(self.send); entry.addWidget(self.input,1)
        self.mic_button=QPushButton('🎙 Speak'); self.mic_button.setMinimumHeight(46); self.mic_button.setToolTip('Record one command for at most 8 seconds and transcribe locally'); self.mic_button.clicked.connect(self.voice_input); entry.addWidget(self.mic_button)
        self.wake_button=QPushButton('Wake: starting…'); self.wake_button.setMinimumHeight(46); self.wake_button.setToolTip('KEN listens in short microphone clips for “hello”, “hi”, “ken”, or “wake up”. Click to pause or resume.'); self.wake_button.clicked.connect(self.toggle_wake_word); entry.addWidget(self.wake_button)
        send=QPushButton('Send  ↑'); send.setObjectName('accent'); send.setMinimumHeight(46); send.clicked.connect(self.send); entry.addWidget(send); center.addLayout(entry)
        right_scroll=QScrollArea(); right_scroll.setWidgetResizable(True); right_scroll.setMinimumWidth(255); right_scroll.setMaximumWidth(330); right_widget=QWidget(); right=QVBoxLayout(right_widget); right.setContentsMargins(0,0,2,0); right.setSpacing(9); right_scroll.setWidget(right_widget); content.addWidget(right_scroll,1)
        f,v=self.card('Device stats','LIVE'); self.stat_labels={}
        for key,label in [('cpu','CPU'),('memory','Memory'),('disk','Storage')]:
            row=QHBoxLayout(); row.addWidget(QLabel(label)); row.addStretch(); val=QLabel('—',objectName='tiny'); row.addWidget(val); v.addLayout(row); bar=QProgressBar(); bar.setRange(0,100); bar.setTextVisible(False); v.addWidget(bar); self.stat_labels[key]=(val,bar)
        self.battery=QLabel('Battery · reading…',objectName='tiny'); v.addWidget(self.battery); right.addWidget(f)
        f,v=self.card('Weather','Open-Meteo'); self.weather_info=QLabel('Add a city to see current conditions.'); self.weather_info.setObjectName('muted'); self.weather_info.setWordWrap(True); v.addWidget(self.weather_info)
        wr=QHBoxLayout(); self.city_input=QLineEdit(); self.city_input.setPlaceholderText('City name'); self.city_input.returnPressed.connect(self.load_weather); wr.addWidget(self.city_input,1); wb=QPushButton('↻'); wb.setToolTip('Update weather'); wb.clicked.connect(self.load_weather); wr.addWidget(wb); v.addLayout(wr); right.addWidget(f)
        f,v=self.card('Your files','Documents folder'); self.filelist=QListWidget(); self.filelist.setMaximumHeight(145); self.filelist.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.filelist.itemDoubleClicked.connect(lambda _:self.open_selected_file()); v.addWidget(self.filelist)
        acts=QHBoxLayout(); op=QPushButton('Open'); op.clicked.connect(self.open_selected_file); browse=QPushButton('Browse PC'); browse.clicked.connect(self.open_file); sm=QPushButton('Summarize'); sm.clicked.connect(self.summarize_file); acts.addWidget(op); acts.addWidget(browse); acts.addWidget(sm); v.addLayout(acts); right.addWidget(f); self.refresh_files()
        f,v=self.card('Shortcuts'); grid=QGridLayout(); grid.setSpacing(6)
        for i,(label,fn) in enumerate([('＋ New chat',self.new_chat),('⌕ Web search',self.web_search),('▤ Documents',self.open_documents),('☏ WhatsApp Web',self.open_whatsapp)]):
            b=QPushButton(label); b.clicked.connect(fn); grid.addWidget(b,i//2,i%2)
        v.addLayout(grid); self.ttscheck=QCheckBox('Speak greeting and replies'); self.ttscheck.setChecked(True); self.ttscheck.toggled.connect(lambda checked:setattr(self,'tts',checked)); v.addWidget(self.ttscheck); right.addWidget(f); right.addStretch()

    def refresh_microphones(self,initial=False):
        previous=str(self.settings.value('microphone_device','default')); self.mic_devices.blockSignals(True); self.mic_devices.clear(); self.mic_devices.addItem('System default mic','default')
        try:
            for device_id,name in services.audio_input_devices(): self.mic_devices.addItem(name[:34],str(device_id))
        except Exception as exc: self.mic_devices.setToolTip(f'Microphone discovery failed: {exc}')
        idx=self.mic_devices.findData(previous)
        if idx>=0: self.mic_devices.setCurrentIndex(idx)
        self.mic_devices.blockSignals(False)
        if not getattr(self,'_mic_signal_connected',False):
            self.mic_devices.currentIndexChanged.connect(self.save_microphone); self._mic_signal_connected=True
        if initial and self.mic_devices.count()==1: self.mic_devices.setToolTip('No microphone listed. Check Windows microphone privacy settings, then restart KEN AI.')

    def save_microphone(self): self.settings.setValue('microphone_device',self.mic_devices.currentData())
    def microphone_device(self):
        value=self.mic_devices.currentData(); return None if value in (None,'default') else int(value)
    def open_microphone_settings(self):
        QDesktopServices.openUrl(QUrl('ms-settings:privacy-microphone'))
        self.status.setText('Enable Microphone access and Let desktop apps access your microphone in Windows settings')
    def tick(self): self.core.phase=(self.core.phase+1)%45; self.core.update()
    def update_clock(self): self.time_label.setText(datetime.now().astimezone().strftime('%a, %b %d  ·  %I:%M %p'))

    def _load_history(self):
        sessions=self.memory.sessions()
        if sessions: self.current_session=sessions[0][0]
        self.load_session_list(); self.render_session(self.current_session)
    def load_session_list(self):
        query=self.chat_search.text().strip().lower() if hasattr(self,'chat_search') else ''; self.session_list.clear()
        for session_id,title in self.memory.sessions(100):
            if query and query not in title.lower(): continue
            item=QListWidgetItem('◉   '+title); item.setData(Qt.ItemDataRole.UserRole,session_id); item.setToolTip(title); self.session_list.addItem(item)
            if session_id==self.current_session: item.setSelected(True)
    def filter_sessions(self,_): self.load_session_list()
    def select_session(self,item):
        session_id=item.data(Qt.ItemDataRole.UserRole)
        if session_id: self.current_session=session_id; self.render_session(session_id); self.input.setFocus()
    def render_session(self,session_id):
        self.chatlog.clear()
        for role,text in self.memory.recent(80,session_id): self.append_message(role,text,False)
    def startup_greeting(self):
        greeting='Hi Chief, I am KEN. How could I assist you?'
        if not self.memory.recent(1,self.current_session): self.append_message('assistant',greeting)
        if self.tts:
            try: services.speak(greeting)
            except Exception as exc: self.status.setText(f'Speech output unavailable: {exc}')
    def append_message(self,role,text,save=True):
        safe=escape(str(text)).replace('\n','<br>'); name='You' if role=='user' else 'KEN AI'; color='#ff7380' if role=='assistant' else '#f1dfe4'
        self.chatlog.append(f'<p style="margin:6px 2px"><b style="color:{color}">{name}</b><br>{safe}</p>')
        if save: self.memory.add(role,str(text),self.current_session); self.load_session_list()
    def send(self):
        text=self.input.text().strip()
        if not text or self.busy:
            if self.busy: self.status.setText('KEN is finishing the current request. Your text remains in the input.')
            return
        if self.wake_stop:
            self.wake_stop.set(); self.wake_cancelled=True
            self.wake_button.setText('Stopping…'); self.wake_button.setEnabled(False)
        self.input.clear(); self.append_message('user',text); self.busy=True; self.status.setText('Thinking with your local model…')
        history=[{'role':r,'content':c} for r,c in self.memory.recent(24,self.current_session)]; threading.Thread(target=self.worker,args=(history,),daemon=True).start()
    def worker(self,history):
        try: result=services.ollama_chat(history); error=None
        except Exception as exc: result=''; error=str(exc)
        self.signals.done.emit(result,error)
    def on_done(self,result,error):
        self.busy=False
        if error: self.status.setText('Connection needs attention'); self.append_message('assistant',error)
        else:
            self.status.setText('Ready · response generated locally'); self.append_message('assistant',result)
            if self.tts:
                try: services.speak(result)
                except Exception as exc: self.status.setText(f'Speech output unavailable: {exc}')
        self.input.setFocus()
        if self.auto_wake: QTimer.singleShot(max(2500,min(30000,len(str(result).split())*350+2000)),self.start_wake_word)
    def new_chat(self):
        self.current_session=self.memory.create_session(); self.chatlog.clear(); self.load_session_list(); self.status.setText('New chat · type a message or use the microphone'); self.input.setFocus()
    def refresh_stats(self): threading.Thread(target=lambda:self.signals.stats.emit(services.system_stats()),daemon=True).start()
    def on_stats(self,data):
        if data is None: self.status.setText('System stats need psutil. Run setup.bat to install packages.'); return
        for key in ('cpu','memory','disk'):
            value=int(data[key]); label,bar=self.stat_labels[key]; label.setText(f'{value}%'); bar.setValue(value)
        self.battery.setText(f"Battery · {data['battery']}%" if data['battery'] is not None else 'Battery · desktop power')
    def load_weather(self):
        city=self.city_input.text().strip()
        if not city: self.weather_info.setText('Enter a city to look up current weather.'); return
        self.settings.setValue('weather_city',city); self.weather_info.setText(f'Loading weather for {escape(city)}…'); threading.Thread(target=self.weather_worker,args=(city,),daemon=True).start()
    def weather_worker(self,city):
        try: data=services.weather_for_location(city); error=None
        except Exception as exc: data=None; error=str(exc)
        self.signals.weather.emit(data,error)
    def on_weather(self,data,error):
        if error: self.weather_info.setText(f'Weather unavailable: {escape(str(error))}'); return
        self.weather_info.setText(f"<b style='font-size:22px;color:#fff0e2'>{escape(str(data['temperature']))}°C</b>  {escape(str(data['condition']))}<br>Feels like {escape(str(data['feels_like']))}°C · Humidity {escape(str(data['humidity']))}%<br>Wind {escape(str(data['wind']))} km/h<br>{escape(str(data['location']))} · {escape(str(data['updated']))}")
    def refresh_files(self):
        self.filelist.clear(); folder=Path.home()/'Documents'
        try: files=sorted((p for p in folder.iterdir() if p.is_file()),key=lambda p:p.stat().st_mtime,reverse=True)[:8]
        except OSError: files=[]
        for path in files:
            label=path.name if len(path.name)<=27 else path.name[:24]+'…'; item=QListWidgetItem('▧  '+label); item.setData(Qt.ItemDataRole.UserRole,str(path)); item.setToolTip(str(path)); self.filelist.addItem(item)
        if not files:
            item=QListWidgetItem('No files in Documents'); item.setFlags(Qt.ItemFlag.NoItemFlags); self.filelist.addItem(item)
    def selected_file(self):
        item=self.filelist.currentItem(); return item.data(Qt.ItemDataRole.UserRole) if item else None
    def open_selected_file(self):
        path=self.selected_file()
        if path: QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else: self.open_file()
    def open_documents(self): QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path.home()/'Documents')))
    def open_whatsapp(self):
        try:
            from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QMessageBox.critical(self,'WhatsApp Web unavailable','Qt WebEngine is missing. Close KEN and run setup.bat again to install the full PySide6 package.'); return
        if getattr(self,'whatsapp_dialog',None) is not None:
            self.whatsapp_dialog.show(); self.whatsapp_dialog.raise_(); self.whatsapp_dialog.activateWindow(); self.whatsapp_dialog.exec(); return
        dialog=QDialog(self); dialog.setWindowTitle('KEN AI · WhatsApp Web'); dialog.resize(1180,780); layout=QVBoxLayout(dialog); toolbar=QHBoxLayout()
        for label,action in [('←', 'back'),('→','forward'),('↻','reload')]:
            button=QPushButton(label); button.setFixedWidth(44); toolbar.addWidget(button)
            if action=='back': back_button=button
            elif action=='forward': forward_button=button
            else: reload_button=button
        toolbar.addWidget(QLabel('WhatsApp Web · sign in to see your chats',objectName='muted')); toolbar.addStretch(); external=QPushButton('Open in browser'); toolbar.addWidget(external); layout.addLayout(toolbar)
        view=QWebEngineView(dialog)
        profile_dir=Path(os.getenv('LOCALAPPDATA',str(Path.home()))) / 'KenAI' / 'whatsapp-profile'; profile_dir.mkdir(parents=True,exist_ok=True)
        profile=QWebEngineProfile('KENAIWhatsApp',self); profile.setPersistentStoragePath(str(profile_dir)); profile.setCachePath(str(profile_dir/'cache')); profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        page=QWebEnginePage(profile,view); view.setPage(page); view.setUrl(QUrl('https://web.whatsapp.com')); layout.addWidget(view,1)
        back_button.clicked.connect(view.back); forward_button.clicked.connect(view.forward); reload_button.clicked.connect(view.reload); external.clicked.connect(lambda:webbrowser.open('https://web.whatsapp.com'))
        self.whatsapp_profile=profile; self.whatsapp_view=view; self.whatsapp_dialog=dialog
        resume_wake=self.auto_wake
        if self.wake_stop: self.wake_cancelled=True; self.wake_stop.set()
        dialog.finished.connect(lambda _=0: QTimer.singleShot(700,self.start_wake_word) if resume_wake else None)
        dialog.exec()

    def open_file(self):
        filename,_=QFileDialog.getOpenFileName(self,'Choose any file on this computer',Path.home().anchor,'Documents (*.txt *.md *.pdf *.docx *.csv *.json *.py);;All files (*.*)')
        if filename: QDesktopServices.openUrl(QUrl.fromLocalFile(filename))
    def summarize_file(self):
        filename=self.selected_file()
        if not filename:
            filename,_=QFileDialog.getOpenFileName(self,'Choose a document to summarize',Path.home().anchor,'Documents (*.txt *.md *.pdf *.docx *.csv *.json *.py);;All files (*.*)')
            if not filename: return
        self.process_document(filename,True)
    def process_document(self,path,summary=True):
        if self.busy: self.status.setText('KEN is finishing the current request first.'); return
        self.status.setText(f'Reading {Path(path).name} locally…'); self.busy=True
        def run():
            try:
                result=services.summarize_file(path,[],'qwen3:1.7b') if summary else f'Selected file: {path}\nChoose Summarize to ask the local model to summarize its contents.'; error=None
            except Exception as exc: result=''; error=str(exc)
            self.signals.done.emit(result,error)
        threading.Thread(target=run,daemon=True).start()
    def web_search(self):
        query=self.input.text().strip()
        if not query: self.status.setText('Type a search in the chat field, then choose Web search.'); self.input.setFocus(); return
        if self.busy: self.status.setText('KEN is finishing the current request first.'); return
        self.input.clear(); self.append_message('user','Search the web for: '+query); self.status.setText('Searching the web…'); self.busy=True
        def run():
            try:
                rows=services.search_web(query); result='Web results for: '+query+'\n\n'+('\n\n'.join(f"{i+1}. {r['title']}\n{r['body']}\n{r['url']}" for i,r in enumerate(rows)) or 'No results found.'); error=None
            except Exception as exc: result=''; error=str(exc)
            self.signals.done.emit(result,error)
        threading.Thread(target=run,daemon=True).start()
    def voice_input(self):
        if self.busy or self.voice_active: self.status.setText('Finish or stop the current request before recording.'); return
        self.voice_active=True; self.mic_button.setText('Recording…'); self.mic_button.setEnabled(False); self.status.setText('Recording for up to 8 seconds; speech is transcribed locally…')
        threading.Thread(target=self.voice_worker,args=(self.microphone_device(),),daemon=True).start()
    def voice_worker(self,device):
        try: result=services.transcribe_bounded(8,device=device); error=None
        except Exception as exc: result=''; error=services.format_microphone_error(exc)
        self.signals.voice.emit(result,error)
    def on_voice(self,result,error):
        was_wake=self.wake_stop is not None; self.voice_active=False; self.mic_button.setText('🎙 Speak'); self.mic_button.setEnabled(True)
        if was_wake: self.wake_stop=None; self.wake_button.setText('Wake: on' if self.auto_wake else 'Wake: off'); self.wake_button.setEnabled(True)
        if self.wake_cancelled: self.wake_cancelled=False; self.status.setText('Wake-word listening stopped'); return
        if error:
            if was_wake: self.auto_wake=False; self.wake_button.setText('Wake: off')
            self.status.setText(error); QMessageBox.warning(self,'Microphone or transcription issue',error)
        elif result: self.input.setText(result); self.status.setText('I heard you · sending your request to KEN'); self.send()
        elif was_wake:
            self.status.setText('Still listening for “hello”, “hi”, “ken”, or “wake up”.')
            if self.auto_wake: QTimer.singleShot(600,self.start_wake_word)
        else: self.status.setText('No speech detected. Check the selected mic and try a short phrase.')
        self.input.setFocus()
    def toggle_wake_word(self):
        if self.wake_stop:
            self.auto_wake=False; self.wake_cancelled=True; self.wake_stop.set(); self.wake_button.setText('Stopping…'); self.wake_button.setEnabled(False); self.status.setText('Pausing wake listening after this short mic clip…'); return
        self.auto_wake=True; self.start_wake_word()
    def start_wake_word(self):
        if not self.auto_wake or self.busy or self.voice_active: return
        if self.wake_stop:
            QTimer.singleShot(500,self.start_wake_word); return
        self.wake_cancelled=False; self.wake_stop=threading.Event(); self.voice_active=True; self.wake_button.setText('Wake: on · pause'); self.status.setText('Listening for “hello”, “hi”, “ken”, or “wake up”…')
        threading.Thread(target=self.wake_worker,args=(self.wake_stop,self.microphone_device()),daemon=True).start()
    def wake_worker(self,stop_event,device):
        try: result=services.listen_for_wake_word(stop_event,device=device); error=None
        except Exception as exc: result=''; error=services.format_microphone_error(exc)
        self.signals.voice.emit(result,error)
    def navigate(self,name):
        if name=='WhatsApp': self.open_whatsapp()
        elif name=='Files': self.open_documents()
        elif name=='Settings': self.open_microphone_settings()
        elif name=='Chat': self.input.setFocus()
        else: self.status.setText('Ready when you are · local assistant'); self.input.setFocus()

def main():
    app=QApplication(sys.argv); app.setApplicationName('KEN AI NEXT GEN'); app.setStyle('Fusion'); app.setStyleSheet(STYLE)
    window=MainWindow(); window.show(); return app.exec()

