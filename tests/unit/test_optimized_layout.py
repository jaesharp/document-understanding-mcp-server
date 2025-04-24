from src.document_understanding.extractor import PDFExtractor


class TestOptimizedLayoutExtraction:
    """Tests for the optimized layout extraction functionality using real PDFs."""

    def test_extract_layout_with_options_params(self, mocker, test_pdfs_setup):
        """Test that extract_layout has new options parameters."""
        extractor = PDFExtractor()
        spy = mocker.spy(extractor, "extract_layout")
        pdf_path = str(test_pdfs_setup["text"])
        extractor.extract_layout(pdf_path, "1")
        assert spy.call_args.args[0] == pdf_path
        assert spy.call_args.args[1] == "1"
        assert spy.call_args.kwargs.get("include_images", True) is True
        assert spy.call_args.kwargs.get("include_drawings", True) is True

    def test_extract_layout_without_images(self, test_pdfs_setup):
        """Test that extract_layout skips image processing when include_images=False."""
        pdf_path = str(test_pdfs_setup["drawings_only"])
        extractor = PDFExtractor()

        result = extractor.extract_layout(
            pdf_path, "1", include_images=False, include_drawings=True
        )

        assert len(result) == 1
        page_layout = result[0]
        assert "text_blocks" in page_layout
        assert "images" not in page_layout
        assert "drawings" in page_layout
        assert len(page_layout["drawings"]) > 0

    def test_extract_layout_without_drawings(self, test_pdfs_setup):
        """Test that extract_layout skips drawing processing when include_drawings=False."""
        pdf_path = str(test_pdfs_setup["image"])
        extractor = PDFExtractor()

        result = extractor.extract_layout(
            pdf_path, "1", include_images=True, include_drawings=False
        )

        assert len(result) == 1
        page_layout = result[0]
        assert "text_blocks" in page_layout
        assert "drawings" not in page_layout
        assert "images" in page_layout
        assert len(page_layout["images"]) > 0

    def test_extract_layout_without_images_or_drawings(self, test_pdfs_setup):
        """Test that extract_layout skips both image and drawing processing."""
        pdf_path = str(test_pdfs_setup["text"])
        extractor = PDFExtractor()

        result = extractor.extract_layout(
            pdf_path, "1", include_images=False, include_drawings=False
        )

        assert len(result) == 1
        page_layout = result[0]
        assert "text_blocks" in page_layout
        assert "drawings" not in page_layout
        assert "images" not in page_layout

    def test_extract_layout_returns_correct_structure_with_options(
        self, test_pdfs_setup
    ):
        """Test that extract_layout returns the correct structure based on options."""
        pdf_path = str(test_pdfs_setup["all_elements"])
        extractor = PDFExtractor()

        result_all = extractor.extract_layout(
            pdf_path, "1", include_images=True, include_drawings=True
        )
        assert len(result_all) == 1
        page_all = result_all[0]
        assert "text_blocks" in page_all
        assert "drawings" in page_all
        assert "images" in page_all
        assert len(page_all["images"]) > 0
        assert len(page_all["drawings"]) > 0

        result_img = extractor.extract_layout(
            pdf_path, "1", include_images=True, include_drawings=False
        )
        assert len(result_img) == 1
        page_img = result_img[0]
        assert "text_blocks" in page_img
        assert "images" in page_img
        assert "drawings" not in page_img
        assert len(page_img["images"]) > 0

        result_draw = extractor.extract_layout(
            pdf_path, "1", include_images=False, include_drawings=True
        )
        assert len(result_draw) == 1
        page_draw = result_draw[0]
        assert "text_blocks" in page_draw
        assert "images" not in page_draw
        assert "drawings" in page_draw
        assert len(page_draw["drawings"]) > 0

        result_none = extractor.extract_layout(
            pdf_path, "1", include_images=False, include_drawings=False
        )
        assert len(result_none) == 1
        page_none = result_none[0]
        assert "text_blocks" in page_none
        assert "images" not in page_none
        assert "drawings" not in page_none

        result_default = extractor.extract_layout(pdf_path, "1")
        assert len(result_default) == 1
        page_default = result_default[0]
        assert "text_blocks" in page_default
        assert "images" not in page_default
        assert "drawings" not in page_default
