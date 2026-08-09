import os
import tempfile

import pytest
from docx import Document

from backend.services.parser import extract_text


def test_extract_txt():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello world")
        path = f.name
    try:
        assert extract_text(path) == "hello world"
    finally:
        os.remove(path)


def test_extract_docx():
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    try:
        doc = Document()
        doc.add_paragraph("Hello from docx")
        doc.save(path)
        text = extract_text(path)
        assert "Hello from docx" in text
    finally:
        os.remove(path)


def test_extract_unsupported_format():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        path = f.name
    try:
        with pytest.raises(ValueError):
            extract_text(path)
    finally:
        os.remove(path)
