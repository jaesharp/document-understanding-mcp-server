from src.document_understanding.extractor import PDFExtractor
import pytest

# Use a single real instance for most tests
extractor_real = PDFExtractor()
extractor_for_parsing = extractor_real


# --- parse_pages tests (using extractor_for_parsing) ---
def test_parse_pages_none():
    assert extractor_for_parsing.parse_pages(None, 10) == list(range(10))


def test_parse_pages_empty_string():
    assert extractor_for_parsing.parse_pages("", 10) == list(range(10))


def test_parse_pages_whitespace_string():
    assert extractor_for_parsing.parse_pages("  ", 10) == list(range(10))


def test_parse_pages_single_valid():
    assert extractor_for_parsing.parse_pages("1", 10) == [0]
    assert extractor_for_parsing.parse_pages(" 5 ", 10) == [4]
    assert extractor_for_parsing.parse_pages("10", 10) == [9]


def test_parse_pages_multiple_valid():
    assert extractor_for_parsing.parse_pages("1, 5, 10", 10) == [0, 4, 9]
    assert extractor_for_parsing.parse_pages(" 10 ,1, 5 ", 10) == [0, 4, 9]


def test_parse_pages_negative_indices():
    assert extractor_for_parsing.parse_pages("-1", 10) == [9]
    assert extractor_for_parsing.parse_pages("-10", 10) == [0]
    assert extractor_for_parsing.parse_pages("1, -1", 10) == [0, 9]
    assert extractor_for_parsing.parse_pages("-2, -1", 10) == [8, 9]


def test_parse_pages_range_valid():
    assert extractor_for_parsing.parse_pages("1-3", 10) == [0, 1, 2]
    assert extractor_for_parsing.parse_pages(" 8 - 10 ", 10) == [7, 8, 9]
    assert extractor_for_parsing.parse_pages("1-1", 10) == [0]


def test_parse_pages_range_negative():
    assert extractor_for_parsing.parse_pages("1--1", 10) == list(range(10))
    assert extractor_for_parsing.parse_pages("-3--1", 10) == [7, 8, 9]


def test_parse_pages_mixed():
    assert extractor_for_parsing.parse_pages("1, 3-5, 9, -1", 10) == [0, 2, 3, 4, 8, 9]
    assert extractor_for_parsing.parse_pages(" 6-8, 2 ", 10) == [1, 5, 6, 7]


def test_parse_pages_duplicates_and_overlap():
    assert extractor_for_parsing.parse_pages("1, 1, 2-3, 3-4", 10) == [0, 1, 2, 3]


def test_parse_pages_invalid_range_order():
    # Covers line 171: if start > end:
    assert extractor_for_parsing.parse_pages("5-3", 10) == [2, 3, 4]


def test_parse_pages_invalid_range_multiple_hyphens():
    # Covers lines 195-196: except ValueError in range split
    with pytest.raises(ValueError, match="Invalid page number format: '1-2-3'"):
        extractor_real.parse_pages("1-2-3", 10)


def test_parse_pages_regex_exception(mocker):
    """Test that generic exceptions during regex matching are caught."""
    extractor = PDFExtractor()
    # Mock re.fullmatch to raise a generic exception
    mocker.patch("re.fullmatch", side_effect=Exception("Regex Unexpected Error"))
    with pytest.raises(
        ValueError,
        match=r"Unexpected error parsing page specification part: '1'.*Regex Unexpected Error",
    ):
        extractor.parse_pages("1,2", 10)  # Input doesn't matter as mock will fail first


def test_parse_pages_invalid_char():
    with pytest.raises(ValueError, match="Invalid page number format: 'abc'"):
        extractor_real.parse_pages("1, abc, 5", 10)


def test_parse_pages_invalid_range_format():
    with pytest.raises(ValueError, match="Invalid page number format: '1-'"):
        extractor_real.parse_pages("1-", 10)
    with pytest.raises(ValueError, match="Invalid page number format: '3-abc'"):
        extractor_real.parse_pages("3-abc", 10)


def test_parse_pages_out_of_bounds_single():
    with pytest.raises(
        ValueError, match=r"Page number '0' .* is outside the valid range"
    ):
        extractor_real.parse_pages("0", 10)
    with pytest.raises(
        ValueError, match=r"Page number '11' .* is outside the valid range"
    ):
        extractor_real.parse_pages("11", 10)
    with pytest.raises(
        ValueError, match=r"Page number '-11' .* is outside the valid range"
    ):
        extractor_real.parse_pages("-11", 10)


def test_parse_pages_out_of_bounds_range():
    with pytest.raises(
        ValueError, match=r"End page '11' .* is outside the valid range"
    ):
        extractor_real.parse_pages("9-11", 10)
    with pytest.raises(
        ValueError, match=r"Start page '0' .* is outside the valid range"
    ):
        extractor_real.parse_pages("0-2", 10)
    with pytest.raises(
        ValueError, match=r"Start page '-11' .* is outside the valid range"
    ):
        extractor_real.parse_pages("-11--9", 10)
