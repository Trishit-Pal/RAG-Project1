import pytest

from core import uploads


def test_save_upload_strips_folders_from_the_name(tmp_path):
    # "../../evil.csv" must never be able to write outside the upload folder.
    saved = uploads.save_upload("../../evil.csv", b"a,b\n1,2\n", folder=tmp_path)

    assert saved.parent == tmp_path
    assert saved.name == "evil.csv"
    assert saved.read_bytes() == b"a,b\n1,2\n"


def test_save_upload_rejects_unsupported_types(tmp_path):
    with pytest.raises(ValueError, match="not supported"):
        uploads.save_upload("virus.exe", b"x", folder=tmp_path)


def test_save_upload_rejects_empty_files(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        uploads.save_upload("a.csv", b"", folder=tmp_path)


def test_list_saved_csvs_returns_only_csv_files_sorted(tmp_path):
    (tmp_path / "b.csv").write_text("x")
    (tmp_path / "a.csv").write_text("x")
    (tmp_path / "notes.txt").write_text("x")

    assert [p.name for p in uploads.list_saved_csvs(folder=tmp_path)] == ["a.csv", "b.csv"]


def test_list_saved_csvs_handles_a_missing_folder(tmp_path):
    assert uploads.list_saved_csvs(folder=tmp_path / "nope") == []


def test_save_upload_refuses_to_replace_a_different_file_with_the_same_name(tmp_path):
    uploads.save_upload("sales.csv", b"a\n1\n", folder=tmp_path)
    with pytest.raises(ValueError, match="already exists"):
        uploads.save_upload("sales.csv", b"a\n2\n", folder=tmp_path)
    assert (tmp_path / "sales.csv").read_bytes() == b"a\n1\n"  # the first file is untouched


def test_save_upload_accepts_the_identical_file_again(tmp_path):
    uploads.save_upload("sales.csv", b"a\n1\n", folder=tmp_path)
    assert uploads.save_upload("sales.csv", b"a\n1\n", folder=tmp_path).exists()


def test_remove_upload_deletes_the_file_and_ignores_missing_ones(tmp_path):
    path = uploads.save_upload("bad.csv", b"x", folder=tmp_path)
    uploads.remove_upload(path)
    uploads.remove_upload(path)  # second call: already gone, no error
    assert not path.exists()
