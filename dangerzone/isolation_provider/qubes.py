import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from ..document import Document
from ..util import get_resource_path
from .base import IsolationProvider

log = logging.getLogger(__name__)

from ..util import get_subprocess_startupinfo, get_tmp_dir
from .qubes_container_code_symlinked import DangerzoneConverter

CONVERTED_FILE_PATH = (
    "/tmp/safe-output-compressed.pdf"  # FIXME won't work for parallel conversions
)


class Qubes(IsolationProvider):
    """Uses a disposable qube for performing the conversion"""

    def install(self) -> bool:
        pass

    def _convert(
        self,
        document: Document,
        ocr_lang: Optional[str],
        stdout_callback: Optional[Callable] = None,
    ):
        success = False

        # FIXME won't work on windows, nor with multi-conversion
        out_dir = Path("/tmp/dangerzone")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir()

        # Reset hard-coded state
        if os.path.exists(CONVERTED_FILE_PATH):
            os.remove(CONVERTED_FILE_PATH)

        percentage = 0.0

        with open(document.input_filename, "rb") as f:
            # TODO handle lack of memory to start qube
            p = subprocess.Popen(
                ["/usr/bin/qrexec-client-vm", "@dispvm", "dz.Convert"],
                stdin=f,
                stdout=subprocess.PIPE,
                startupinfo=get_subprocess_startupinfo(),
            )
            untrusted_n_pages = p.stdout.read(2)
            n_pages = int.from_bytes(untrusted_n_pages, byteorder="big", signed=False)
            if ocr_lang:
                percentage_per_page = 50.0 / n_pages
            else:
                percentage_per_page = 100.0 / n_pages
            for page in range(1, n_pages + 1):
                # TODO handle too width > MAX_PAGE_WIDTH
                # TODO handle too big height > MAX_PAGE_HEIGHT
                untrusted_width = p.stdout.read(2)
                untrusted_height = p.stdout.read(2)
                width = int.from_bytes(untrusted_width, byteorder="big", signed=False)
                height = int.from_bytes(untrusted_height, byteorder="big", signed=False)
                untrusted_pixels = p.stdout.read(
                    width * height * 3
                )  # three color channels

                # Wrapper code
                with open(f"/tmp/dangerzone/page-{page}.width", "w") as f:
                    f.write(str(width))
                with open(f"/tmp/dangerzone/page-{page}.height", "w") as f:
                    f.write(str(height))
                with open(f"/tmp/dangerzone/page-{page}.rgb", "wb") as f:
                    f.write(untrusted_pixels)

                percentage += percentage_per_page

                text = f"Converting page {page}/{n_pages} to pixels"
                self.print_progress(document, False, text, percentage)
                if stdout_callback:
                    stdout_callback(False, text, percentage)

        # TODO handle leftover code input
        text = "Converted document to pixels"
        self.print_progress(document, False, text, percentage)  # type: ignore [arg-type]
        if stdout_callback:
            stdout_callback(False, text, percentage)

        # FIXME pass OCR stuff properly
        old_environ = dict(os.environ)
        if ocr_lang:
            os.environ["OCR"] = "1"
            os.environ["OCR_LANGUAGE"] = ocr_lang

        # HACK file is symlinked
        converter = DangerzoneConverter()
        asyncio.run(
            converter.pixels_to_pdf()
        )  # TODO add progress updates on second stage

        percentage = 100.0
        text = "Safe PDF created"
        self.print_progress(document, False, text, percentage)  # type: ignore [arg-type]
        if stdout_callback:
            stdout_callback(False, text, percentage)

        # FIXME remove once the OCR args are no longer passed with env vars
        os.environ.clear()
        os.environ.update(old_environ)

        shutil.move(CONVERTED_FILE_PATH, document.output_filename)
        success = True

        return success

    def get_max_parallel_conversions(self) -> int:
        return 1


def running_on_qubes() -> bool:
    # https://www.qubes-os.org/faq/#what-is-the-canonical-way-to-detect-qubes-vm
    return os.path.exists("/usr/share/qubes/marker-vm")
