import logging
import os
import pipes
import platform
import shlex
import subprocess
from typing import Dict

from colorama import Fore
from PySide2 import QtCore, QtGui, QtWidgets

if platform.system() == "Darwin":
    import plistlib

elif platform.system() == "Linux":
    import grp
    import getpass
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

        # Preload font
        self.fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)

        # Preload list of PDF viewers on computer
        self.pdf_viewers = self._find_pdf_viewers()

        # Are we done waiting (for Docker Desktop to be installed, or for container to install)
        self.is_waiting_finished = False

    def get_window_icon(self) -> QtGui.QIcon:
        if platform.system() == "Windows":
            path = get_resource_path("dangerzone.ico")
        else:
            path = get_resource_path("icon.png")
        return QtGui.QIcon(path)

    def open_pdf_viewer(self, filename: str) -> None:
        if platform.system() == "Darwin":
            # Open in Preview
            args = ["open", "-a", "Preview.app", filename]

            # Run
            args_str = " ".join(pipes.quote(s) for s in args)
            log.info(Fore.YELLOW + "> " + Fore.CYAN + args_str)
            subprocess.run(args)

        elif platform.system() == "Linux":
            # Get the PDF reader command
            args = shlex.split(self.pdf_viewers[self.settings.get("open_app")])
            # %f, %F, %u, and %U are filenames or URLS -- so replace with the file to open
            for i in range(len(args)):
                if (
                    args[i] == "%f"
                    or args[i] == "%F"
                    or args[i] == "%u"
                    or args[i] == "%U"
                ):
                    args[i] = filename

            # Open as a background process
            args_str = " ".join(pipes.quote(s) for s in args)
            log.info(Fore.YELLOW + "> " + Fore.CYAN + args_str)
            subprocess.Popen(args)

    def _find_pdf_viewers(self) -> Dict[str, str]:
        pdf_viewers: Dict[str, str] = {}
        if platform.system() == "Linux":
            # Find all .desktop files
            for search_path in [
                "/usr/share/applications",
                "/usr/local/share/applications",
                os.path.expanduser("~/.local/share/applications"),
            ]:
                try:
                    for filename in os.listdir(search_path):
                        full_filename = os.path.join(search_path, filename)
                        if os.path.splitext(filename)[1] == ".desktop":

                            # See which ones can open PDFs
                            desktop_entry = DesktopEntry(full_filename)
                            if (
                                "application/pdf" in desktop_entry.getMimeTypes()
                                and desktop_entry.getName() != "dangerzone"
                            ):
                                pdf_viewers[
                                    desktop_entry.getName()
                                ] = desktop_entry.getExec()

                except FileNotFoundError:
                    pass

        return pdf_viewers
