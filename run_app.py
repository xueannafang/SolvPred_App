from PyQt6.QtWidgets import QApplication
import sys

from app.ui.main_window import MainWindow


def run_app() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    run_app()
