import logging
import os
import shutil
import sys
import time
from typing import Callable, Optional

import qubespdfconverter.client as client

from ..document import Document
from ..util import get_resource_path
from .base import IsolationProvider

log = logging.getLogger(__name__)


class Qubes(IsolationProvider):
    """Uses a disposable qube for performing the conversion"""

    def install(self) -> bool:
        pass

    def _convert(
        self,
        document: Document,
        ocr_lang: Optional[str],
        stdout_callback: Optional[Callable] = None,
    ) -> bool:

        # override the call
        client.CLIENT_VM_CMD = ["/usr/bin/qrexec-client-vm", "@dispvm", "dz.Convert"]
        exit_code = client.main([document.input_filename])
        if exit_code == 0:
            return True
        else:
            return False

    def get_max_parallel_conversions(self) -> int:
        return 1
