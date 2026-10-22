"""Document loader tests."""

from pathlib import Path

import pytest

from src.common.errors import UnreadableDocumentError, UnsupportedFileTypeError
from src.ingestion.loaders import load_document


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_load_txt_returns_single_page(tmp_path):
    path = _write(tmp_path, "notes.txt", "Hola, esto es texto plano.")

    pages = load_document(path)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert pages[0].text == "Hola, esto es texto plano."


def test_load_markdown_returns_single_page(tmp_path):
    path = _write(tmp_path, "readme.md", "# Título\n\nContenido en markdown.")

    pages = load_document(path)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert "Contenido en markdown" in pages[0].text


def test_unsupported_extension_raises(tmp_path):
    path = _write(tmp_path, "data.docx", "Este contenido no debería cargarse.")

    with pytest.raises(UnsupportedFileTypeError):
        load_document(path)


def test_missing_file_raises(tmp_path):
    path = tmp_path / "missing.txt"

    with pytest.raises((FileNotFoundError, UnreadableDocumentError)):
        load_document(path)


def test_empty_text_file_returns_empty_or_unreadable_result(tmp_path):
    path = _write(tmp_path, "empty.txt", "")

    try:
        pages = load_document(path)
    except UnreadableDocumentError:
        return

    assert len(pages) == 1
    assert pages[0].page == 1
    assert pages[0].text == ""


def test_real_pdf_loads_from_corpus():
    path = Path("data/raw/RDL_13_2022_RETA.pdf")

    if not path.exists():
        pytest.skip("real corpus PDF not present in this environment")

    pages = load_document(path)

    assert len(pages) > 50
    assert all(page.page >= 1 for page in pages)
    assert all(page.text is not None for page in pages)

    corpus_text = "\n".join(page.text.lower() for page in pages)
    assert "autónomos" in corpus_text or "autonomos" in corpus_text


def test_blank_scanned_pdf_is_reported_as_unreadable(tmp_path):
    pytest.importorskip("fitz")
    import fitz

    path = tmp_path / "blank.pdf"

    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(UnreadableDocumentError):
        load_document(path)
