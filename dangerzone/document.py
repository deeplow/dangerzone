import os
import platform
import stat
import tempfile
from typing import Optional

import appdirs


class DocumentHolder(object):
    """
    Keeps track of one document
    """

    def __init__(self, input_file_path: str = None) -> None:
        self._input_filename: Optional[str] = None
        self._output_filename: Optional[str] = None

        if input_file_path:
            self.input_filename = input_file_path

    @property
    def input_filename(self) -> str:
        if self._input_filename is None:
            raise DocumentFilenameException("Input filename has not been set yet.")
        else:
            return self._input_filename

    @input_filename.setter
    def input_filename(self, filename: str) -> None:
        # validate input filename
        try:
            open(filename, "rb")
        except FileNotFoundError:
            raise DocumentFilenameException(
                "Input file not found: make sure you typed it correctly."
            )
        except PermissionError:
            raise DocumentFilenameException(
                "You don't have permission to open the input file."
            )

        self._input_filename = filename

    @property
    def output_filename(self) -> str:
        if self._output_filename is None:
            raise DocumentFilenameException("Output filename has not been set yet.")
        else:
            return self._output_filename

    @output_filename.setter
    def output_filename(self, filename: str) -> None:
        # validate output filename
        if not filename.endswith(".pdf"):
            raise DocumentFilenameException("Safe PDF filename must end in '.pdf'")
        try:
            with open(os.path.abspath(filename), "wb"):
                pass
        except PermissionError:
            raise DocumentFilenameException("Safe PDF filename is not writable")

        self._output_filename = filename


class DocumentFilenameException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
