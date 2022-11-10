import gzip
import json
import logging
import os
import pipes
import platform
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from typing import Callable, Iterator, List, Optional

import appdirs

from .util import get_resource_path, get_subprocess_startupinfo

container_name = "dangerzone.rocks/dangerzone"

# Define startupinfo for subprocesses
if platform.system() == "Windows":
    startupinfo = subprocess.STARTUPINFO()  # type: ignore [attr-defined]
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore [attr-defined]
else:
    startupinfo = None

log = logging.getLogger(__name__)

# Name of the dangerzone container
container_name = "dangerzone.rocks/dangerzone"


class NoContainerTechException(Exception):
    def __init__(self, container_tech: str) -> None:
        super().__init__(f"{container_tech} is not installed")


def get_runtime_name() -> str:
    if platform.system() == "Linux":
        runtime_name = "podman"
    else:
        # Windows, Darwin, and unknown use docker for now, dangerzone-vm eventually
        runtime_name = "docker"
    return runtime_name


def get_runtime() -> str:
    container_tech = get_runtime_name()
    runtime = shutil.which(container_tech)
    if runtime is None:
        raise NoContainerTechException(container_tech)
    return runtime


def podman_get_subids():
    info = subprocess.run(
        ["podman", "info", "-f", "json"], check=True, stdout=subprocess.PIPE
    )
    info_dict = json.loads(info.stdout)
    for id_type in ["uid", "gid"]:
        mapping = info_dict["host"]["idMappings"][f"{id_type}map"]
        count = 0
        for m in mapping[1:]:
            count += m["size"]
        yield count


def install() -> bool:
    """
    Make sure the podman container is installed. Linux only.
    """
    if is_container_installed():
        return True

    # Load the container into podman
    log.info("Installing Dangerzone container image...")

    p = subprocess.Popen(
        [get_runtime(), "load"],
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

    if not is_container_installed():
        log.error("Failed to install the container image")
        return False

    log.info("Container image installed")
    return True


def is_container_installed() -> bool:
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
            get_runtime(),
            "image",
            "list",
            "--format",
            "{{.ID}}",
            container_name,
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
                [get_runtime(), "rmi", "--force", found_image_id],
                startupinfo=get_subprocess_startupinfo(),
            )
        except:
            log.warning("Couldn't delete old container image, so leaving it there")

    return installed


def exec(args: List[str], stdout_callback: Callable[[str], None] = None) -> int:
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
        if stdout_callback and p.stdout is not None:
            for line in p.stdout:
                stdout_callback(line)

        p.communicate()
        return p.returncode


def exec_container(
    command: List[str],
    extra_args: List[str] = [],
    stdout_callback: Callable[[str], None] = None,
) -> int:
    container_runtime = get_runtime()

    if get_runtime_name() == "podman":
        platform_args = []
        security_args = ["--security-opt", "no-new-privileges"]
        num_subuids, num_subgids = podman_get_subids()
        security_args += ["--uidmap", f"0:1:{num_subuids}"]
        security_args += ["--gidmap", f"0:1:{num_subgids}"]
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
        + [container_name]
        + command
    )

    args = [container_runtime] + args
    return exec(args, stdout_callback)


def convert(
    input_filename: str,
    output_filename: str,
    ocr_lang: Optional[str],
    stdout_callback: Callable[[str], None],
) -> bool:
    dz_tmp = os.path.join(appdirs.user_config_dir("dangerzone"), "tmp")
    os.makedirs(dz_tmp, exist_ok=True)
    tmpdir = tempfile.TemporaryDirectory(dir=dz_tmp)

    success = False

    if ocr_lang:
        ocr = "1"
    else:
        ocr = "0"

    tmp_input_file = os.path.join(tmpdir.name, "input_file")
    pixel_dir = os.path.join(tmpdir.name, "pixels")
    safe_dir = os.path.join(tmpdir.name, "safe")
    shutil.copy(input_filename, tmp_input_file)
    os.makedirs(pixel_dir, exist_ok=True)
    os.makedirs(safe_dir, exist_ok=True)

    with namespaced_tmpdir(tmpdir):
        # Convert document to pixels
        command = [
            "/usr/bin/python3",
            "/usr/local/bin/dangerzone.py",
            "document-to-pixels",
        ]
        extra_args = [
            "-v",
            f"{tmp_input_file}:/tmp/input_file",
            "-v",
            f"{pixel_dir}:/dangerzone",
        ]
        ret = exec_container(command, extra_args, stdout_callback)
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
            ret = exec_container(command, extra_args, stdout_callback)
            if ret != 0:
                log.error("pixels-to-pdf failed")
            else:
                # Move the final file to the right place
                if os.path.exists(output_filename):
                    os.remove(output_filename)

                # We did it
                success = True

    if success:
        container_output_filename = os.path.join(safe_dir, "safe-output-compressed.pdf")
        shutil.move(container_output_filename, output_filename)

    # Clean up
    tmpdir.cleanup()

    return success


@contextmanager
def namespaced_tmpdir(tmpdir: tempfile.TemporaryDirectory) -> Iterator:
    try:
        if get_runtime_name() == "podman":
            unshare_cmd = ["podman", "unshare", "chown", "-R", "1001:1001", tmpdir.name]
            log.debug("> " + " ".join(unshare_cmd))
            subprocess.run(unshare_cmd, check=True)
        yield
    finally:
        if get_runtime_name() == "podman":
            unshare_cmd = ["podman", "unshare", "chown", "-R", "0:0", tmpdir.name]
            log.debug("> " + " ".join(unshare_cmd))
            subprocess.run(unshare_cmd, check=True)


# From global_common:

# def validate_convert_to_pixel_output(self, common, output):
#     """
#     Take the output from the convert to pixels tasks and validate it. Returns
#     a tuple like: (success (boolean), error_message (str))
#     """
#     max_image_width = 10000
#     max_image_height = 10000

#     # Did we hit an error?
#     for line in output.split("\n"):
#         if (
#             "failed:" in line
#             or "The document format is not supported" in line
#             or "Error" in line
#         ):
#             return False, output

#     # How many pages was that?
#     num_pages = None
#     for line in output.split("\n"):
#         if line.startswith("Document has "):
#             num_pages = line.split(" ")[2]
#             break
#     if not num_pages or not num_pages.isdigit() or int(num_pages) <= 0:
#         return False, "Invalid number of pages returned"
#     num_pages = int(num_pages)

#     # Make sure we have the files we expect
#     expected_filenames = []
#     for i in range(1, num_pages + 1):
#         expected_filenames += [
#             f"page-{i}.rgb",
#             f"page-{i}.width",
#             f"page-{i}.height",
#         ]
#     expected_filenames.sort()
#     actual_filenames = os.listdir(common.pixel_dir.name)
#     actual_filenames.sort()

#     if expected_filenames != actual_filenames:
#         return (
#             False,
#             f"We expected these files:\n{expected_filenames}\n\nBut we got these files:\n{actual_filenames}",
#         )

#     # Make sure the files are the correct sizes
#     for i in range(1, num_pages + 1):
#         with open(f"{common.pixel_dir.name}/page-{i}.width") as f:
#             w_str = f.read().strip()
#         with open(f"{common.pixel_dir.name}/page-{i}.height") as f:
#             h_str = f.read().strip()
#         w = int(w_str)
#         h = int(h_str)
#         if (
#             not w_str.isdigit()
#             or not h_str.isdigit()
#             or w <= 0
#             or w > max_image_width
#             or h <= 0
#             or h > max_image_height
#         ):
#             return False, f"Page {i} has invalid geometry"

#         # Make sure the RGB file is the correct size
#         if os.path.getsize(f"{common.pixel_dir.name}/page-{i}.rgb") != w * h * 3:
#             return False, f"Page {i} has an invalid RGB file size"

#     return True, True
