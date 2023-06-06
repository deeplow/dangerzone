import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

# FIXME: We have two cases here, to accommodate for the case of dz.ConvertDev, which
# accepts a Python zipfile that cannot be used as a Python package. Merge them into one,
# if possible.
if __name__ == "__main__":
    from .doc_to_pixels import DocumentToPixels
else:
    from doc_to_pixels import DocumentToPixels


def read_bytes() -> bytes:
    """Read bytes from the stdin."""
    data = sys.stdin.buffer.read()
    if data is None:
        raise EOFError
    return data


def write_bytes(data: bytes, file=sys.stdout):
    file.buffer.write(data)


def write_text(text: str, file=sys.stdout):
    write_bytes(text.encode(), file=file)


def write_int(num: int, file=sys.stdout):
    write_bytes(num.to_bytes(2, signed=False), file=file)


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
        untrusted_data = read_bytes()
    except EOFError:
        sys.exit(1)

    with open("/tmp/input_file", "wb") as f:
        f.write(untrusted_data)

    ret_code = asyncio.run(main())
    num_pages = len(list(out_dir.glob("*.rgb")))
    write_int(num_pages)
    for num_page in range(1, num_pages + 1):
        page_base = out_dir / f"page-{num_page}"
        with open(f"{page_base}.width", "r") as width_file:
            width = int(width_file.read())
        with open(f"{page_base}.height", "r") as height_file:
            height = int(height_file.read())
        write_int(width)
        write_int(height)
        with open(f"{page_base}.rgb", "rb") as rgb_file:
            rgb_data = rgb_file.read()
            write_bytes(rgb_data)

    return ret_code


if __name__ == "__main__":
    sys.exit(main2())
