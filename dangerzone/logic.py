import concurrent.futures
import gzip
import json
import logging
import pathlib
import platform
import shutil
import subprocess
import sys
from typing import Callable, List, Optional

import appdirs
import colorama

from . import errors
from .converter import Converter
from .document import Document
from .settings import Settings
from .util import get_resource_path

log = logging.getLogger(__name__)


class DangerzoneCore(object):
    """
    Singleton of shared state / functionality throughout the app
    """

    def __init__(self) -> None:
        # Initialize terminal colors
        colorama.init(autoreset=True)

        # App data folder
        self.appdata_path = appdirs.user_config_dir("whisperzone")

        # Languages supported by whisper
        with open(get_resource_path("languages.json"), "r") as f:
            self.languages = json.load(f)

        # Models provided by whisper
        with open(get_resource_path("models.json"), "r") as f:
            self.models = json.load(f)

        # Load settings
        self.settings = Settings(self)

        self.documents: List[Document] = []

        self.converter = Converter()

    def add_document_from_filename(
        self,
        input_filename: str,
        output_filename: Optional[str] = None,
        archive: bool = False,
    ) -> None:
        doc = Document(input_filename, output_filename, archive=archive)
        self.add_document(doc)

    def add_document(self, doc: Document) -> None:
        if doc in self.documents:
            raise errors.AddedDuplicateDocumentException()
        self.documents.append(doc)

    def get_unconverted_documents(self) -> List[Document]:
        return [doc for doc in self.documents if doc.is_unconverted()]

    def get_safe_documents(self) -> List[Document]:
        return [doc for doc in self.documents if doc.is_safe()]

    def get_failed_documents(self) -> List[Document]:
        return [doc for doc in self.documents if doc.is_failed()]

    def get_converting_documents(self) -> List[Document]:
        return [doc for doc in self.documents if doc.is_converting()]
