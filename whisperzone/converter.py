import logging
import os
import pipes
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Callable, Optional, Tuple

from colorama import Fore, Style

from .document import Document
from .util import get_resource_path

log = logging.getLogger(__name__)

# Define startupinfo for subprocesses
if platform.system() == "Windows":
    startupinfo = subprocess.STARTUPINFO()  # type: ignore [attr-defined]
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore [attr-defined]
else:
    startupinfo = None


class Converter:
    """Implements the interview transcription logic"""

    def transcribe(
        self,
        document: Document,
        language: str,
        model: str,
        output_format: str,
        stdout_callback: Optional[Callable] = None,
    ) -> bool:

        args = [
            "whisper",
            document.input_filename,
            "--language",
            language,
            "--model",
            model,
            "--output_format",
            output_format,
        ]
        args_str = " ".join(pipes.quote(s) for s in args)
        log.info("> " + args_str)

        with subprocess.Popen(
            args,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            startupinfo=startupinfo,
        ) as p:
            if p.stdout is not None:
                for line in p.stdout:
                    result = self.parse_progress(document, line)
                    if result is None:
                        continue
                    else:
                        (error, text, percentage) = result
                        if stdout_callback:
                            stdout_callback(error, text, percentage)

            p.communicate()
            return p.returncode == 0

    def convert(
        self,
        document: Document,
        language: Optional[str] = "English",
        model: Optional[str] = "small",
        output_format: Optional[str] = "txt",
        stdout_callback: Optional[Callable] = None,
    ) -> None:
        document.mark_as_converting()

        log.debug(
            f"transcribing {os.path.basename(document.input_filename)} in {language}"
        )

        # Get max num minutes
        args = [
            "ffmpeg",
            "-v",
            "quiet",
            "-stats",
            "-i",
            document.input_filename,
            "-f",
            "null",
            "-",
        ]
        p = subprocess.run(args, universal_newlines=True, capture_output=True)

        max_time = p.stderr.rstrip().split("\n")[-1].split()[1][5:]
        self.start_time = datetime.strptime("00:00.000", "%M:%S.%f")
        end_time = datetime.strptime(max_time, "%H:%M:%S.%f")
        self.duration = (end_time - self.start_time).seconds

        try:
            success = self.transcribe(
                document, language, model, output_format, stdout_callback
            )
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

    def parse_progress(
        self, document: Document, line: str
    ) -> None | Tuple[bool, str, int]:
        """
        Parses a line returned by the container.
        """
        # Installing model progress format
        # 0%|                                               | 0.00/139M [00:00<?, ?iB/s]
        # 23%|████████▊                             | 32.3M/139M [00:03<00:11, 10.0MiB/s]
        # 100%|███████████████████████████████████████| 139M/139M [00:15<00:00, 9.36MiB/s]
        installing_model = re.search("^\s*(\d+)%\|", line)

        # Output text format
        # [00:00.000 --> 00:06.600]  This is a Libravox recording. All Libravox recordings are in the public domain. For more information
        # [26:03.440 --> 26:08.360]  There are wealthy gentlemen in England who drive four horse passenger coaches twenty
        transcribing = re.search(
            "^\[(\d+:\d\d\.\d{3}) --> (\d+:\d\d\.\d{3})\]  (.*)", line
        )

        if installing_model and installing_model.group(0):
            progress = float(installing_model.group(1))
            error = False
            text = f"Installing model ({progress}%)"
            percentage = progress * 0.3  # 30% of the progress is to install the model

        elif transcribing and transcribing.group(0):
            end_time = datetime.strptime(transcribing.group(2), "%M:%S.%f")
            duration_percentage = (end_time - self.start_time).seconds / self.duration
            transcribed_line = transcribing.group(2)
            percentage = min(100.0, 30 + duration_percentage * 70)
            error = False
            text = transcribed_line
        else:
            # ignore
            error_message = f"Unexpected output:\n\n\t {line}"
            log.error(error_message)
            return None

        self.print_progress(document, error, text, percentage)
        return (error, text, percentage)

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
