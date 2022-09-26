import enum
import os
import platform
import stat
import tempfile
from typing import Optional

import appdirs

from .errors import DocumentFilenameException

SAFE_EXTENSION = "-safe.pdf"


class Document:
    """Track the state of a single document.

    The Document class is responsible for holding the state of a single
    document, and validating its info.
    """

    doc_counter = 1

    # document conversion state
    STATE_UNCONVERTED = enum.auto()
    STATE_SAFE = enum.auto()
    STATE_FAILED = enum.auto()

    def __init__(self, input_filename: str = None, output_filename: str = None) -> None:
        self.id = Document.doc_counter
        Document.doc_counter += 1

        self._input_filename: Optional[str] = None
        self._output_filename: Optional[str] = None

        if input_filename:
            self.input_filename = input_filename

            if output_filename:
                self.output_filename = output_filename

        self.state = Document.STATE_UNCONVERTED

    @staticmethod
    def normalize_filename(filename: str) -> str:
        return os.path.abspath(filename)

    @staticmethod
    def validate_input_filename(filename: str) -> None:
        try:
            open(filename, "rb")
        except FileNotFoundError as e:
            raise DocumentFilenameException(
                "Input file not found: make sure you typed it correctly."
            ) from e
        except PermissionError as e:
            raise DocumentFilenameException(
                "You don't have permission to open the input file."
            ) from e

    @staticmethod
    def validate_output_filename(filename: str) -> None:
        if not filename.endswith(".pdf"):
            raise DocumentFilenameException("Safe PDF filename must end in '.pdf'")
        try:
            with open(filename, "wb"):
                pass
        except PermissionError as e:
            raise DocumentFilenameException("Safe PDF filename is not writable") from e

    @property
    def input_filename(self) -> str:
        if self._input_filename is None:
            raise DocumentFilenameException("Input filename has not been set yet.")
        else:
            return self._input_filename

    @input_filename.setter
    def input_filename(self, filename: str) -> None:
        filename = self.normalize_filename(filename)
        self.validate_input_filename(filename)
        self._input_filename = filename

    @property
    def output_filename(self) -> str:
        if self._output_filename is None:
            if self._input_filename is not None:
                return self.default_output_filename
            else:
                raise DocumentFilenameException("Output filename has not been set yet.")
        else:
            return self._output_filename

    @output_filename.setter
    def output_filename(self, filename: str) -> None:
        filename = self.normalize_filename(filename)
        self.validate_output_filename(filename)
        self._output_filename = filename

    @property
    def default_output_filename(self) -> str:
        return f"{os.path.splitext(self.input_filename)[0]}{SAFE_EXTENSION}"

    def is_unconverted(self) -> bool:
        return self.state is Document.STATE_UNCONVERTED

    def is_failed(self) -> bool:
        return self.state is Document.STATE_FAILED

    def is_safe(self) -> bool:
        return self.state is Document.STATE_SAFE

    def mark_as_failed(self) -> None:
        self.state = Document.STATE_FAILED

    def mark_as_safe(self) -> None:
        self.state = Document.STATE_SAFE
