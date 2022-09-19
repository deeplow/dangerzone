import os
import sys
from pathlib import Path

import pytest

sys.dangerzone_dev = True

from dangerzone.document import SAFE_EXTENSION

SAMPLE_DIRECTORY = "test_docs"
BASIC_SAMPLE = "sample.pdf"
test_docs_dir = Path(__file__).parent.joinpath(SAMPLE_DIRECTORY)
test_docs = [
    p
    for p in test_docs_dir.rglob("*")
    if p.is_file() and not p.name.endswith(SAFE_EXTENSION)
]

# Pytest parameter decorators
for_each_doc = pytest.mark.parametrize("doc", test_docs)


class TestBase:
    sample_doc = str(test_docs_dir.joinpath(BASIC_SAMPLE))


@pytest.fixture
def sample_doc():
    return str(test_docs_dir.joinpath(BASIC_SAMPLE))


@pytest.fixture
def unwriteable_pdf(tmp_path):
    file_path = str(tmp_path / "document.pdf")
    with open(file_path, "w+"):
        # create file
        pass
    os.chmod(file_path, mode=600)
    return file_path


@pytest.fixture
def unreadable_pdf(tmp_path):
    file_path = str(tmp_path / "document.pdf")
    with open(file_path, "w+"):
        # create file
        pass
    os.chmod(file_path, mode=0)
    return file_path
