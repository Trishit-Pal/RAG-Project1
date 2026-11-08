from core.vectors import to_vector_literal


def test_to_vector_literal_formats_list():
    assert to_vector_literal([0.5, 1.0]) == "[0.5,1.0]"