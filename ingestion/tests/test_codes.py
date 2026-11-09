from ingestion.codes import code_from_parts, normalize_codes


def test_normalize_codes_rewrites_variants_to_who_notation() -> None:
    text = "Combine Lu 07, LI-04, St20, TB 5, Pe 06, MP 6, LV3 and BL 30."
    assert normalize_codes(text) == "Combine LU7, LI4, ST20, TE5, PC6, SP6, LR3 and BL30."


def test_normalize_codes_leaves_other_text_alone() -> None:
    assert normalize_codes("Press for 30 seconds, step 2.") == "Press for 30 seconds, step 2."
    assert normalize_codes("LI40X and XLI4") == "LI40X and XLI4"


def test_code_from_parts() -> None:
    assert code_from_parts("tb", "05") == "TE5"
    assert code_from_parts("lv", 3) == "LR3"
    assert code_from_parts("ex", 1) is None
