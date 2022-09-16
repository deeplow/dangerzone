import os
import tempfile

import pytest

from dangerzone.document import DocumentFilenameException, DocumentHolder

from . import sample_doc, unreadable_pdf, unwriteable_pdf


def test_input_sample_init(sample_doc):
    DocumentHolder(sample_doc)


def test_input_sample_after(sample_doc):
    d = DocumentHolder()
    d.input_filename = sample_doc


def test_input_file_none():
    """
    Attempts to read a document's filename when no doc has been set
    """
    d = DocumentHolder()
    with pytest.raises(DocumentFilenameException):
        d.input_filename


def test_input_file_non_existing():
    with pytest.raises(DocumentFilenameException):
        DocumentHolder("fake-dir/non-existing-file.pdf")


def test_input_file_unreadable(unreadable_pdf):
    with pytest.raises(DocumentFilenameException):
        DocumentHolder(unreadable_pdf)


def test_output_file_unwriteable(unwriteable_pdf):
    d = DocumentHolder()
    with pytest.raises(DocumentFilenameException):
        d.output_filename = unwriteable_pdf


def test_output(tmp_path):
    pdf_file = str(tmp_path / "document.pdf")
    d = DocumentHolder()
    d.output_filename = pdf_file


def test_output_file_none():
    """
    Attempts to read a document's filename when no doc has been set
    """
    d = DocumentHolder()
    with pytest.raises(DocumentFilenameException):
        d.output_filename(self, filename)


def test_output_file_not_pdf(tmp_path):
    docx_file = str(tmp_path / "document.docx")
    d = DocumentHolder()

    with pytest.raises(DocumentFilenameException):
        d.output_filename = docx_file

    assert not os.path.exists(docx_file)
