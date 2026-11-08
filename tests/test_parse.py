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