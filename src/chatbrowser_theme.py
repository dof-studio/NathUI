# chatbrowser_theme.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# Rev 0 version 4.0

# Returns the complete QSS string according to the current theme
def generate_stylesheet(theme, background_css):
    if theme == "Dark":
        return f"""
        QMainWindow {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop: 0 #2c3e50, stop: 1 #4ca1af);
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 14px;
            color: #e0e0e0;
        }}
        QToolBar {{
            background: transparent;
            spacing: 10px;
            padding: 5px;
        }}
        QMenuBar {{
            background: transparent;
        }}
        QMenuBar::item {{
            padding: 5px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: rgba(255, 255, 255, 20%);
        }}
        QLineEdit, QPlainTextEdit, QTextEdit {{
            border: 2px solid #555;
            border-radius: 8px;
            padding: 6px 10px;
            background: #3b3b3b;
            color: #e0e0e0;
            selection-background-color: #4CAF50;
        }}
        QPushButton {{
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3498db, stop:1 #2980b9);
            color: white;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2980b9, stop:1 #3498db);
        }}
        QTabWidget::pane {{
            border: 1px solid #555;
            border-radius: 8px;
            background: #3b3b3b;
        }}
        QTabBar::tab {{
            background: #444;
            border: 1px solid #555;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin: 2px;
            color: #e0e0e0;
        }}
        QTabBar::tab:selected {{
            background: #3b3b3b;
            border-bottom: none;
        }}
        QSplitter::handle {{
            background: #666;
            width: 8px;
            margin: 0 2px;
        }}
        """
    # NathMath@bilibili/DOF Studio
    elif theme == "Light":
        return f"""
        QMainWindow {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop: 0 #f5f7fa, stop: 1 #c3cfe2);
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 14px;
        }}
        QToolBar {{
            background: transparent;
            spacing: 10px;
            padding: 5px;
        }}
        QMenuBar {{
            background: transparent;
        }}
        QMenuBar::item {{
            padding: 5px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: rgba(0, 0, 0, 20%);
        }}
        QLineEdit, QPlainTextEdit, QTextEdit {{
            border: 2px solid #ccc;
            border-radius: 8px;
            padding: 6px 10px;
            background: #fff;
            color: #000;
            selection-background-color: #4CAF50;
        }}
        QPushButton {{
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45a049);
            color: white;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #45a049, stop:1 #4CAF50);
        }}
        QTabWidget::pane {{
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fff;
        }}
        QTabBar::tab {{
            background: #eee;
            border: 1px solid #ddd;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin: 2px;
            color: #000;
        }}
        QTabBar::tab:selected {{
            background: #fff;
            border-bottom: none;
        }}
        QSplitter::handle {{
            background: #ccc;
            width: 8px;
            margin: 0 2px;
        }}
        """
    elif theme == "Custom":
        return f"""
        QMainWindow {{
            {background_css}
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 14px;
        }}
        QToolBar {{
            background: transparent;
            spacing: 10px;
            padding: 5px;
        }}
        QMenuBar {{
            background: transparent;
        }}
        QMenuBar::item {{
            padding: 5px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: rgba(0, 0, 0, 20%);
        }}
        QLineEdit, QPlainTextEdit, QTextEdit {{
            border: 2px solid #ccc;
            border-radius: 8px;
            padding: 6px 10px;
            background: #fff;
            selection-background-color: #4CAF50;
        }}
        QPushButton {{
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45a049);
            color: white;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #45a049, stop:1 #4CAF50);
        }}
        QTabWidget::pane {{
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fff;
        }}
        QTabBar::tab {{
            background: #eee;
            border: 1px solid #ddd;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 16px;
            margin: 2px;
        }}
        QTabBar::tab:selected {{
            background: #fff;
            border-bottom: none;
        }}
        QSplitter::handle {{
            background: #ccc;
            width: 8px;
            margin: 0 2px;
        }}
        """
    else:
        return ""
