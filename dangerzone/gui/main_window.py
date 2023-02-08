import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from abc import abstractmethod
from multiprocessing.pool import ThreadPool
from typing import List, Optional

from colorama import Fore, Style
from PySide2 import QtCore, QtGui, QtWidgets

from .. import errors
from ..document import SAFE_EXTENSION, Document
from ..util import get_resource_path, get_subprocess_startupinfo, get_version
from .logic import Alert, DangerzoneGui

log = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super(MainWindow, self).__init__()
        self.dangerzone = dangerzone

        self.setWindowTitle("Whisperzone")
        self.setWindowIcon(self.dangerzone.get_window_icon())

        self.setMinimumWidth(600)
        if platform.system() == "Darwin":
            # FIXME have a different height for macOS due to font-size inconsistencies
            # https://github.com/freedomofpress/dangerzone/issues/270
            self.setMinimumHeight(470)
        else:
            self.setMinimumHeight(430)

        # Header
        logo = QtWidgets.QLabel()
        logo.setPixmap(
            QtGui.QPixmap.fromImage(QtGui.QImage(get_resource_path("icon.png")))
        )
        header_label = QtWidgets.QLabel("Whisperzone")
        header_label.setFont(self.dangerzone.fixed_font)
        header_label.setStyleSheet("QLabel { font-weight: bold; font-size: 50px; }")
        header_version_label = QtWidgets.QLabel(get_version())
        header_version_label.setProperty("class", "version")  # type: ignore [arg-type]
        header_version_label.setAlignment(QtCore.Qt.AlignBottom)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addStretch()
        header_layout.addWidget(logo)
        header_layout.addSpacing(10)
        header_layout.addWidget(header_label)
        header_layout.addWidget(header_version_label)
        header_layout.addStretch()

        # Waiting widget replaces content widget while container runtime isn't available
        self.waiting_widget: WaitingWidgetFFmpeg = WaitingWidgetFFmpeg(self.dangerzone)
        self.waiting_widget.finished.connect(self.waiting_finished)

        # Content widget, contains all the window content
        self.content_widget = ContentWidget(self.dangerzone)
        self.waiting_widget.show()
        self.content_widget.hide()

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(header_layout)
        layout.addWidget(self.waiting_widget, stretch=1)
        layout.addWidget(self.content_widget, stretch=1)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.waiting_widget.check_state()

        self.show()

    def waiting_finished(self) -> None:
        self.dangerzone.is_waiting_finished = True
        self.waiting_widget.hide()
        self.content_widget.show()

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        alert_widget = Alert(
            self.dangerzone,
            message="Some documents are still being converted.\n Are you sure you want to quit?",
            ok_text="Abort conversions",
        )
        converting_docs = self.dangerzone.get_converting_documents()
        if not converting_docs:
            e.accept()
        else:
            accept_exit = alert_widget.exec_()
            if not accept_exit:
                e.ignore()
                return
            else:
                e.accept()

        self.dangerzone.app.quit()


class WaitingWidgetAbstract(QtWidgets.QWidget):
    finished = QtCore.Signal()

    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super(WaitingWidgetAbstract, self).__init__()
        self.dangerzone = dangerzone

        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setOpenExternalLinks(True)
        self.label.setStyleSheet("QLabel { font-size: 20px; }")

        # Buttons
        check_button = QtWidgets.QPushButton("Check Again")
        check_button.clicked.connect(self.check_state)
        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(check_button)
        buttons_layout.addStretch()
        self.buttons = QtWidgets.QWidget()
        self.buttons.setLayout(buttons_layout)

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.buttons)
        layout.addStretch()
        self.setLayout(layout)

        # Check the state
        self.check_state()

    @abstractmethod
    def check_state(self) -> None:
        pass

    @abstractmethod
    def state_change(self, state: str) -> None:
        pass


class WaitingWidgetFFmpeg(WaitingWidgetAbstract):
    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super(WaitingWidgetFFmpeg, self).__init__(dangerzone)

    def check_state(self) -> None:
        state: Optional[str] = None
        try:
            subprocess.run(
                ["ffmpeg", "--help"],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            state = "ffmpeg_installed"
        except FileNotFoundError:
            state = "ffmpeg_not_installed"

        # Update the state
        self.state_change(state)

    def state_change(self, state: str) -> None:
        if state == "ffmpeg_not_installed":
            self.label.setText(
                "<strong>Whisperzone Requires FFmpeg</strong><br><br><a href='https://ffmpeg.org/download.html#get-packages'>Download FFmpeg</a> and install it."
            )
            self.buttons.show()
        elif state == "ffmpeg_installed":
            self.finished.emit()


class ContentWidget(QtWidgets.QWidget):
    documents_added = QtCore.Signal(list)

    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super(ContentWidget, self).__init__()
        self.dangerzone = dangerzone
        self.conversion_started = False

        # Doc selection widget
        self.doc_selection_widget = DocSelectionWidget()
        self.doc_selection_widget.documents_selected.connect(self.documents_selected)

        # Settings
        self.settings_widget = SettingsWidget(self.dangerzone)
        self.documents_added.connect(self.settings_widget.documents_added)
        self.settings_widget.start_clicked.connect(self.start_clicked)
        self.settings_widget.hide()

        # Convert
        self.documents_list = DocumentsListWidget(self.dangerzone)
        self.documents_added.connect(self.documents_list.documents_added)
        self.settings_widget.start_clicked.connect(self.documents_list.start_conversion)
        self.documents_list.hide()

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.settings_widget, stretch=1)
        layout.addWidget(self.documents_list, stretch=1)
        layout.addWidget(self.doc_selection_widget, stretch=1)
        self.setLayout(layout)

    def documents_selected(self, new_docs: List[Document]) -> None:
        if not self.conversion_started:

            # assumed all files in batch are in the same directory
            first_doc = new_docs[0]
            output_dir = os.path.dirname(first_doc.input_filename)
            if not self.dangerzone.output_dir:
                self.dangerzone.output_dir = output_dir
            elif self.dangerzone.output_dir != output_dir:
                Alert(
                    self.dangerzone,
                    message="Dangerzone does not support adding documents from multiple locations.\n\n The newly added documents were ignored.",
                    has_cancel=False,
                ).exec_()
                return
            else:
                self.dangerzone.output_dir = output_dir

            for doc in new_docs.copy():
                try:
                    self.dangerzone.add_document(doc)
                except errors.AddedDuplicateDocumentException:
                    new_docs.remove(doc)
                    Alert(
                        self.dangerzone,
                        message=f"Document '{doc.input_filename}' has already been added for conversion.",
                        has_cancel=False,
                    ).exec_()

            self.doc_selection_widget.hide()
            self.settings_widget.show()

            if len(new_docs) > 0:
                self.documents_added.emit(new_docs)

        else:
            Alert(
                self.dangerzone,
                message="Dangerzone does not support adding documents after the conversion has started.",
                has_cancel=False,
            ).exec_()

    def start_clicked(self) -> None:
        self.conversion_started = True
        self.settings_widget.hide()
        self.documents_list.show()


class DocSelectionWidget(QtWidgets.QWidget):
    documents_selected = QtCore.Signal(list)

    def __init__(self) -> None:
        super(DocSelectionWidget, self).__init__()

        # Dangerous document selection
        self.dangerous_doc_label = QtWidgets.QLabel()
        self.dangerous_doc_label.hide()
        self.dangerous_doc_button = QtWidgets.QPushButton("Select audio interviews ...")
        self.dangerous_doc_button.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 10px; }"
        )
        self.dangerous_doc_button.clicked.connect(self.dangerous_doc_button_clicked)

        dangerous_doc_layout = QtWidgets.QHBoxLayout()
        dangerous_doc_layout.addStretch()
        dangerous_doc_layout.addWidget(self.dangerous_doc_button)
        dangerous_doc_layout.addStretch()

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addStretch()
        layout.addLayout(dangerous_doc_layout)
        layout.addStretch()
        self.setLayout(layout)

    def dangerous_doc_button_clicked(self) -> None:
        (filenames, _) = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Open documents",
            filter="Documents (*.mp3 *.m4a *.wav)",
        )
        if filenames == []:
            # no files selected
            return

        documents = [Document(filename) for filename in filenames]
        self.documents_selected.emit(documents)


class SettingsWidget(QtWidgets.QWidget):
    start_clicked = QtCore.Signal()

    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super(SettingsWidget, self).__init__()
        self.dangerzone = dangerzone

        # Num Docs Selected
        self.docs_selected_label = QtWidgets.QLabel("No documents selected")
        self.docs_selected_label.setAlignment(QtCore.Qt.AlignCenter)
        self.docs_selected_label.setContentsMargins(0, 0, 0, 20)
        self.docs_selected_label.setProperty("class", "docs-selection")  # type: ignore [arg-type]

        # Interview language
        self.lang_label = QtWidgets.QLabel("Language")
        self.lang_combobox = QtWidgets.QComboBox()
        for k in self.dangerzone.languages:
            self.lang_combobox.addItem(k, self.dangerzone.languages[k])
        lang_layout = QtWidgets.QHBoxLayout()
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combobox)
        lang_layout.addStretch()

        # Button
        self.start_button = QtWidgets.QPushButton()
        self.start_button.clicked.connect(self.start_button_clicked)
        self.start_button.setStyleSheet(
            "QPushButton { font-size: 16px; font-weight: bold; }"
        )
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addStretch()

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(lang_layout)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)

        # Load values from settings
        index = self.lang_combobox.findText(self.dangerzone.settings.get("language"))
        if index != -1:
            self.lang_combobox.setCurrentIndex(index)

    def update_ui(self) -> None:
        pass

    def documents_added(self, new_docs: List[Document]) -> None:
        self.update_doc_n_labels()
        self.update_ui()

    def update_doc_n_labels(self) -> None:
        """Updates labels dependent on the number of present documents"""
        n_docs = len(self.dangerzone.get_unconverted_documents())

        if n_docs == 1:
            self.start_button.setText("Convert to Safe Document")
            self.docs_selected_label.setText(f"1 document selected")
        else:
            self.start_button.setText("Convert to Safe Documents")
            self.docs_selected_label.setText(f"{n_docs} documents selected")

    def start_button_clicked(self) -> None:
        # Update settings
        self.dangerzone.settings.set("language", self.lang_combobox.currentText())
        self.dangerzone.settings.save()

        # Start!
        self.start_clicked.emit()


class ConvertTask(QtCore.QObject):
    finished = QtCore.Signal(bool)
    update = QtCore.Signal(bool, str, int)

    def __init__(
        self,
        dangerzone: DangerzoneGui,
        document: Document,
        language: str = None,
    ) -> None:
        super(ConvertTask, self).__init__()
        self.document = document
        self.language = language
        self.error = False
        self.dangerzone = dangerzone

    def convert_document(self) -> None:
        self.dangerzone.converter.convert(
            self.document,
            self.language,
            self.stdout_callback,
        )
        self.finished.emit(self.error)

    def stdout_callback(self, error: bool, text: str, percentage: int) -> None:
        if error:
            self.error = True

        self.update.emit(error, text, percentage)


class DocumentsListWidget(QtWidgets.QListWidget):
    def __init__(self, dangerzone: DangerzoneGui) -> None:
        super().__init__()
        self.dangerzone = dangerzone
        self.document_widgets: List[DocumentWidget] = []

        # Initialize thread_pool only on the first conversion
        # to ensure docker-daemon detection logic runs first
        self.thread_pool_initized = False

    def documents_added(self, new_docs: List[Document]) -> None:
        for document in new_docs:
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(500, 50))
            widget = DocumentWidget(self.dangerzone, document)
            self.addItem(item)
            self.setItemWidget(item, widget)
            self.document_widgets.append(widget)

    def start_conversion(self) -> None:
        if not self.thread_pool_initized:
            max_jobs = self.dangerzone.converter.get_max_parallel_conversions()
            self.thread_pool = ThreadPool(max_jobs)

        for doc_widget in self.document_widgets:
            task = ConvertTask(
                self.dangerzone, doc_widget.document, self.get_language()
            )
            task.update.connect(doc_widget.update_progress)
            task.finished.connect(doc_widget.all_done)
            self.thread_pool.apply_async(task.convert_document)

    def get_language(self) -> Optional[str]:
        language = self.dangerzone.languages[
            self.dangerzone.settings.get("language")
        ]
        return language


class DocumentWidget(QtWidgets.QWidget):
    def __init__(
        self,
        dangerzone: DangerzoneGui,
        document: Document,
    ) -> None:
        super().__init__()
        self.dangerzone = dangerzone
        self.document = document

        self.error = False

        # Dangerous document label
        self.dangerous_doc_label = QtWidgets.QLabel()
        self.dangerous_doc_label.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
        )
        self.dangerous_doc_label.setText(os.path.basename(self.document.input_filename))
        self.dangerous_doc_label.setMinimumWidth(200)
        self.dangerous_doc_label.setMaximumWidth(200)

        # Conversion status images
        self.img_status_unconverted = self.load_status_image("status_unconverted.png")
        self.img_status_converting = self.load_status_image("status_converting.png")
        self.img_status_failed = self.load_status_image("status_failed.png")
        self.img_status_safe = self.load_status_image("status_safe.png")
        self.status_image = QtWidgets.QLabel()
        self.status_image.setMaximumWidth(15)
        self.status_image.setPixmap(self.img_status_unconverted)

        # Error label
        self.error_label = QtWidgets.QLabel()
        self.error_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        self.error_label.setWordWrap(True)
        self.error_label.hide()  # only show on error

        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        # Layout
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.status_image)
        layout.addWidget(self.dangerous_doc_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.error_label)
        self.setLayout(layout)

    def update_progress(self, error: bool, text: str, percentage: int) -> None:
        self.update_status_image()
        if error:
            self.error = True
            self.error_label.setText(text)
            self.error_label.setToolTip(text)
            self.error_label.show()
            self.progress.hide()
        else:
            self.progress.setToolTip(text)
            self.progress.setValue(percentage)

    def load_status_image(self, filename: str) -> QtGui.QPixmap:
        path = get_resource_path(filename)
        img = QtGui.QImage(path)
        image = QtGui.QPixmap.fromImage(img)
        return image.scaled(QtCore.QSize(15, 15))

    def update_status_image(self) -> None:
        if self.document.is_unconverted():
            self.status_image.setPixmap(self.img_status_unconverted)
        elif self.document.is_converting():
            self.status_image.setPixmap(self.img_status_converting)
        elif self.document.is_failed():
            self.status_image.setPixmap(self.img_status_failed)
        elif self.document.is_safe():
            self.status_image.setPixmap(self.img_status_safe)

    def all_done(self) -> None:
        self.update_status_image()

        if self.error:
            return


class QLabelClickable(QtWidgets.QLabel):
    """QLabel with a 'clicked' event"""

    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.clicked.emit()
