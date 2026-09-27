import sys
from PyQt5.QtWidgets import QApplication
from interface import BoogieInterface

def launch_ui():
    app = QApplication(sys.argv)
    ui = BoogieInterface()
    ui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    launch_ui()
