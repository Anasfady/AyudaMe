from src.ingestion.tables import _forward_fill, _table_to_markdown


def test_forward_fill_carries_down_merged_column():
    rows = [
        ["Sección", "Tramo", "Base"],
        ["Reducida", "1", "653,59"],
        [None, "2", "718,95"],
        [None, "3", "849,67"],
        ["General", "1", "950,98"],
    ]
    filled = _forward_fill(rows)
    assert filled[2] == ["Reducida", "2", "718,95"]
    assert filled[3] == ["Reducida", "3", "849,67"]
    assert filled[4] == ["General", "1", "950,98"]


def test_forward_fill_leaves_empty_string_alone():
    # A genuinely blank ("") cell is NOT the same as a merged (None) cell and
    # must not be overwritten — see the docstring in tables.py for why.
    rows = [["A", "B"], ["", "x"], ["y", "z"]]
    filled = _forward_fill(rows)
    assert filled[1] == ["", "x"]


def test_table_to_markdown_renders_header_and_rows():
    rows = [["Tramo", "Base"], ["1", "653,59"], ["2", "718,95"]]
    markdown = _table_to_markdown(rows)
    lines = markdown.splitlines()
    assert lines[0] == "| Tramo | Base |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 653,59 |"


def test_table_to_markdown_cleans_embedded_newlines_in_header():
    rows = [["Base mínima\n–\nEuros/mes", "Base máxima"], ["653,59", "718,94"]]
    markdown = _table_to_markdown(rows)
    assert "\n" not in markdown.splitlines()[0]
    assert "Base mínima – Euros/mes" in markdown.splitlines()[0]


def test_table_to_markdown_empty_input():
    assert _table_to_markdown([]) == ""
