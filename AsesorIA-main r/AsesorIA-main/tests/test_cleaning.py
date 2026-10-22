"""Tests for text cleaning."""

from src.ingestion.cleaning import clean_text, remove_repeated_lines
from src.ingestion.loaders import LoadedPage


def test_clean_text_dehyphenates_and_collapses_blank_lines():
    raw = (
        "Este texto tiene una pala-\n"
        "bra cortada.\n"
        "Y otra linea.\n"
        "\n"
        "\n"
        "\n"
        "Nuevo parrafo."
    )

    assert clean_text(raw) == (
        "Este texto tiene una palabra cortada.\n"
        "Y otra linea.\n\n"
        "Nuevo parrafo."
    )


def test_remove_repeated_lines_removes_exact_repeated_header():
    pages = [
        LoadedPage(
            text=f"CABECERA OFICIAL\nContenido unico {i}\nfin",
            page=i + 1,
        )
        for i in range(4)
    ]

    cleaned = remove_repeated_lines(pages)

    assert [p.text for p in cleaned] == [
        f"Contenido unico {i}" for i in range(4)
    ]


def test_remove_repeated_lines_strips_rotating_date_prefix():
    pages = [
        LoadedPage(
            text=f"28/09/2026 - Manual practico\nContenido unico {i}\nfin",
            page=i + 1,
        )
        for i in range(5)
    ]

    cleaned = remove_repeated_lines(pages)

    assert [p.text for p in cleaned] == [
        f"Contenido unico {i}" for i in range(5)
    ]


def test_remove_repeated_lines_strips_isolated_pagina_n_marker():
    pages = [
        LoadedPage(
            text=f"Cuerpo real de la pagina {i}\nPágina {i + 1}",
            page=i + 1,
        )
        for i in range(5)
    ]

    cleaned = remove_repeated_lines(pages)

    assert [p.text for p in cleaned] == [
        f"Cuerpo real de la pagina {i}" for i in range(5)
    ]


def test_remove_repeated_lines_does_not_conflate_content_that_only_differs_by_digit():
    pages = [
        LoadedPage(
            text=(
                f"28/09/2026 - Manual practico\n"
                f"Contenido unico {i}\n"
                "fin"
            ),
            page=i + 1,
        )
        for i in range(5)
    ]

    cleaned = remove_repeated_lines(pages)

    for i, page in enumerate(cleaned):
        assert f"Contenido unico {i}" in page.text


def test_remove_repeated_lines_noop_under_three_pages():
    pages = [
        LoadedPage(text="CABECERA\ncontenido", page=1),
        LoadedPage(text="CABECERA\nmas", page=2),
    ]

    assert remove_repeated_lines(pages) == pages
