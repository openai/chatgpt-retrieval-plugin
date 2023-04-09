import os
import tempfile
import pytest
from pathlib import Path
from services.file import extract_text_from_filepath
import matplotlib.pyplot as plt

TEST_DATA_DIR = Path(__file__).parent / "test_data"

def create_test_image(text: str, output_path: str) -> None:
    """Create an image with text."""
    fig, ax = plt.subplots(figsize=(5, 2), dpi=100)
    
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 2)
    ax.axis('off')

    ax.text(0.1, 0.5, text, fontsize=30, ha='left', va='center')

    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

@pytest.fixture
def test_image_path() -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
        test_text = "Hello world"
        create_test_image(test_text, f.name)
        yield f.name
        os.unlink(f.name)

def test_extract_text_from_generated_image(test_image_path: str) -> None:
    extracted_text = extract_text_from_filepath(test_image_path, "image/jpeg")
    assert "Hello world" in extracted_text

def test_extract_text_from_pdf() -> None:
    test_pdf_path = str(TEST_DATA_DIR / "numbers.pdf")
    extracted_text = extract_text_from_filepath(test_pdf_path, "application/pdf")
    for num in range(1, 5):
        assert str(num) in extracted_text

def test_extract_text_from_simpledoc_pdf() -> None:
    test_pdf_path = str(TEST_DATA_DIR / "simpledoc.pdf")
    extracted_text = extract_text_from_filepath(test_pdf_path, "application/pdf")
    # Check for a few specific words in the document to ensure text extraction
    assert "A purely peer-to-peer version of electronic cash" in extracted_text
    assert "a system for electronic transactions without relying on trust." in extracted_text
