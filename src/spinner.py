# spinner.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import sys
import time
import threading
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

class Spinner(QWidget):
    def __init__(self, word:str = ""):
        super().__init__()
        self.word = word
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Spinner")
        self.setGeometry(100, 100, 200, 100)
        
        self.label = QLabel(self.word, self)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.animating = True
        self.thread = threading.Thread(target=self.start)
        self.thread.start()
        
    def start(self):
        dots = ""
        while self.animating:
            dots = "." * ((len(dots) % 3) + 1)
            self.label.setText(self.word + f"{dots}")
            time.sleep(0.5)
        
    def stop(self):
        self.animating = False
        self.thread.join()
        self.close()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    spinner = Spinner()
    spinner.show()
    sys.exit(app.exec_())
