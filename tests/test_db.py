from core.db import rows_to_dicts, to_vector_text


def test_to_vector_text_formats_a_list_of_numbers():
    assert to_vector_text([0.5, 1]) == "[0.5,1.0]"


def test_rows_to_dicts_names_each_value():
    assert rows_to_dicts(["a", "b"], [(1, 2), (3, 4)]) == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
