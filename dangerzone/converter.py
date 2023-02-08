import logging
import os
import shutil
import sys
import time
from typing import Callable, Optional

from colorama import Fore, Style

from .document import Document
from .util import get_resource_path

log = logging.getLogger(__name__)


class Converter:
    """Implements the interview transcription logic"""

    def __init__(self) -> None:
        pass

    def convert(
        self,
        document: Document,
        ocr_lang: Optional[str],
        stdout_callback: Optional[Callable] = None,
    ) -> None:
        document.mark_as_converting()
        try:
            success = self._convert(document, ocr_lang, stdout_callback)
        except Exception:
            success = False
            log.exception(
                f"An exception occurred while converting document '{document.id}'"
            )
        if success:
            document.mark_as_safe()
            if document.archive_after_conversion:
                document.archive()
        else:
            document.mark_as_failed()

    def _convert(
        self,
        document: Document,
        ocr_lang: Optional[str],
        stdout_callback: Optional[Callable] = None,
    ) -> bool:
        log.debug("Dummy converter started:")
        log.debug(
            f"  - document: {os.path.basename(document.input_filename)} ({document.id})"
        )
        log.debug(f"  - ocr     : {ocr_lang}")
        log.debug("\n(simulating conversion)")

        success = True

        progress = [
            [False, "Converting to PDF using GraphicsMagick", 0.0],
            [False, "Separating document into pages", 3.0],
            [False, "Converting page 1/1 to pixels", 5.0],
            [False, "Converted document to pixels", 50.0],
            [False, "Converting page 1/1 from pixels to PDF", 50.0],
            [False, "Merging 1 pages into a single PDF", 95.0],
            [False, "Compressing PDF", 97.0],
            [False, "Safe PDF created", 100.0],
        ]

        for (error, text, percentage) in progress:
            self.print_progress(document, error, text, percentage)  # type: ignore [arg-type]
            if stdout_callback:
                stdout_callback(error, text, percentage)
            if error:
                success = False
            time.sleep(0.2)

        if success:
            shutil.copy(
                get_resource_path("dummy_document.pdf"), document.output_filename
            )

        return success

    def print_progress(
        self, document: Document, error: bool, text: str, percentage: float
    ) -> None:
        s = Style.BRIGHT + Fore.YELLOW + f"[doc {document.id}] "
        s += Fore.CYAN + f"{percentage}% "
        if error:
            s += Style.RESET_ALL + Fore.RED + text
            log.error(s)
        else:
            s += Style.RESET_ALL + text
            log.info(s)

    def get_max_parallel_conversions(self) -> int:
        return 1
