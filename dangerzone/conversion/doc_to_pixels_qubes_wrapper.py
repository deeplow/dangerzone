import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

# FIXME: We have two cases here, to accommodate for the case of dz.ConvertDev, which
# accepts a Python zipfile that cannot be used as a Python package. Merge them into one,
# if possible.
if __name__ == "__main__":
    from .doc_to_pixels import DocumentToPixels
else:
    from doc_to_pixels import DocumentToPixels


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
    converter = DocumentToPixels()

    try:
        await converter.convert()
    except (RuntimeError, TimeoutError, ValueError) as e:
        # converter.update_progress(str(e), error=True)
        return 1
    else:
        return 0  # Success!


# FIXME: Convert the following to asyncio code, so that there's no need to have a
# separate function.
def main2() -> int:
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
    send_b(num_pages.to_bytes(2, byteorder="big", signed=False))
    for num_page in range(1, num_pages + 1):
        page_base = out_dir / f"page-{num_page}"
        with open(f"{page_base}.width", "r") as width_file:
            width = int(width_file.read())
        with open(f"{page_base}.height", "r") as height_file:
            height = int(height_file.read())
        send_b(width.to_bytes(2, byteorder="big", signed=False))
        send_b(height.to_bytes(2, byteorder="big", signed=False))
        with open(f"{page_base}.rgb", "rb") as rgb_file:
            rgb_data = rgb_file.read()
            send_b(rgb_data)

    return ret_code


if __name__ == "__main__":
    sys.exit(main2())
