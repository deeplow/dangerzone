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


def _read_bytes() -> bytes:
    """Read bytes from the stdin."""
    data = sys.stdin.buffer.read()
    if data is None:
        raise EOFError
    return data


def _write_bytes(data: bytes, file=sys.stdout):
    file.buffer.write(data)


def _write_text(text: str, file=sys.stdout):
    _write_bytes(text.encode(), file=file)


def _write_int(num: int, file=sys.stdout):
    _write_bytes(num.to_bytes(2, signed=False), file=file)

# ==== ASYNC METHODS ====
# We run sync methods in async wrappers, because pure async methods are more difficult:
# https://stackoverflow.com/a/52702646
#
# In practice, because they are I/O bound and we don't have many running concurrently,
# they shouldn't cause a problem.

async def read_bytes() -> bytes:
    return await asyncio.to_thread(_read_bytes)


async def write_bytes(data: bytes, file=sys.stdout):
    return await asyncio.to_thread(_write_bytes, data, file=file)


async def write_text(text: str, file=sys.stdout):
    return await asyncio.to_thread(_write_text, text, file=file)


async def write_int(num: int, file=sys.stdout):
    return await asyncio.to_thread(_write_int, num, file=file)


# FIXME: Convert the following to asyncio code, so that there's no need to have a
# separate function.
async def main() -> int:
    out_dir = Path("/tmp/dangerzone")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()

    try:
        untrusted_data = await read_bytes()
    except EOFError:
        sys.exit(1)

    with open("/tmp/input_file", "wb") as f:
        f.write(untrusted_data)

    converter = DocumentToPixels()

    try:
        await converter.convert()
    except Exception as e:
        await write_text(f"Conversion failed with: {e}", file=sys.stderr)
        return 1

    num_pages = len(list(out_dir.glob("*.rgb")))
    await write_int(num_pages)
    for num_page in range(1, num_pages + 1):
        page_base = out_dir / f"page-{num_page}"
        with open(f"{page_base}.width", "r") as width_file:
            width = int(width_file.read())
        with open(f"{page_base}.height", "r") as height_file:
            height = int(height_file.read())
        await write_int(width)
        await write_int(height)
        with open(f"{page_base}.rgb", "rb") as rgb_file:
            rgb_data = rgb_file.read()
            await write_bytes(rgb_data)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
