import pymupdf

from core.parse import parse_csv, parse_pdf


def test_parse_csv_reads_rows_and_columns(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("name,amount\nAlice,10\nBob,20\n", encoding="utf-8")

    df = parse_csv(csv_file)

    assert list(df.columns) == ["name", "amount"]
    assert len(df) == 2


def test_parse_pdf_returns_one_text_per_page(tmp_path):
    pdf_file = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from page one")
    doc.save(str(pdf_file))
    doc.close()

    pages = parse_pdf(pdf_file)

    assert len(pages) == 1
    assert "Hello from page one" in pages[0]

def test_parse_docx_returns_paragraphs_and_table_cells_as_one_page(tmp_path):
    import docx

    from core.parse import parse_docx

    path = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_paragraph("First paragraph")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "cell A"
    table.rows[0].cells[1].text = "cell B"
    document.save(str(path))

    pages = parse_docx(path)

    assert len(pages) == 1
    assert "First paragraph" in pages[0]
    assert "cell A | cell B" in pages[0]


def test_parse_txt_returns_the_whole_file_as_one_page(tmp_path):
    from core.parse import parse_txt

    path = tmp_path / "notes.txt"
    path.write_text("line one\nline two", encoding="utf-8")

    assert parse_txt(path) == ["line one\nline two"]


def test_parse_txt_does_not_crash_on_bad_bytes(tmp_path):
    from core.parse import parse_txt

    path = tmp_path / "bad.txt"
    path.write_bytes(b"ok \xff\xfe text")

    assert "ok" in parse_txt(path)[0]


def test_parse_txt_reads_utf16_files_from_windows_notepad(tmp_path):
    from core.parse import parse_txt

    path = tmp_path / "unicode.txt"
    path.write_text("café notes", encoding="utf-16")  # writes a byte-order mark

    text = parse_txt(path)[0]
    assert text == "café notes"
    assert "\x00" not in text  # the database refuses NUL characters
