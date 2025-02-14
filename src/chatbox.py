import sys
import time
import markdown
import json
from PyQt5.QtCore import Qt, QUrl, QPoint, QCoreApplication
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLineEdit, QPushButton, QTabWidget, QTabBar, QToolButton,
                            QFileDialog, QMenu, QAction, QStyleFactory, QDialog, QComboBox,
                            QScrollArea, QSpinBox, QCheckBox, QLabel, QTextEdit)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QColor, QPalette, QIcon, QCursor, QTextCursor

# ======================
# 自定义组件
# ======================
class ModernInputField(QLineEdit):
    """现代风格输入框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("输入消息...")
        self.setMinimumHeight(45)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #c0c0c0;
                border-radius: 15px;
                padding: 8px 15px;
                font-size: 16px;
                background: rgba(255,255,255,0.9);
                margin: 5px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                background: white;
            }
        """)

class IconButton(QPushButton):
    """图标文本按钮"""
    def __init__(self, icon_name, text, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(f"icons/{icon_name}.png"))  # 需要图标资源
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                border: none;
                border-radius: 8px;
                background: #f0f0f0;
                color: #404040;
                margin: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #e0e0e0;
            }
            QPushButton:pressed {
                background: #d0d0d0;
            }
        """)

class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setGeometry(300, 300, 400, 500)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # 命令行输入
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("输入命令...")
        self.command_edit.returnPressed.connect(self.execute_command)
        main_layout.addWidget(self.command_edit)

        # 选项菜单
        options_group = QWidget()
        options_layout = QVBoxLayout()

        # 主题选择
        theme_layout = QHBoxLayout()
        theme_label = QLabel("主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "深色", "海洋"])
        self.theme_combo.currentIndexChanged.connect(self.apply_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        options_layout.addLayout(theme_layout)

        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_label = QLabel("字体大小:")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setValue(16)
        self.font_size_spin.setRange(10, 30)
        self.font_size_spin.valueChanged.connect(self.adjust_font_size)
        font_size_layout.addWidget(font_size_label)
        font_size_layout.addWidget(self.font_size_spin)
        options_layout.addLayout(font_size_layout)

        # 消息显示
        self.show_timestamps = QCheckBox("显示时间戳")
        self.show_timestamps.setChecked(True)
        self.show_timestamps.stateChanged.connect(self.toggle_timestamps)
        options_layout.addWidget(self.show_timestamps)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # 命令历史
        self.command_history = QTextEdit()
        self.command_history.setReadOnly(True)
        main_layout.addWidget(self.command_history)

        self.setLayout(main_layout)

    def execute_command(self):
        command = self.command_edit.text().strip()
        if command:
            self.command_history.append(f"> {command}")
            parts = command.split()
            if parts[0] == "/theme":
                theme = parts[1] if len(parts) > 1 else "default"
                self.parent.apply_theme(theme)
            elif parts[0] == "/clear":
                self.parent.clear_all_sessions()
            elif parts[0] == "/help":
                self.show_help()
            self.command_edit.clear()

    def show_help(self):
        help_text = """
        帮助：
        /theme [主题名] - 切换主题
        /clear - 清除所有会话
        /help - 显示帮助信息
        """
        self.command_history.append(help_text)

    def apply_theme(self, index):
        themes = ["default", "dark", "ocean"]
        theme = themes[index]
        self.parent.apply_theme(theme)

    def adjust_font_size(self, size):
        for i in range(self.parent.tabs.count()):
            tab = self.parent.tabs.widget(i)
            tab.browser.setZoomFactor(size / 16)

    def toggle_timestamps(self, state):
        QCoreApplication.instance().show_timestamps = state == Qt.Checked

# ======================
# 聊天会话组件
# ======================
class ChatSession(QWidget):
    """单个聊天会话实例"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conversation_md = ""
        self.rounds = 0
        self.background = ""
        self.init_ui()
        self.apply_theme("default")

    def init_ui(self):
        # 浏览器组件
        self.browser = QWebEngineView()
        
        # 功能按钮
        self.send_btn = IconButton("send", "发送", self)
        self.clear_btn = IconButton("clear", "清空", self)
        self.style_btn = IconButton("palette", "主题", self)
        
        # 输入区域
        self.input_field = ModernInputField(self)
        self.input_field.returnPressed.connect(self.send_message)
        
        # 布局管理
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.style_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.send_btn)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.browser, 1)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.input_field)
        self.setLayout(main_layout)

        # 信号连接
        self.send_btn.clicked.connect(self.send_message)
        self.clear_btn.clicked.connect(self.clear_history)
        self.style_btn.clicked.connect(lambda: self.parent().show_theme_menu())

    def send_message(self):
        text = self.input_field.text().strip()
        if text:
            timestamp = time.strftime("[%H:%M:%S]", time.localtime())
            self.append_message("user", f"{timestamp} {text}")
            self.input_field.clear()
            # 模拟AI回复
            self.append_message("assistant", f"{timestamp} 这是对 '{text}' 的模拟回复")

    def append_message(self, role, content):
        self.conversation_md += f"\n**{role.capitalize()}:** {content}\n"
        self.update_display()

    def clear_history(self):
        self.conversation_md = ""
        self.browser.setHtml("")
        self.rounds = 0

    def update_display(self):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    {self.background};
                    font-family: 'Segoe UI', sans-serif;
                    padding: 20px;
                    color: #333;
                    font-size: {QCoreApplication.instance().font_size}px;
                }}
                .message {{
                    background: rgba(255,255,255,0.8);
                    border-radius: 10px;
                    padding: 15px;
                    margin: 10px 0;
                    backdrop-filter: blur(5px);
                }}
                strong {{ color: #0078d4; }}
            </style>
        </head>
        <body>
            {markdown.markdown(self.conversation_md)}
        </body>
        </html>
        """
        self.browser.setHtml(html)

    def apply_theme(self, theme):
        themes = {
            "default": "background: #f0f2f5;",
            "dark": """
                background: #2d2d2d;
                color: white;
            """,
            "ocean": "background: url('backgrounds/ocean.jpg') no-repeat center/cover;"
        }
        self.background = themes.get(theme, themes["default"])
        self.update_display()

# ======================
# 主浏览器窗口
# ======================
class ChatBrowser(QMainWindow):
    """主浏览器窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NathChat Browser")
        self.resize(1400, 800)
        self.init_ui()
        self.setWindowIcon(QIcon("icons/app.png"))
        self.show_timestamps = True
        self.font_size = 16

    def init_ui(self):
        # 标签页系统
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabBar().setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        
        # 新建标签按钮
        self.new_tab_btn = QToolButton()
        self.new_tab_btn.setText("+")
        self.new_tab_btn.clicked.connect(self.new_tab)
        self.tabs.setCornerWidget(self.new_tab_btn, Qt.TopRightCorner)

        # 工具栏
        self.init_toolbar()

        self.setCentralWidget(self.tabs)
        self.new_tab()

    def init_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        actions = [
            ("new", "新建会话", self.new_tab),
            ("save", "保存会话", self.save_session),
            ("open", "导入会话", self.import_session),
            ("theme", "更换主题", self.show_theme_menu),
            ("settings", "设置", self.show_settings)
        ]
        for icon, text, callback in actions:
            action = QAction(QIcon(f"icons/{icon}.png"), text, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)

    def new_tab(self, title="新会话"):
        tab = ChatSession(self)
        self.tabs.addTab(tab, title)
        self.tabs.setCurrentWidget(tab)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            widget = self.tabs.widget(index)
            widget.deleteLater()
            self.tabs.removeTab(index)

    def show_theme_menu(self):
        menu = QMenu(self)
        themes = ["default", "dark", "ocean"]
        for theme in themes:
            action = menu.addAction(theme.capitalize())
            action.triggered.connect(lambda _, t=theme: self.apply_theme(t))
        menu.exec_(QCursor.pos())

    def apply_theme(self, theme):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).apply_theme(theme)

    def save_session(self):
        current_tab = self.tabs.currentWidget()
        path, _ = QFileDialog.getSaveFileName(
            self, "保存会话", "", "Markdown Files (*.md)")
        if path:
            with open(path, 'w') as f:
                f.write(current_tab.conversation_md)

    def import_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入会话", "", "Markdown Files (*.md)")
        if path:
            with open(path, 'r') as f:
                content = f.read()
                current_tab = self.tabs.currentWidget()
                current_tab.conversation_md = content
                current_tab.update_display()

    def show_settings(self):
        self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show()

    def clear_all_sessions(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab.clear_history()

# ======================
# 应用启动
# ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 全局样式
    app.setStyleSheet("""
        QMainWindow {
            background: #f5f5f5;
        }
        QTabWidget::pane {
            border: none;
        }
        QTabBar::tab {
            padding: 8px 15px;
            background: #e0e0e0;
            border-radius: 4px;
            margin: 2px;
        }
        QTabBar::tab:selected {
            background: #0078d4;
            color: white;
        }
    """)

    window = ChatBrowser()
    window.show()
    sys.exit(app.exec_())