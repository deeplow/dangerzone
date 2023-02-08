import logging
import os
import pipes
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Dict

from colorama import Fore
from PySide2 import QtCore, QtGui, QtWidgets

if platform.system() == "Linux":
    from xdg.DesktopEntry import DesktopEntry

from ..logic import DangerzoneCore
from ..settings import Settings
from ..util import get_resource_path

log = logging.getLogger(__name__)


class DangerzoneGui(DangerzoneCore):
    """
    Singleton of shared state / functionality for the GUI and core app logic
    """

    def __init__(self, app: QtWidgets.QApplication) -> None:
        super().__init__()

        # Qt app
        self.app = app

        # Only one output dir is supported in the GUI
        self.output_dir: str = ""

        # Preload font
        self.fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

    def get_window_icon(self) -> QtGui.QIcon:
        if platform.system() == "Windows":
            path = get_resource_path("whisperzone.ico")
        else:
            path = get_resource_path("icon.png")
        return QtGui.QIcon(path)


class Alert(QtWidgets.QDialog):
    def __init__(
        self,
        dangerzone: DangerzoneGui,
        message: str,
        ok_text: str = "Ok",
        has_cancel: bool = True,
        extra_button_text: str = None,
    ) -> None:
        super(Alert, self).__init__()
        self.dangerzone = dangerzone

        self.setWindowTitle("whisperzone")
        self.setWindowIcon(self.dangerzone.get_window_icon())
        self.setModal(True)

        flags = (
            QtCore.Qt.CustomizeWindowHint
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setWindowFlags(flags)

        logo = QtWidgets.QLabel()
        logo.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(get_resource_path("icon.png")))
        )

        label = QtWidgets.QLabel()
        label.setText(message)
        label.setWordWrap(True)

        message_layout = QtWidgets.QHBoxLayout()
        message_layout.addWidget(logo)
        message_layout.addSpacing(10)
        message_layout.addWidget(label, stretch=1)

        ok_button = QtWidgets.QPushButton(ok_text)
        ok_button.clicked.connect(self.clicked_ok)
        if extra_button_text:
            extra_button = QtWidgets.QPushButton(extra_button_text)
            extra_button.clicked.connect(self.clicked_extra)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_button)
        if extra_button_text:
            buttons_layout.addWidget(extra_button)
        if has_cancel:
            cancel_button = QtWidgets.QPushButton("Cancel")
            cancel_button.clicked.connect(self.clicked_cancel)
            buttons_layout.addWidget(cancel_button)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(message_layout)
        layout.addSpacing(10)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def clicked_ok(self) -> None:
        self.done(QtWidgets.QDialog.Accepted)

    def clicked_extra(self) -> None:
        self.done(2)

    def clicked_cancel(self) -> None:
        self.done(QtWidgets.QDialog.Rejected)

    def launch(self) -> int:
        return self.exec_()
