import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from dangerzone import DangerzoneConverter


def recv_b():
    """Qrexec wrapper for receiving binary data from the client

    Borrowed from https://github.com/QubesOS/qubes-app-linux-pdf-converter/blob/main/qubespdfconverter/server.py#L82
    """
    untrusted_data = sys.stdin.buffer.read()
    if not untrusted_data:
        raise EOFError
    return untrusted_data


def send_b(data):
    """Qrexec wrapper for sending binary data to the client

    Borrowed from https://github.com/QubesOS/qubes-app-linux-pdf-converter/blob/main/qubespdfconverter/server.py#L82

    """
    if isinstance(data, (str, int)):
        data = str(data).encode()

    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def send(data):
    """Qrexec wrapper for sending text data to the client

    borrowed from https://github.com/QubesOS/qubes-app-linux-pdf-converter/blob/main/qubespdfconverter/server.py#L77
    """
    print(data, flush=True)


async def main() -> int:
    converter = DangerzoneConverter()

    try:
        await converter.document_to_pixels()
    except (RuntimeError, TimeoutError, ValueError) as e:
        # converter.update_progress(str(e), error=True)
        return 1
    else:
        return 0  # Success!


if __name__ == "__main__":
    out_dir = Path("/tmp/dangerzone")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()

    try:
        untrusted_data = recv_b()
    except EOFError:
        sys.exit(1)

    with open("/tmp/input_file", "wb") as f:
        f.write(untrusted_data)

    ret_code = asyncio.run(main())
    num_pages = len(list(out_dir.glob("*.rgb")))

    send(num_pages)
    for num_page in range(1, num_pages + 1):
        page_base = out_dir / f"page-{num_page}"
        with open(f"{page_base}.width", "r") as width_file:
            width = width_file.read()
        with open(f"{page_base}.height", "r") as height_file:
            height = height_file.read()
        send(f"{width} {height}")

        with open(f"{page_base}.rgb", "rb") as rgb_file:
            rgb_data = rgb_file.read()
            send_b(rgb_data)

    sys.exit(ret_code)
