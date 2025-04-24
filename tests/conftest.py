import pytest
from PIL import Image  # To check/create sample image

# Import PDF generation functions from the consolidated module
from tests.pdf_generators import (
    create_text_pdf,
    create_image_pdf,
    create_drawing_pdf,
    create_all_elements_pdf,
    create_empty_pdf,
    create_table_pdf,
    create_outline_pdf,
    create_encrypted_pdf,
)

# PDF generation functions are now imported from pdf_generators.py

# --- Updated Fixture ---


@pytest.fixture(scope="session")
def test_pdfs_setup(tmp_path_factory):
    """Generates or copies test PDF files once per session in a temporary directory."""
    base_temp_dir = tmp_path_factory.mktemp("pdf_test_files_session")
    paths_dict = {}

    # --- Dynamic Generation ---

    # Generate sample image dynamically within the temp directory
    sample_image_path = base_temp_dir / "runtime_sample_image.png"
    try:
        img = Image.new("RGB", (30, 20), color="purple")  # Create image in memory
        img.save(sample_image_path, "PNG")  # Save to temp dir
    except Exception as e:
        pytest.fail(f"Failed to create runtime sample image: {e}")

    # (Rest of the dynamic generation uses the generated sample_image_path)
    paths_dict["text"] = base_temp_dir / "text_doc.pdf"
    create_text_pdf(paths_dict["text"])

    paths_dict["image"] = base_temp_dir / "image_doc.pdf"
    create_image_pdf(paths_dict["image"], sample_image_path)

    paths_dict["drawings_only"] = base_temp_dir / "drawings_only_doc.pdf"
    create_drawing_pdf(paths_dict["drawings_only"])

    paths_dict["all_elements"] = base_temp_dir / "all_elements_doc.pdf"
    create_all_elements_pdf(paths_dict["all_elements"], sample_image_path)

    paths_dict["encrypted"] = base_temp_dir / "encrypted_doc.pdf"
    create_encrypted_pdf(paths_dict["encrypted"], "testpassword")

    # Generate the previously static files dynamically
    paths_dict["empty"] = base_temp_dir / "empty_doc.pdf"
    create_empty_pdf(paths_dict["empty"])

    paths_dict["table"] = base_temp_dir / "table_doc.pdf"
    create_table_pdf(paths_dict["table"])

    paths_dict["outline"] = base_temp_dir / "outline_doc.pdf"
    create_outline_pdf(paths_dict["outline"])

    # Add a path for a non-existent file
    paths_dict["non_existent"] = base_temp_dir / "does_not_exist.pdf"

    print(f"\n[test_pdfs_setup] Generated/Copied PDFs in: {base_temp_dir}")
    print(f"Keys: {list(paths_dict.keys())}")

    return paths_dict


# Note: May need `pip install reportlab Pillow` or add to pyproject.toml [tool.poetry.group.dev.dependencies]
