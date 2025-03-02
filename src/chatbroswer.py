# chatbroswer.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################

import os
import sys
import pickle
import ctypes
import urllib.parse
from flask import Flask, request, jsonify

# PyQt Libs
from PyQt5.QtWidgets import (
    QTabWidget, QLabel, QPushButton, QSlider,
    QHBoxLayout, QVBoxLayout, QMessageBox, QInputDialog, QTableWidgetItem,
    QSpinBox, QColorDialog, QDoubleSpinBox, QLineEdit, QApplication, QGroupBox,
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QMenu,
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout,
    QTabWidget, QToolBar, QAction, QFileDialog, QMessageBox, QInputDialog, QDialog, QLineEdit,
    QDialogButtonBox, QLabel, QColorDialog, QComboBox, QFontComboBox, QSpinBox, QSplitter, QTextEdit, QScrollArea,
    QGroupBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QObject, pyqtSlot, QStandardPaths
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QDesktopServices
# pip install --upgrade PyQt5 PyQtWebEngine

# Custom Modules
import debug
import argsettings
import params
import version
from chatloop import Chatloop, model_list
from dethink import think_output_split as tos
from mkdown_convertor import convert_markdown_to_html as to_html
from chatbrowser_theme import generate_stylesheet
from threadpool import ThreadPool
from strutil import str_unquote, str_demarkdown
from strlang import is_english
from kokoro_infer import AudioPlayer, KokoroTTS, kokoro_language_dict, kokoro_voicer_dict

# Global Variables
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
DEFAULT_FONT_FAMILY = "Arial, sans-serif"
DEFAULT_FONT_SIZE = 22  # pixels
DEFAULT_EXTRA_CSS = "body { background-color: #ffffff; }"
CHAT_ENABLE_MARKDOWN = True

# Control Panels
DEFAULT_CONTROL_TYPE = "Default"  # Means nothing

# Flusk App
flaskapp = Flask(__name__)
flask_button_signals = []

# Flusk - Functinal, Process Javasript button events
@flaskapp.route('/button_clicked', methods=['POST'])
def button_clicked():
    data = request.get_json()
    # Append the signal (e.g., action and index) to the list
    flask_button_signals.append(data) 
    print(f"Button clicked: {data}")  # For debugging
    return jsonify({'status': 'success', 'data': data})


# CustomWebEnginePage: Internal Webpage Engine
# It supports interactive windows 
# (such as verification codes, human-machine verification)    
class CustomWebEnginePage(QWebEnginePage):
    popup_windows = []

    def __init__(self, parent=None, new_tab_callback=None):
        super().__init__(parent)
        self.new_tab_callback = new_tab_callback
        # Enable advanced settings to mimic a modern browser.
        self.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        self.settings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)

    def createWindow(self, _type):
        # For new tab requests: if a new_tab_callback is provided, use it.
        if _type in (QWebEnginePage.WebBrowserTab, QWebEnginePage.WebBrowserBackgroundTab):
            if self.new_tab_callback is not None:
                new_webview = self.new_tab_callback()
                return new_webview.page()
            else:
                # If no callback is provided, fallback to redirecting in the same window.
                return self

        # For genuine popups, create a new top-level window.
        popup = QWebEngineView()
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setWindowFlags(Qt.Window)  # Ensure the popup is an independent window.
        popup.setWindowTitle("Popup")
        popup.resize(900, 600)
        # Create a new CustomWebEnginePage for the popup and share the same profile.
        popup_page = CustomWebEnginePage(popup, new_tab_callback=self.new_tab_callback)
        popup_page.setProfile(self.profile())
        popup.setPage(popup_page)

        # Apply the same advanced settings to the popup.
        popup.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        popup.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        popup.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        popup.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        popup.settings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)

        popup.show()
        CustomWebEnginePage.popup_windows.append(popup)
        popup.destroyed.connect(lambda: CustomWebEnginePage.popup_windows.remove(popup)
        if popup in CustomWebEnginePage.popup_windows else None)
        return popup_page

    def userAgentForUrl(self, url):
        # Return a modern user agent string so sites like ChatGPT see a contemporary browser.
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"

    def javaScriptAlert(self, securityOrigin, msg):
        alert = QMessageBox()
        alert.setWindowTitle("Alert")
        alert.setText(msg)
        alert.exec_()

    def javaScriptConfirm(self, securityOrigin, msg):
        reply = QMessageBox.question(None, "Confirm", msg, QMessageBox.Yes | QMessageBox.No)
        return reply == QMessageBox.Yes

    def javaScriptPrompt(self, securityOrigin, msg, defaultValue, result):
        text, ok = QInputDialog.getText(None, "Prompt", msg, text=defaultValue)
        if ok:
            result.append(text)
            return True
        return False


# Receive inline editing updates
# from the web page through QWebChannel
class ChatHistoryBridge(QObject):
    def __init__(self, chat_widget):
        super().__init__()
        self.chat_widget = chat_widget
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"

    @pyqtSlot(int, str, str)
    def updateMessage(self, index, role, newText):
        self.chat_widget.update_message(index, role, newText)


# Chatting Special Control Panel (commands)
class SpecialControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.control_type_combo = QComboBox()
        self.control_type_combo.addItems([
            # See chatbox.py
            # NathMATH all rights reserved
            DEFAULT_CONTROL_TYPE,
            r"\quit",
            r"\delete",
            r"\deleteall",
            r"\toolcall",
            r"\visit",
            r"\search",
            r"\locate",
            r"\connect",
            r"\insert",
            r"\update",
            r"\query",
            r"\select"
        ])
        self.control_input = QLineEdit()
        self.control_input.setPlaceholderText("输入控制参数...")
        self.send_control_button = QPushButton("应用控制选项")
        layout = QHBoxLayout()
        layout.addWidget(self.control_type_combo)
        layout.addWidget(self.control_input)
        layout.addWidget(self.send_control_button)
        self.setLayout(layout)


# Single chat session
# It supports inline editing of chat history,
# input area height adjustment and special controls
# It connects to the backend 
class ChatWidget(QWidget):
    
    def __init__(self, 
                 font_family=DEFAULT_FONT_FAMILY, 
                 font_size=DEFAULT_FONT_SIZE,
                 extra_css=DEFAULT_EXTRA_CSS, 
                 enable_markdown=CHAT_ENABLE_MARKDOWN,
                 model=params.nathui_backend_model,
                 temperature=1.0,
                 top_p=0.95,
                 max_tokens=8192,
                 system_prompt="You are a helpful assistant.",
                 kokoro_cn_voicer=kokoro_voicer_dict["z"][0],
                 kokoro_en_voicer=kokoro_voicer_dict["a"][0],
                 parent=None):

        # Basic settings
        super().__init__(parent)
        self.font_family = font_family
        self.font_size = font_size
        self.extra_css = extra_css
        self.enable_markdown = enable_markdown
        
        # Advanced Inference settings
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        
        # Voice settings
        self.kokoro_cn_voicer = kokoro_cn_voicer
        self.kokoro_en_voicer = kokoro_en_voicer

        # Sync or async
        self.sync = False

        # Sending without an reply
        self.sending_pending_reply = False

        # History of conversations
        # Supports "User", "Assistant", "Control", DO NOT INCLUDE "System"
        self.conversation_turns = []
        
        # Audio TTS related threads and player
        self.audios = []
        self.player = AudioPlayer(self.audios, sample_rate=24000)
        
        self.player_isplaying = False
        self.player_threadpool = ThreadPool(4)

        ###################################################
        # Connect to the backend Chatloop
        # For any browser that is external, No Renderer is a must
        # Internal treatment, without trigerring an renderer internally
        ###################################################
        self.chatloop = Chatloop(use_external="No Renderer")
        # Note, in this class, chat history is still maintained as a copy
        # But when treating with the savings, we should save the backend and load to it as well
        
        
        ###################################################
        # 
        # Load inference settings if exists
        self.load_inference_settings()
        
        ###################################################
        #
        # Apply inference settings
        # It must be here after chatloop has been initialized
        self.apply_inference_setting()
        
        # Chat history display area, using QWebEngineView to render inline editable HTML
        self.browser = QWebEngineView()
        self.browser.setMinimumHeight(400)
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        # Setting up QWebChannel for JS and Python interaction (inline editing updates)
        self.channel = QWebChannel(self.browser.page())
        self.bridge = ChatHistoryBridge(self)
        self.channel.registerObject('bridge', self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Message input area, supporting multi-line input
        self.message_input = QPlainTextEdit()
        self.message_input.setPlaceholderText(r"输入消息 (或使用命令，如 \search)")

        # The lower input panel contains the 
        # send, clear and special control buttons 
        # (the editing history is already inline)
        self.input_panel = QWidget()
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout = QHBoxLayout()
        self.send_button = QPushButton("发送")
        self.regen_button = QPushButton("重新生成")
        self.clear_lstrnd = QPushButton("回退一轮")
        self.clear_button = QPushButton("清空对话")
        self.ttsread_button = QPushButton("语音朗读")
        self.toggle_control_button = QPushButton("特殊控制面板")
        # add widget
        btn_layout.addWidget(self.send_button)
        btn_layout.addWidget(self.regen_button)
        btn_layout.addWidget(self.clear_lstrnd)
        btn_layout.addWidget(self.clear_button)
        btn_layout.addWidget(self.ttsread_button)
        btn_layout.addWidget(self.toggle_control_button)
        self.special_control_panel = SpecialControlPanel()
        self.special_control_panel.setVisible(False)
        panel_layout.addLayout(btn_layout)
        panel_layout.addWidget(self.special_control_panel)
        self.input_panel.setLayout(panel_layout)

        # Use QSplitter to separate the chat history and input area, 
        # allowing the height to be adjusted freely
        self.input_splitter = QSplitter(Qt.Vertical)
        self.input_splitter.addWidget(self.message_input)
        self.input_splitter.addWidget(self.input_panel)

        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(self.browser)
        self.main_splitter.addWidget(self.input_splitter)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.main_splitter)
        self.setLayout(main_layout)

        # Bind - When send triggered
        self.send_button.clicked.connect(self.process_sending)
        
        # Bind - When regenerate triggered
        self.regen_textbuffer = {}
        self.regen_button.clicked.connect(self.regenerate_response)
        
        # Bind - When clear lastround triggered
        self.clear_lstrnd.clicked.connect(self.clear_lastround)

        # Bind - When clear triggered
        self.clear_button.clicked.connect(self.clear_conversation)
        
        # Bind - When ttsread triggered
        self.ttsread_button.clicked.connect(self.ttsread_clicked)

        # Bind - When Special Control button is clicked
        self.toggle_control_button.clicked.connect(self.toggle_control_panel)

        # Bind - When Control Send is clicked
        self.special_control_panel.send_control_button.clicked.connect(self.process_control_input)

        self.update_conversation()
        
        # Author Tag
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        
    # Export Data (static)
    @staticmethod
    def _export_data(data, filepath) -> bool:
        try:
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            return False
        
    # Import Data (static)
    @staticmethod
    def _import_data(filepath, default=None) -> any:
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return default
        except Exception as e:
            return default   
      
    # Reload inference settings to the self
    # Before chatting, you need to `apply` it 
    # Only non-None variables will be set here
    def reload_inference_setting(self,
                                 model=None,
                                 temperature=None,
                                 top_p=None,
                                 max_tokens=None,
                                 system_prompt=None,
                                 kokoro_cn_voicer=None,
                                 kokoro_en_voicer=None):
        if model:
            self.model = model
        if temperature:
            self.temperature = temperature
        if top_p:
            self.top_p = top_p
        if max_tokens:
            self.max_tokens = max_tokens
        if system_prompt:
            self.system_prompt = system_prompt
        if kokoro_cn_voicer:
            self.kokoro_cn_voicer = kokoro_cn_voicer
        if kokoro_en_voicer:
            self.kokoro_en_voicer = kokoro_en_voicer
        return
    
    # Apply inference settings to the backend
    def apply_inference_setting(self):
        
        # To set the system_prompt
        self.chatloop.system_prompt_set(self.system_prompt)
        
        # To update a new default mode
        self.chatloop.reattach_new_model(new_model = self.model)
        
        # To the backend
        inf_params = self.chatloop.infer_params_get()
        inf_params["temperature"] = self.temperature
        inf_params["max_tokens"] = self.max_tokens
        inf_params["top_p"] = self.top_p
        self.chatloop.infer_params_set(inf_params)
        return None
        
    # When send is clicked (communicate with backend to get responses)
    def process_sending(self):

        ###################
        #
        # Here, it actually connects to the backend and generate AI responses
        #
        ###################
        
        #### If triggered as a regenerate
        user_text = ""
        if len(self.regen_textbuffer) > 0:
            # Paste here
            user_text = self.regen_textbuffer["text"].strip()
            # self.regen_textbuffer may have more things in the future
            self.regen_textbuffer = {}            
            
        #### Triggered as input
        else:
            # Try to paste remained control panel to test
            self.process_control_input()
    
            # Get total input
            user_text = self.message_input.toPlainText().strip()
            
            # Clear after get
            self.message_input.clear()
        
        # No text? back
        if not user_text or len(user_text) == 0:
            return

        # If already sent, return
        if self.sending_pending_reply == True:
            # Occupied
            return

        # Sending without reply counter
        self.sending_pending_reply = True

        # Add a new round and save the user message
        #                                                 here we omit assitant
        #                                                 and will be added when responsed
        self.conversation_turns.append({"user": user_text, })

        # Update showing
        self.update_conversation()

        QApplication.processEvents()

        # Sync
        if self.sync == True:

            # Get response generated and record it 
            thinking, response, placeholder = self.generate_response(user_text)
            self.conversation_turns[-1]["assistant"] = response

            # Update showing
            self.update_conversation()

        # Async
        else:
            # Create a worker thread instance and connect the signal
            self.worker = self.Chatloop_GenerateWorker(self.chatloop, user_text)
            self.worker.first_call_done.connect(self.on_first_call_done)
            self.worker.final_result_ready.connect(self.on_final_result_ready)

            # Start a thread to generate a response asynchronously
            self.worker.start()

    # When regenerate is clicked
    def regenerate_response(self):
        
        # First get the last round of conversation
        # If no round, return
        if len(self.conversation_turns) == 0:
            return
        
        else:
            last_turn = self.conversation_turns[-1]
            self.conversation_turns = self.conversation_turns[0:-1]
            
            # If no user, return
            if last_turn.get("user", None) is None:
                return
            
            # Backend clearing 
            self.chatloop.clear_lastround()
            
            # Trigger process sending as the regenerate mode
            self.regen_textbuffer["text"] = last_turn["user"]
            self.process_sending()

    # When control send is clicked
    def process_control_input(self):

        # Get control type selected and commands input
        control_type = self.special_control_panel.control_type_combo.currentText()
        control_command = self.special_control_panel.control_input.text().strip()

        # No command is selected, disregard it
        if len(control_type) == 0 or control_type == DEFAULT_CONTROL_TYPE:
            return

        # If no command, then single control type
        if len(control_command) == 0:
            control_appended = control_type
        # If has a command, then starting and ending quotes
        else:
            control_appended = control_type + " " + control_command + " " + control_type + " "

        # Append everything to the front of user input
        new_input = control_appended + self.message_input.toPlainText()
        self.message_input.setPlainText(new_input)

        # Clear and restore type
        self.special_control_panel.control_input.clear()

        # Set to default type
        default_index = self.special_control_panel.control_type_combo.findText(DEFAULT_CONTROL_TYPE)
        self.special_control_panel.control_type_combo.setCurrentIndex(default_index)

    # When control panel is clicked (open up or make it invisible)
    def toggle_control_panel(self):
        visible = not self.special_control_panel.isVisible()
        self.special_control_panel.setVisible(visible)

    # NONBIND - Worker thread to handle the Generate Calls
    class Chatloop_GenerateWorker(QThread):

        # Signal emitted after the first API call completes. 
        # It can carry a placeholder or message.
        first_call_done = pyqtSignal(str)

        # Signal emitted when the final result is ready
        # (thinking, output, placeholder)
        final_result_ready = pyqtSignal(str, str, str)

        def __init__(self, chatloop, user_text, parent=None):
            super().__init__(parent)
            self.chatloop = chatloop
            self.user_text = user_text
            self.extra_css = """
                #display {
                    font-size: 20px;
                    font-weight: regular;
                    text-align: left;
                    padding: 10px;
                    margin-top: 20px;
                    color: #333;
                    animation: fade 1.2s infinite;
                }
                
                @keyframes fade {
                    0% { opacity: 0.3; }
                    50% { opacity: 1; }
                    100% { opacity: 0.3; }
                }
                """

        def run(self, placeholder: str = ""):
            # Replace to default
            if placeholder is None or placeholder == "":
                placeholder = f"""
                    <style>
                    {self.extra_css}
                    </style>
                    <div id="display"></div>
                    <script>
                      const texts = ["Thinking", "Thinking .", "Thinking ..", "Thinking ..."];
                      let index = 0;
                      setInterval(() => {{
                        document.getElementById("display").innerText = texts[index];
                        index = (index + 1) % texts.length;
                      }}, 200);
                    </script>
                    """

            # Emit signal to indicate the first call is done (e.g., to prompt user or update status)
            self.first_call_done.emit(placeholder)

            ###################################################################
            # Actual calling

            # Optionally, if you need a delay or wait for user interaction before the second call,
            # you can implement that here. For now, we call it immediately.
            # Second API call: get the final data.
            chat_once_result = self.chatloop.api_chat_once(self.user_text, chat=True)

            # Process the latest response to extract thinking and output
            try:
                thinking, output = tos(self.chatloop.responses[-1][1])
                # Emit the final result so the GUI can update accordingly.
                self.final_result_ready.emit(thinking, output, "")
                
            except Exception as e:
                print("Error in generating a response! " + str(e))
                self.final_result_ready.emit(thinking, output, "")

    # NONBIND - To get the response from the backend (synchronizedly)
    # DEPRECATED
    def generate_response_sync(self, user_text):

        # Each time, rest the backend chat history since it may be modified
        self.chatloop.convert_external_chat_history(self.conversation_turns)

        # Trigger the response chat_once
        placeholder = self.chatloop.api_chat_once(user_text)

        # Get the latest response
        try:
            thinking, output = tos(self.chatloop.responses[-1][1])
        except Exception as e:
            print("Error in generating a response! " + str(e))
            return "", "", ""

        return thinking, output, placeholder

    # NONBIND - To get the response async - 1st calls
    @pyqtSlot(str)
    def on_first_call_done(self, placeholder_html):
        # Tmply update to placeholder
        self.conversation_turns[-1]["assistant_html"] = placeholder_html

        # Tmply update
        self.update_conversation()

    # NONBIND - To get the response async - 2nd calls
    @pyqtSlot(str, str, str)
    def on_final_result_ready(self, thinking, output, placeholder2):
        # Finally update the AI ​​answer in the last round
        self.conversation_turns[-1]["assistant"] = output

        # Finally Drop the "assistant_html"
        self.conversation_turns[-1].pop("assistant_html")

        # Finally update
        self.update_conversation()

        # Release resending hold
        self.sending_pending_reply = False

    # NONBIND - Caller, convert all updated history to an updated html
    def update_conversation(self):
        # Called after each round and update
        html_content = self._generate_conversation_html()
        self.browser.setHtml(html_content)

    # NONBIND - Functional, Generate all conversations into a html
    def _generate_conversation_html(self):
        html = "<html><head>"
        html += "<meta charset='utf-8'>"
        html += f"<style>body {{ font-family: {self.font_family}; font-size: {self.font_size}px; {self.extra_css} }} "
        html += ".message { padding: 10px; margin: 10px; border: 1px solid #ccc; border-radius: 5px; } "
        html += ".user { background-color: #e8f5e9; } "
        html += ".assistant { background-color: #e3f2fd; } "
        html += ".control { background-color: #fff9c4; } "
        html += ".editable:hover { border: 1px dashed #666; cursor: pointer; } "
        html += """
          .assistant-buttons button {
            background-color: #e3f2fd;
            border: none;
            color: black;
            padding: 8px 16px;
            font-size: 14px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.3s ease;
          }
          .assistant-buttons button:hover {
            background-color: #fffffd;
          }
          .assistant-buttons {
            margin-top: 8px;
          }
        """
        html += "</style>"
        html += "<script src='qrc:///qtwebchannel/qwebchannel.js'></script>"
        # Javascript
        html += """
        <script>
        var bridge = null;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;
        });
        function enableEditing(elem) {
            elem.contentEditable = true;
            elem.focus();
        }
        function disableEditing(elem) {
            elem.contentEditable = false;
            var index = parseInt(elem.getAttribute('data-index'));
            var role = elem.getAttribute('data-role');
            var newText = elem.innerText;
            if(bridge) {
                bridge.updateMessage(index, role, newText);
            }
        }
        window.addEventListener('DOMContentLoaded', (event) => {
          // Attach event listeners to editable elements.
          var editables = document.getElementsByClassName('editable');
          for (var i = 0; i < editables.length; i++) {
              editables[i].addEventListener('dblclick', function(e) {
                  // Prevent enabling editing if a button inside the editable is clicked.
                  if(e.target.tagName !== 'BUTTON') {
                      enableEditing(this);
                  }
              });
              editables[i].addEventListener('blur', function(e) {
                  disableEditing(this);
              });
          }
        
        document.addEventListener('DOMContentLoaded', function() {
          // Attach click event listeners for Regenerate buttons.
          document.querySelectorAll('.regenerate-button').forEach(function(btn) {
              btn.addEventListener('click', function(e) {
                  e.stopPropagation(); // Prevent event bubbling.
                  let index = this.getAttribute('data-index');
                  fetch('/button_clicked', {
                      method: 'POST',
                      headers: {'Content-Type': 'application/json'},
                      body: JSON.stringify({action: 'regenerate', index: index})
                  })
                  .then(response => response.json())
                  .then(data => console.log('Response:', data))
                  .catch(error => console.error('Error:', error));
              });
          });
        
          // Attach click event listeners for TTS buttons.
          document.querySelectorAll('.TTS-button').forEach(function(btn) {
              btn.addEventListener('click', function(e) {
                  e.stopPropagation(); // Prevent event bubbling.
                  let index = this.getAttribute('data-index');
                  fetch('/button_clicked', {
                      method: 'POST',
                      headers: {'Content-Type': 'application/json'},
                      body: JSON.stringify({action: 'TTS', index: index})
                  })
                  .then(response => response.json())
                  .then(data => console.log('Response:', data))
                  .catch(error => console.error('Error:', error));
              });
          });
        });

        </script>
        """
        html += "</head><body>"

        # For each round
        for i, turn in enumerate(self.conversation_turns):

            html += "<div class='turn'>"

            # User text
            if "user" in turn:
                if self.enable_markdown:
                    user_html = to_html(turn["user"],
                                        DEFAULT_FONT_FAMILY,
                                        DEFAULT_FONT_SIZE,
                                        "")
                else:
                    user_html = turn["user"].replace("\n", "<br>")
                html += f"<div class='message user editable' data-index='{i}' data-role='user'><strong>User:</strong><br>{user_html}</div>"

            # Assistant text
            if "assistant" in turn:
                if self.enable_markdown:
                    assistant_html = to_html(turn["assistant"],
                                             DEFAULT_FONT_FAMILY,
                                             DEFAULT_FONT_SIZE,
                                             "")
                else:
                    assistant_html = turn["assistant"].replace("\n", "<br>")
                html += f"""<div class='message assistant editable' data-index='{i}' data-role='assistant'><strong>Assistant:</strong><br>{assistant_html}</div>"""
                
                # @todo
                # I haven't solved the issue of receving the signal of these buttons
                # So use a gereral button for regenerate and TTS
                # 
                # Add buttons for assistant messages
                # html += f"""
                #  <div class='assistant-buttons' data-index='{i}'>
                #    <button class='regenerate-button' data-index='{i}'>Regenerate</button>
                #    <button class='TTS-button' data-index='{i}'>TTS</button>
                #  </div>"""
                
            # Directly Assistant Html text
            if "assistant_html" in turn:
                # Always disable markdown
                assistant_html = turn["assistant_html"]
                html += f"<div class='message assistant editable' data-index='{i}' data-role='assistant'><strong>Assistant:</strong><br>{assistant_html}</div>"

            # Control text
            if "control" in turn:
                if self.enable_markdown:
                    control_html = to_html(turn["control"],
                                           DEFAULT_FONT_FAMILY,
                                           DEFAULT_FONT_SIZE,
                                           "")
                else:
                    control_html = turn["control"].replace("\n", "<br>")
                html += f"<div class='message control editable' data-index='{i}' data-role='control'><strong>Control [{turn.get('control_type', '')}] :</strong><br>{control_html}</div>"

            # We do not have system here
            # It will be set to the backend directly
            if "system" in turn:
                pass

            html += "</div>"

        # Scroll down script
        scroll_script = """
            <script type="text/javascript">
              window.onload = function() {
                window.scrollTo(0, document.body.scrollHeight);
              };
            </script>
            """
        html += scroll_script

        html += "</body></html>"
        return html
    
    # Update conversation turns api
    def update_message(self, index, role, new_text):
        try:
            if role in self.conversation_turns[index]:
                self.conversation_turns[index][role] = new_text
        except IndexError:
            pass

    # Set background css style
    def set_background(self, background_css):
        self.extra_css = background_css
        self.update_conversation()

    # When clear lastround is clicked
    def clear_lastround(self):
        
        # First see if we have last round of conversation
        # If no round, return
        if len(self.conversation_turns) == 0:
            return
        else:
            # Frontend clearing 
            self.conversation_turns = self.conversation_turns[0:-1]
            self.update_conversation()
            # Add system prompt in the future

            # Backend clearing 
            self.chatloop.clear_lastround()

    # When clear conversion is clicked
    def clear_conversation(self):

        # Frontend clearing 
        self.conversation_turns = []
        self.update_conversation()
        # Add system prompt in the future

        # Backend clearing 
        self.chatloop.clear_messages()

    # Generate text to audio thread function
    @staticmethod
    def try_generate(player: AudioPlayer, audios, sample_text, cn_voicer, en_voicer):    
        
        # De-markdown
        sample_text = str_demarkdown(sample_text)
        
        # Identify English or Chinese
        ratio, is_eng = is_english(sample_text)
        if is_eng:
            lang = "a"
            voicer = en_voicer
        else:
            lang = "z"
            voicer = cn_voicer

        # Generate audio
        tts_engine = KokoroTTS(lang_code=lang,
                               voice=voicer, 
                               speed=1.1, 
                               split_pattern=r'(?:\n+|[.。；;!！]+)', 
                               sample_rate=24000, 
                               display_audio=False, 
                               save_to_file=False, 
                               output_dir='__kokoro_audio__')
        
        # Generate and process audio segments in realtime.
        for segment_index, (graphemes, phonemes, audio) in enumerate(tts_engine.synthesize(sample_text)):
            audios.append(audio)
            # print(f"Segment {segment_index}")
            # print("Text:", graphemes)
            # print("Phonemes:", phonemes)
            
        # Finale
        player.finale()
        
        # Wait until stop
        player.wait_until_stop()
            
        return player

    # When tts read clicked (start or stop)
    def ttsread_clicked(self):
        # No conversation or last no assistant
        if len(self.conversation_turns) == 0:
            return
        if self.conversation_turns[-1].get("assistant", None) is None:
            return
        
        if self.player_isplaying == False:
            
            # Clear audios
            self.audios = []
            self.player.rebind(self.audios)
            
            # Create and start the realtime audio player.
            self.player.start()
            
            # Get last generated assistant
            last_generated = self.conversation_turns[-1]["assistant"]
            
            # Start to play
            self.player_threadpool.execute(self.try_generate,
                           player = self.player, 
                           audios = self.audios, 
                           sample_text = last_generated,
                           cn_voicer = self.kokoro_cn_voicer,
                           en_voicer = self.kokoro_en_voicer)
            
            self.player_isplaying = True
            
        else:
            # If aleady stopped
            if self.player.current_index == 0 and self.player.max_index == 100**10:
                self.player.stop()
                self.player_threadpool.stopall()
                self.player_isplaying = False
                # Regenerate audio
                self.ttsread_clicked()
                
            else:
                # Stop from player to threadpool
                self.player.stop()
                self.player_threadpool.stopall()
                
                self.player_isplaying = False
        
    # Save Inference Settings
    def save_inference_settings(self, file_path = None):
        # Default place
        if file_path is None:
            file_path = params.nathui_backend_config_folder + "inference.config"
            
        # Dict
        inference_settings = {
            
            "~attr~": "inference_settings",
        
            "params": {
                # Advanced Inference settings
                "model" : self.model,
                "temperature" : self.temperature,
                "top_p" : self.top_p,
                "max_tokens" : self.max_tokens,
                "system_prompt": self.system_prompt,
                
                # Voice settings
                "kokoro_cn_voicer" : self.kokoro_cn_voicer,
                "kokoro_en_voicer" : self.kokoro_en_voicer,
                }
        }
        
        self._export_data(inference_settings, file_path)
        
    # Load Inference Settings
    def load_inference_settings(self, file_path = None):
        # Default place
        if file_path is None:
            file_path = params.nathui_backend_config_folder + "inference.config"
        
        # Not exists, pass
        if os.path.exists(file_path) == False:
            return
            
        inference_settings = self._import_data(file_path)
        # Attr check
        if inference_settings.get("~attr~", None) != "inference_settings":
            return
        
        self.reload_inference_setting(**inference_settings["params"])
        self.apply_inference_setting()
        
    # Save ft-bk history to file
    def save_conversation(self, file_path):
        try:
            md_object = {
                "frontend_object": self.conversation_turns,
                "backend_object": self.chatloop.save_messages(None)
            }
            self.chatloop._export_data(md_object, file_path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存失败：{str(e)}")
            return False

    # Load and restore history from file
    def load_conversation(self, file_path):
        try:
            md_object = self.chatloop._import_data(file_path, {})
            if md_object["frontend_object"]:
                self.conversation_turns = md_object["frontend_object"]
            if md_object["backend_object"]:
                self.chatloop.load_messages(md_object["backend_object"])
            self.update_conversation()
            return True
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载失败：{str(e)}")
            return False


# Download manager pop-up window to display download tasks
class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载管理器")
        self.resize(500, 300)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["文件名", "进度", "状态"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showContextMenu)
        self.table.cellDoubleClicked.connect(self.onCellDoubleClicked)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 10px;
            }
            QTableWidget {
                background-color: #ffffff;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #0078d7;
                color: white;
                padding: 5px;
                border: none;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #ccc;
            }
            QMenu::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)

    def addDownload(self, download_item):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Constructs a file item and saves the full file path in the UserRole data
        file_item = QTableWidgetItem(download_item.downloadFileName())
        download_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        file_path = os.path.join(download_path, download_item.downloadFileName())
        file_item.setData(Qt.UserRole, file_path)

        progress_item = QTableWidgetItem("0%")
        status_item = QTableWidgetItem("进行中")

        self.table.setItem(row, 0, file_item)
        self.table.setItem(row, 1, progress_item)
        self.table.setItem(row, 2, status_item)

        download_item.downloadProgress.connect(lambda received, total, r=row: self.updateProgress(r, received, total))
        download_item.finished.connect(lambda r=row: self.updateStatus(r))

        download_item.setPath(file_path)
        download_item.accept()

    def updateProgress(self, row, received, total):
        percent = int(received / total * 100) if total > 0 else 0
        self.table.item(row, 1).setText(f"{percent}%")
        if percent >= 100:
            self.table.item(row, 2).setText("完成")

    def updateStatus(self, row):
        self.table.item(row, 2).setText("完成")

    def showContextMenu(self, pos):
        item = self.table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        menu = QMenu(self)
        open_folder_action = menu.addAction("打开所在文件夹")
        open_file_action = menu.addAction("打开文件")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == open_folder_action:
            self.openFolder(row)
        elif action == open_file_action:
            self.openFile(row)

    def onCellDoubleClicked(self, row, column):
        self.openFile(row)

    def openFolder(self, row):
        file_path = self.table.item(row, 0).data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            folder_path = os.path.dirname(file_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def openFile(self, row):
        file_path = self.table.item(row, 0).data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


# Interface of web browsing,
# including the address bar and navigation buttons
class WebSearchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("请输入 URL 或搜索关键词...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border: none;
                border-radius: 15px;
                padding: 5px 10px;
                background-color: #f1f1f1;
                font-size: 16px;
            }
        """)
        self.go_button = QPushButton("Go")
        self.go_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 15px;
                padding: 5px 15px;
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        self.back_button = QPushButton("Back")
        self.forward_button = QPushButton("Forward")
        self.refresh_button = QPushButton("Refresh")
        self.downloads_button = QPushButton("Downloads")

        nav_button_style = """
            QPushButton {
                border: none;
                border-radius: 15px;
                padding: 5px 15px;
                background-color: #008CBA;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #007BB5;
            }
        """
        self.back_button.setStyleSheet(nav_button_style)
        self.forward_button.setStyleSheet(nav_button_style)
        self.refresh_button.setStyleSheet(nav_button_style)
        self.downloads_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 15px;
                padding: 5px 15px;
                background-color: #2196F3;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.refresh_button)
        nav_layout.addWidget(self.downloads_button)
        nav_layout.addWidget(self.search_bar)
        nav_layout.addWidget(self.go_button)

        self.web_view = QWebEngineView()
        # Use the custom page that handles new window requests.
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.web_view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.web_view)
        self.setLayout(main_layout)

        self.go_button.clicked.connect(self.load_url)
        self.search_bar.returnPressed.connect(self.load_url)
        self.back_button.clicked.connect(self.web_view.back)
        self.forward_button.clicked.connect(self.web_view.forward)
        self.refresh_button.clicked.connect(self.web_view.reload)
        self.downloads_button.clicked.connect(self.show_download_manager)

        self.web_view.urlChanged.connect(self.update_url)

        # Download manager as an independent dialog.
        self.download_manager = DownloadManagerDialog()
        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self.handle_downloadRequested)

    # Load url and enter to the website
    def load_url(self, external_text: None | str = None):
        text = self.search_bar.text().strip()
        if isinstance(external_text, str):
            text = external_text.strip()

        if not text:
            return

        if text.startswith("http://") or text.startswith("https://"):
            url = text
        else:
            query = urllib.parse.quote(text)
            if params.nathui_backend_default_search_engine == "google":
                url = f"https://www.google.com/search?q={query}"
            elif params.nathui_backend_default_search_engine == "bing":
                url = f"https://www.bing.com/search?q={query}"
            elif params.nathui_backend_default_search_engine == "yahoo":
                url = f"https://search.yahoo.com/search?p={query}"
            else:
                url = f"https://www.google.com/search?q={query}"
        self.web_view.setUrl(QUrl(url))

    def update_url(self, qurl):
        self.search_bar.setText(qurl.toString())

    def handle_downloadRequested(self, download_item):
        self.download_manager.addDownload(download_item)
        self.download_manager.show()
        self.download_manager.raise_()
        self.download_manager.activateWindow()

    def show_download_manager(self):
        self.download_manager.show()
        self.download_manager.raise_()
        self.download_manager.activateWindow()


# Interface of settings
class SettingsTab(QWidget):
    
    # Selected settings
    # Which is a signal that will be captured by the main widge
    # to apply the actual settings and inference settings
    settingsApplied = pyqtSignal(dict)

    def __init__(self, current_theme="Light", current_bg_css="body { background-color: #ffffff; }",
                 current_font_family=DEFAULT_FONT_FAMILY, current_font_size=DEFAULT_FONT_SIZE, parent=None):
        super().__init__(parent)
        self.current_theme = current_theme
        self.current_bg_css = current_bg_css
        self.current_font_family = current_font_family
        self.current_font_size = current_font_size

        # Basic settings section
        self.theme_label = QLabel("主题选择:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Custom"])
        self.theme_combo.setCurrentText(self.current_theme)

        self.bg_color_label = QLabel("背景颜色:")
        self.bg_color_button = QPushButton("选择颜色")

        self.font_family_label = QLabel("字体:")
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(self.current_font_family))

        self.font_size_label = QLabel("字号:")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 48)
        self.font_size_spin.setValue(self.current_font_size)

        ########################
        #
        # Inference settings: model selection, temperature, top p, system prompt words
        self.model_label = QLabel("模型选择:")
        self.model_combo = QComboBox()
        self.reload_all_models()
        
        # Temperature
        self.temperature_label = QLabel("温度:")
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(1.0)
        
        # Top p parameters
        self.top_p_label = QLabel("Top p:")
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.01)
        self.top_p_spin.setValue(0.95)
        
        # Max Tokens
        self.max_tokens_label = QLabel("Max Tokens:")
        self.max_tokens_slider = QSlider(Qt.Horizontal)
        self.max_tokens_slider.setRange(128, 32768)
        self.max_tokens_slider.setSingleStep(128)
        self.max_tokens_slider.setValue(4096)
        self.max_tokens_slider.setMinimumWidth(600)
        self.max_tokens_slider.setMaximumWidth(900)
        

        # Create a spin box to display the value
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(128, 32768)
        self.max_tokens_spin.setValue(4096)
        self.max_tokens_spin.setMaximumWidth(100)
        # Connect the slider and spin box so that a change in one updates the other
        self.max_tokens_slider.valueChanged.connect(self.max_tokens_spin.setValue)
        self.max_tokens_spin.valueChanged.connect(self.max_tokens_slider.setValue)
        
        # Kokoro CN Voicer
        self.kokoro_cn_label = QLabel("TTS中文声优:")
        self.kokoro_cn_combo = QComboBox()
        
        # Kokoro EN Voicer
        self.kokoro_en_label = QLabel("TTS英文声优:")
        self.kokoro_en_combo = QComboBox()
        
        # System Prompt
        self.system_prompt_label = QLabel("系统提示词:")
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setFixedHeight(120)
        
        # Load all voicers to add to combos
        self.reload_all_voicers()
        
        # Load all inference parameters if exists
        self.load_inference_settings()

        self.apply_button = QPushButton("应用设置")

        ########################
        #
        # Main layout
        main_layout = QVBoxLayout()

        # Basic settings layout
        basic_layout = QVBoxLayout()
        layout_theme = QHBoxLayout()
        layout_theme.addWidget(self.theme_label)
        layout_theme.addWidget(self.theme_combo)
        basic_layout.addLayout(layout_theme)

        layout_bg = QHBoxLayout()
        layout_bg.addWidget(self.bg_color_label)
        layout_bg.addWidget(self.bg_color_button)
        basic_layout.addLayout(layout_bg)

        layout_font = QHBoxLayout()
        layout_font.addWidget(self.font_family_label)
        layout_font.addWidget(self.font_combo)
        basic_layout.addLayout(layout_font)

        layout_size = QHBoxLayout()
        layout_size.addWidget(self.font_size_label)
        layout_size.addWidget(self.font_size_spin)
        basic_layout.addLayout(layout_size)
        
        ###### Inf Group
        # 
        # Inference Settings
        advanced_group = QGroupBox("推理设置")
        advanced_layout = QVBoxLayout()

        layout_model = QHBoxLayout()
        layout_model.addWidget(self.model_label)
        layout_model.addWidget(self.model_combo)
        advanced_layout.addLayout(layout_model)

        layout_temp = QHBoxLayout()
        layout_temp.addWidget(self.temperature_label)
        layout_temp.addWidget(self.temperature_spin)
        advanced_layout.addLayout(layout_temp)

        layout_top_p = QHBoxLayout()
        layout_top_p.addWidget(self.top_p_label)
        layout_top_p.addWidget(self.top_p_spin)
        advanced_layout.addLayout(layout_top_p)
        
        layout_max_tokens = QHBoxLayout()
        layout_max_tokens.addWidget(self.max_tokens_label)
        layout_max_tokens.addWidget(self.max_tokens_slider)
        layout_max_tokens.addWidget(self.max_tokens_spin)
        advanced_layout.addLayout(layout_max_tokens)

        kokoro_cn_prompt = QHBoxLayout()
        kokoro_cn_prompt.addWidget(self.kokoro_cn_label)
        kokoro_cn_prompt.addWidget(self.kokoro_cn_combo)
        advanced_layout.addLayout(kokoro_cn_prompt)
        
        kokoro_en_prompt = QHBoxLayout()
        kokoro_en_prompt.addWidget(self.kokoro_en_label)
        kokoro_en_prompt.addWidget(self.kokoro_en_combo)
        advanced_layout.addLayout(kokoro_en_prompt)
        
        layout_prompt = QHBoxLayout()
        layout_prompt.addWidget(self.system_prompt_label)
        layout_prompt.addWidget(self.system_prompt_input)
        advanced_layout.addLayout(layout_prompt)
        
        # Set group
        advanced_group.setLayout(advanced_layout)
        
        ############
        #
        # Combine all layouts into a main layout
        main_layout.addLayout(basic_layout)
        main_layout.addWidget(advanced_group)
        main_layout.addWidget(self.apply_button)

        self.setLayout(main_layout)
        
        ########################
        #
        # Signal Connection
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        self.apply_button.clicked.connect(self.on_apply)
        
    # Export Data (static)
    @staticmethod
    def _export_data(data, filepath) -> bool:
        try:
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            return False
        
    # Import Data (static)
    @staticmethod
    def _import_data(filepath, default=None) -> any:
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return default
        except Exception as e:
            return default   
      
    # Load Inference Settings from filepath
    def load_inference_settings(self, file_path = None):
        # Default place
        if file_path is None:
            file_path = params.nathui_backend_config_folder + "inference.config"
        
        # Not exists, pass
        if os.path.exists(file_path) == False:
            print("Warning: inference setting does not exist. Using default...")
            return
            
        inference_settings = self._import_data(file_path)
        # Attr check
        if inference_settings.get("~attr~", None) != "inference_settings":
            return
        
        # Load model
        model = inference_settings["params"]["model"]
        if model in model_list():
            self.model_combo.setCurrentText(model)
            
        # Load temperature
        temperature = inference_settings["params"]["temperature"]
        self.temperature_spin.setValue(temperature)
        
        # Load top_p
        top_p = inference_settings["params"]["top_p"]
        self.top_p_spin.setValue(top_p)
        
        # Load max_tokens
        max_tokens = inference_settings["params"]["max_tokens"]
        self.max_tokens_spin.setValue(max_tokens)
        
        # Load system prompt
        system_prompt = inference_settings["params"]["system_prompt"]
        self.system_prompt_input.setText(system_prompt)
        
        # Load kokoro voicers
        kokoro_cn = inference_settings["params"]["kokoro_cn_voicer"]
        kokoro_en = inference_settings["params"]["kokoro_en_voicer"]
        self.kokoro_cn_combo.setCurrentText(kokoro_cn)
        self.kokoro_en_combo.setCurrentText(kokoro_en)
        return
      
    # Reload all voicers to add to combos
    def reload_all_voicers(self):
        cn_voicers = kokoro_voicer_dict["z"]
        en_voicers = kokoro_voicer_dict["a"]
        self.kokoro_cn_combo.addItems(cn_voicers)
        self.kokoro_cn_combo.setCurrentIndex(0)
        self.kokoro_en_combo.addItems(en_voicers)
        self.kokoro_en_combo.setCurrentIndex(0)
        
    # Reload all models
    def reload_all_models(self):
        models = model_list()
        models.sort()
        self.model_combo.addItems(models)
        self.model_combo.setCurrentIndex(0)
        
    # Choose backgournd colors
    def choose_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_bg_css = f"body {{ background-color: {color.name()}; }}"
            self.bg_color_label.setText(f"背景颜色: {color.name()}")

    # Apply settings
    def on_apply(self):
        settings = self.get_settings()
        self.settingsApplied.emit(settings)

    # Return all settings in a dict
    def get_settings(self) -> dict:
        
        settings = {}
        
        # Theme
        theme = self.theme_combo.currentText()
        settings["theme"] = theme
        
        # Font related
        font_family = self.font_combo.currentFont().family()
        font_size = self.font_size_spin.value()
        settings["font_family"] = font_family
        settings["font_size"] = font_size
        
        # Css
        if theme == "Light":
            bg_css = "body { background-color: #ffffff; color: #000000; }"
        elif theme == "Dark":
            bg_css = "body { background-color: #2b2b2b; color: #e0e0e0; }"
        elif theme == "Custom":
            bg_css = self.current_bg_css if self.current_bg_css else "body { background-color: #ffffff; }"
        else:
            bg_css = "body { background-color: #ffffff; }"
        settings["bg_css"] = bg_css
            
        # Model Selected
        model_selected = self.model_combo.currentText()
        settings["model_selected"] = model_selected
        
        # Temperature
        temperature = self.temperature_spin.value()
        settings["temperature"] = temperature
        
        # Top p
        top_p = self.top_p_spin.value()
        settings["top_p"] = top_p
        
        # Max tokens
        max_tokens = self.max_tokens_spin.value()
        settings["max_tokens"] = max_tokens
        
        # kokoro_cn
        kokoro_cn = self.kokoro_cn_combo.currentText()
        settings["kokoro_cn"] = kokoro_cn
        
        # kokoro_en
        kokoro_en = self.kokoro_en_combo.currentText()
        settings["kokoro_en"] = kokoro_en
        
        # system_prompt
        system_prompt = self.system_prompt_input.toPlainText()
        settings["system_prompt"] = system_prompt
        
        return settings


# Customize the QMainWindow ui logic
class MyQMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_pos = None
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.center_window()

    # Global blank spaces can be dragged
    def mousePressEvent(self, event):  # press
        if event.button() == Qt.LeftButton:
            self.initial_pos = event.pos()
        super().mousePressEvent(event)
        event.accept()

    def mouseMoveEvent(self, event):  # move
        if self.initial_pos is not None:
            delta = event.pos() - self.initial_pos
            self.window().move(
                self.window().x() + delta.x(),
                self.window().y() + delta.y(),
            )
        super().mouseMoveEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):  # release
        self.initial_pos = None
        super().mouseReleaseEvent(event)
        event.accept()

    def about(self):  # about
        QMessageBox.about(self, "关于",
                          "<h4>NathUI</h4>"
                          '<p>author: NathMath@<a href="https://space.bilibili.com/303266889" style="color: #3598db;">bilibili</a></p>'
                          '<p>source:  <a href="https://github.com/dof-studio/NathUI" style="color: #3598db;">dof-studio</a></p>'
                          "<p>Copyright &copy; 2025 NathUI</p>"
                          '<p>License:  <a href="http://www.apache.org/licenses/" style="color: #3598db;">Apache License</a></p>'
                          )

    def center_window(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            x = int((screen_geometry.width() - self.width()) / 2)
            y = int((screen_geometry.height() - self.height()) / 2)
            self.move(x, y)


# NathUI_MainBrowser (Most Exterior Window)
# Main window, manage tabs, toolbars, menus, status bar and global settings
class NathUI_MainBrowser(MyQMainWindow):

    def __init__(self):
        super().__init__()

        # Nath UI @by NathMath
        self.setWindowTitle("Nath UI"  + " v" + version.nathui_version)
        # self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT) # instead of self.center_window

        # Global Initialized Theme
        self.current_theme = "Light"
        self.font_family = DEFAULT_FONT_FAMILY
        self.font_size = DEFAULT_FONT_SIZE
        self.background_css = "body { background-color: #ffffff; }"
        
        # Global Initialized Inference Settings
        self.model_selected = params.nathui_backend_model
        self.temperature = 1.0
        self.top_p = 0.95
        self.max_tokens = 4096
        self.kokoro_cn = kokoro_voicer_dict["z"][0]
        self.kokoro_en = kokoro_voicer_dict["a"][0]
        if debug.nathui_global_lang == "CN":
            self.system_prompt = params.nathui_backend_default_sysprompt_CN
        else:
            self.system_prompt = params.nathui_backend_default_sysprompt_EN
            
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabBarDoubleClicked.connect(self.rename_tab)
        self.setCentralWidget(self.tabs)

        # Status Bar
        self.statusBar().showMessage("Ready")
        
        # Apply settings
        self.load_inference_settings()
        self.apply_settings(None)

        self.create_new_chat_tab()
        self.create_toolbar()
        self.create_menus()
        self.update_main_style()

    # Export Data (static)
    @staticmethod
    def _export_data(data, filepath) -> bool:
        try:
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            return False
        
    # Import Data (static)
    @staticmethod
    def _import_data(filepath, default=None) -> any:
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return default
        except Exception as e:
            return default   
      
    # Save Inference Settings
    def save_inference_settings(self, file_path = None):
        # Default place
        if file_path is None:
            file_path = params.nathui_backend_config_folder + "inference.config"
            
        # Dict
        inference_settings = {
            
            "~attr~": "inference_settings",
        
            "params": {
                # Advanced Inference settings
                "model" : self.model_selected,
                "temperature" : self.temperature,
                "top_p" : self.top_p,
                "max_tokens" : self.max_tokens,
                "system_prompt": self.system_prompt,
                
                # Voice settings
                "kokoro_cn_voicer" : self.kokoro_cn,
                "kokoro_en_voicer" : self.kokoro_en,
                }
        }
        
        self._export_data(inference_settings, file_path)
        
    # Load Inference Settings
    def load_inference_settings(self, file_path = None):
        # Default place
        if file_path is None:
            file_path = params.nathui_backend_config_folder + "inference.config"
        
        # Not exists, pass
        if os.path.exists(file_path) == False:
            print("Warning: inference setting does not exist. Using default...")
            return
            
        inference_settings = self._import_data(file_path)
        # Attr check
        if inference_settings.get("~attr~", None) != "inference_settings":
            return
        
        # Load
        self.model_selected = inference_settings["params"]["model"]
        self.temperature = inference_settings["params"]["temperature"]
        self.top_p = inference_settings["params"]["top_p"]
        self.max_tokens = inference_settings["params"]["max_tokens"]
        self.system_prompt = inference_settings["params"]["system_prompt"]
        self.kokoro_cn = inference_settings["params"]["kokoro_cn_voicer"]
        self.kokoro_en = inference_settings["params"]["kokoro_en_voicer"]
        return
      
    # Form-creation Function: create a toolbar
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        new_chat_action = QAction("新建聊天", self)
        new_chat_action.triggered.connect(self.create_new_chat_tab)
        toolbar.addAction(new_chat_action)

        web_search_action = QAction("访问网络", self)
        web_search_action.triggered.connect(self.create_web_search_tab)
        toolbar.addAction(web_search_action)

        settings_tab_action = QAction("设置", self)
        settings_tab_action.triggered.connect(self.create_settings_tab)
        toolbar.addAction(settings_tab_action)

        save_action = QAction("保存聊天", self)
        save_action.triggered.connect(self.save_current_chat)
        toolbar.addAction(save_action)

        load_action = QAction("导入聊天", self)
        load_action.triggered.connect(self.load_chat)
        toolbar.addAction(load_action)

    # Form-creation Function: create a menu bar
    def create_menus(self):
        menubar = self.menuBar()

        #########################################################
        # File menu toolbox
        file_menu = menubar.addMenu("文件")

        new_chat_action = QAction("新建聊天", self)
        new_chat_action.triggered.connect(self.create_new_chat_tab)
        file_menu.addAction(new_chat_action)

        web_search_action = QAction("访问网络", self)
        web_search_action.triggered.connect(self.create_web_search_tab)
        file_menu.addAction(web_search_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.create_settings_tab)
        file_menu.addAction(settings_action)

        save_chat_action = QAction("保存聊天", self)
        save_chat_action.triggered.connect(self.save_current_chat)
        file_menu.addAction(save_chat_action)

        load_chat_action = QAction("导入聊天", self)
        load_chat_action.triggered.connect(self.load_chat)
        file_menu.addAction(load_chat_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        #########################################################
        # Settings menu toolbox
        settings_menu = menubar.addMenu("设置")
        # Reserved for future use

        # Load settings page
        settings_action_open = QAction("打开设置", self)
        settings_action_open.triggered.connect(self.create_settings_tab)
        settings_menu.addAction(settings_action_open)

        #########################################################
        # Help menu toolbox
        help_menu = menubar.addMenu("帮助")
        # Reserved for future use

        # Load official website
        load_bilipage_nathui = QAction("B站主页", self)
        load_bilipage_nathui.triggered.connect(self.load_bilibili_webpage)
        help_menu.addAction(load_bilipage_nathui)

        # Load official website
        load_webpage_nathui = QAction("开源官网", self)
        load_webpage_nathui.triggered.connect(self.load_opensource_webpage)
        help_menu.addAction(load_webpage_nathui)

        # show about (need to remove the above 2 redundant functions and merge them into about?)
        show_about = QAction("关于", self)
        show_about.triggered.connect(self.about)
        help_menu.addAction(show_about)

        ########
        # Working on
        # @todo update the broswer kernel to support notion document

        # Load notion document website
        # load_notiondoc_nathui = QAction("Notion文档", self)
        # load_notiondoc_nathui.triggered.connect(self.load_notion_webpage)
        # help_menu.addAction(load_notiondoc_nathui)

    # Form-creation Function: create a new chat tab
    def create_new_chat_tab(self) -> int:
        chat_widget = ChatWidget(font_family=self.font_family,
                                 font_size=self.font_size,
                                 extra_css=self.background_css)
        tab_index = self.tabs.addTab(chat_widget, f"聊天 {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(tab_index)
        return tab_index

    # Click - Form-creation Function: create a new web tab
    def create_web_search_tab(self) -> int:
        web_search_widget = WebSearchWidget()
        tab_index = self.tabs.addTab(web_search_widget, f"冲浪 {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(tab_index)
        return tab_index

    # Click - Form-creation Function: create a new setting tab
    def create_settings_tab(self) -> int:
        settings_tab = SettingsTab(
            current_theme=self.current_theme,
            current_bg_css=self.background_css,
            current_font_family=self.font_family,
            current_font_size=self.font_size
        )
        settings_tab.settingsApplied.connect(self.apply_settings)
        tab_index = self.tabs.addTab(settings_tab, "设置")
        self.tabs.setCurrentIndex(tab_index)
        return tab_index

    # Click - Form-closure: close one tab
    def close_tab(self, index) -> int | None:
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            self.tabs.removeTab(index)
            widget.deleteLater()
            return index
        else:
            QMessageBox.warning(self, "提示", "不能关闭最后一个标签页。")
            return None

    # Click - Form-rename
    def rename_tab(self, index) -> int | None:
        if index < 0:
            return None
        current_text = self.tabs.tabText(index)
        new_name, ok = QInputDialog.getText(self, "重命名标签", "请输入新的标签名称：", text=current_text)
        if ok and new_name.strip():
            self.tabs.setTabText(index, new_name.strip())
        return index

    # Clisk - Get current chat widget (used by kernel functions)
    def get_current_chat_widget(self):
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, ChatWidget):
            return current_widget
        return None

    # Click - Save one chat into disk
    def save_current_chat(self):
        # Save chat
        current_chat = self.get_current_chat_widget()
        if current_chat:
            file_path, _ = QFileDialog.getSaveFileName(self, "保存聊天历史", "", "NathUI Files (*.nath);;All Files (*)")
            if file_path:
                # Internal Chat tab calling
                if current_chat.save_conversation(file_path):
                    self.statusBar().showMessage("聊天记录保存成功。", 5000)

    # Click - Load one chat into disk
    def load_chat(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入保存聊天历史", "", "NathUI Files (*.nath);;All Files (*)")
        if file_path:
            chat_widget = ChatWidget(font_family=self.font_family,
                                     font_size=self.font_size,
                                     extra_css=self.background_css)
            # Internal Chat tab calling
            if chat_widget.load_conversation(file_path):
                tab_index = self.tabs.addTab(chat_widget, f"聊天 {self.tabs.count() + 1}")
                self.tabs.setCurrentIndex(tab_index)
                self.statusBar().showMessage("聊天记录导入成功。", 5000)

    # Click - Open the a general tab of website
    def load_general_webpage(self, url):
        # Create a new tab
        index = self.create_web_search_tab()

        # Get current chat widget
        widget = self.tabs.widget(index)
        widget.load_url(url)

    # Click - Open the opensource homepage
    def load_opensource_webpage(self):
        self.load_general_webpage(params.nathui_official_website)

    # Click - Open the notion document homepage
    def load_notion_webpage(self):
        self.load_general_webpage(params.nathui_official_notion_doc)

    # Click - Open the bilibili homepage
    def load_bilibili_webpage(self):
        self.load_general_webpage(params.nathui_official_bilibili_website)

    # Click - Apply settings
    def apply_settings(self, settings = None):
        
        if settings is not None:
            
            # Theme
            self.current_theme = settings["theme"]
            self.font_family = settings["font_family"]
            self.font_size = settings["font_size"]
            self.background_css = settings["bg_css"]
            
            # Inference
            self.model_selected = settings["model_selected"]
            self.temperature = settings["temperature"]
            self.top_p = settings["top_p"]
            self.max_tokens = settings["max_tokens"]
            self.kokoro_cn = settings["kokoro_cn"]
            self.kokoro_en = settings["kokoro_en"]
            self.system_prompt = settings["system_prompt"]
        
        # Apply theme to everything
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, ChatWidget):
                widget.font_family = self.font_family
                widget.font_size = self.font_size
                widget.set_background(self.background_css)
                widget.update_conversation()
        
        # Apply inference to all chats
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, ChatWidget):
                widget.reload_inference_setting(
                                 model=self.model_selected,
                                 temperature=self.temperature,
                                 top_p=self.top_p,
                                 max_tokens=self.max_tokens,
                                 system_prompt=self.system_prompt,
                                 kokoro_cn_voicer=self.kokoro_cn,
                                 kokoro_en_voicer=self.kokoro_en
                    )
                widget.apply_inference_setting()
                
        # Save settings
        self.save_inference_settings()
                
        self.update_main_style()
        self.statusBar().showMessage("设置应用成功。", 5000)

    # Update the main style if changed
    def update_main_style(self):
        stylesheet = generate_stylesheet(self.current_theme, self.background_css)
        self.setStyleSheet(stylesheet)


def main():
    app = QApplication(sys.argv)
    try:
        # show the logo to the windows taskbar
        appid = 'pyqt5.python.ui'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

        window = NathUI_MainBrowser()
        # show icon
        window.setWindowIcon(QIcon("__static__/icon.png"))
        window.show()
        sys.exit(app.exec_())
        
    except Exception as e:
        print("Main Chatbrower.py Error: " + str(e))
        pass


if __name__ == "__main__":
    main()
