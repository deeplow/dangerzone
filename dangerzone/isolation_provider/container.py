import gzip
import json
import logging
import os
import pipes
import platform
import shutil
import subprocess
import tempfile
from typing import Callable, List, Optional, Tuple

import appdirs

from ..document import Document
from ..util import get_resource_path, get_subprocess_startupinfo
from . import IsolationProvider

# Define startupinfo for subprocesses
if platform.system() == "Windows":
    startupinfo = subprocess.STARTUPINFO()  # type: ignore [attr-defined]
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore [attr-defined]
else:
    startupinfo = None


log = logging.getLogger(__name__)


class NoContainerTechException(Exception):
    def __init__(self, container_tech: str) -> None:
        super().__init__(f"{container_tech} is not installed")


class Container(IsolationProvider):

    # Name of the dangerzone container
    CONTAINER_NAME = "dangerzone.rocks/dangerzone"

    def __init__(self) -> None:
        pass

    def get_runtime_name(self) -> str:
        if platform.system() == "Linux":
            runtime_name = "podman"
        else:
            # Windows, Darwin, and unknown use docker for now, dangerzone-vm eventually
            runtime_name = "docker"
        return runtime_name

    def get_runtime(self) -> str:
        container_tech = self.get_runtime_name()
        runtime = shutil.which(container_tech)
        if runtime is None:
            raise NoContainerTechException(container_tech)
        return runtime

    def install(self) -> bool:
        """
        Make sure the podman container is installed. Linux only.
        """
        if self.is_container_installed():
            return True

        # Load the container into podman
        log.info("Installing Dangerzone container image...")

        p = subprocess.Popen(
            [self.get_runtime(), "load"],
            stdin=subprocess.PIPE,
            startupinfo=get_subprocess_startupinfo(),
        )

        chunk_size = 10240
        compressed_container_path = get_resource_path("container.tar.gz")
        with gzip.open(compressed_container_path) as f:
            while True:
                chunk = f.read(chunk_size)
                if len(chunk) > 0:
                    if p.stdin:
                        p.stdin.write(chunk)
                else:
                    break
        p.communicate()

        if not self.is_container_installed():
            log.error("Failed to install the container image")
            return False

        log.info("Container image installed")
        return True

    def is_container_installed(self) -> bool:
        """
        See if the podman container is installed. Linux only.
        """
        # Get the image id
        with open(get_resource_path("image-id.txt")) as f:
            expected_image_id = f.read().strip()

        # See if this image is already installed
        installed = False
        found_image_id = subprocess.check_output(
            [
                self.get_runtime(),
                "image",
                "list",
                "--format",
                "{{.ID}}",
                self.CONTAINER_NAME,
            ],
            text=True,
            startupinfo=get_subprocess_startupinfo(),
        )
        found_image_id = found_image_id.strip()

        if found_image_id == expected_image_id:
            installed = True
        elif found_image_id == "":
            pass
        else:
            log.info("Deleting old dangerzone container image")

            try:
                subprocess.check_output(
                    [self.get_runtime(), "rmi", "--force", found_image_id],
                    startupinfo=get_subprocess_startupinfo(),
                )
            except:
                log.warning("Couldn't delete old container image, so leaving it there")

        return installed

    def parse_progress(self, document: Document, line: str) -> Tuple[bool, str, int]:
        """
        Parses a line returned by the container.
        """
        try:
            status = json.loads(line)
        except:
            error_message = f"Invalid JSON returned from container:\n\n\t {line}"
            log.error(error_message)
            return (True, error_message, -1)

        self.print_progress(
            document, status["error"], status["text"], status["percentage"]
        )
        return (status["error"], status["text"], status["percentage"])

    def exec(
        self,
        document: Document,
        args: List[str],
        stdout_callback: Optional[Callable] = None,
    ) -> int:
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
                    (error, text, percentage) = self.parse_progress(document, line)
                    if stdout_callback:
                        stdout_callback(error, text, percentage)

            p.communicate()
            return p.returncode

    def exec_container(
        self,
        document: Document,
        command: List[str],
        extra_args: List[str] = [],
        stdout_callback: Optional[Callable] = None,
    ) -> int:
        container_runtime = self.get_runtime()

        if self.get_runtime_name() == "podman":
            platform_args = []
            security_args = ["--security-opt", "no-new-privileges"]
            security_args += ["--userns", "keep-id"]
        else:
            platform_args = ["--platform", "linux/amd64"]
            security_args = ["--security-opt=no-new-privileges:true"]

        # drop all linux kernel capabilities
        security_args += ["--cap-drop", "all"]
        user_args = ["-u", "dangerzone"]

        prevent_leakage_args = ["--rm"]

        args = (
            ["run", "--network", "none"]
            + platform_args
            + user_args
            + security_args
            + prevent_leakage_args
            + extra_args
            + [self.CONTAINER_NAME]
            + command
        )

        args = [container_runtime] + args
        return self.exec(document, args, stdout_callback)

    def _convert(
        self,
        document: Document,
        ocr_lang: Optional[str],
        stdout_callback: Optional[Callable] = None,
    ) -> bool:
        success = False

        if ocr_lang:
            ocr = "1"
        else:
            ocr = "0"

        dz_tmp = os.path.join(appdirs.user_config_dir("dangerzone"), "tmp")
        os.makedirs(dz_tmp, exist_ok=True)

        tmpdir = tempfile.TemporaryDirectory(dir=dz_tmp)
        pixel_dir = os.path.join(tmpdir.name, "pixels")
        safe_dir = os.path.join(tmpdir.name, "safe")
        os.makedirs(pixel_dir, exist_ok=True)
        os.makedirs(safe_dir, exist_ok=True)

        # Convert document to pixels
        command = [
            "/usr/bin/python3",
            "/usr/local/bin/dangerzone.py",
            "document-to-pixels",
        ]
        extra_args = [
            "-v",
            f"{document.input_filename}:/tmp/input_file",
            "-v",
            f"{pixel_dir}:/dangerzone",
        ]
        ret = self.exec_container(document, command, extra_args, stdout_callback)
        if ret != 0:
            log.error("documents-to-pixels failed")
        else:
            # TODO: validate convert to pixels output

            # Convert pixels to safe PDF
            command = [
                "/usr/bin/python3",
                "/usr/local/bin/dangerzone.py",
                "pixels-to-pdf",
            ]
            extra_args = [
                "-v",
                f"{pixel_dir}:/dangerzone",
                "-v",
                f"{safe_dir}:/safezone",
                "-e",
                f"OCR={ocr}",
                "-e",
                f"OCR_LANGUAGE={ocr_lang}",
            ]
            ret = self.exec_container(document, command, extra_args, stdout_callback)
            if ret != 0:
                log.error("pixels-to-pdf failed")
            else:
                # Move the final file to the right place
                if os.path.exists(document.output_filename):
                    os.remove(document.output_filename)

                container_output_filename = os.path.join(
                    safe_dir, "safe-output-compressed.pdf"
                )
                shutil.move(container_output_filename, document.output_filename)

                # We did it
                success = True

        # Clean up
        tmpdir.cleanup()

        return success

    def get_max_parallel_conversions(self) -> int:

        # FIXME hardcoded 1 until timeouts are more limited and better handled
        # https://github.com/freedomofpress/dangerzone/issues/257
        return 1

        n_cpu = 1  # type: ignore [unreachable]
        if platform.system() == "Linux":
            # if on linux containers run natively
            cpu_count = os.cpu_count()
            if cpu_count is not None:
                n_cpu = cpu_count

        elif self.get_runtime_name() == "docker":
            # For Windows and MacOS containers run in VM
            # So we obtain the CPU count for the VM
            n_cpu_str = subprocess.check_output(
                [self.get_runtime(), "info", "--format", "{{.NCPU}}"],
                text=True,
                startupinfo=get_subprocess_startupinfo(),
            )
            n_cpu = int(n_cpu_str.strip())

        return 2 * n_cpu + 1
