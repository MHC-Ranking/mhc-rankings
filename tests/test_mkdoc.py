import os
from pathlib import Path
from mhc_rankings.mkdoc import convert_markdown_to_html

def test_convert_algorithms_md(tmp_path):
    """Test generating an HTML document from docs/algorithms.md."""
    project_root = Path(__file__).parent.parent
    input_md = project_root / "docs" / "algorithms.md"
    
    assert input_md.exists(), f"Could not find {input_md}"
    
    output_html = tmp_path / "algorithms.html"
    
    # Run the conversion
    convert_markdown_to_html(input_md, output_html)
    
    # Verify the file was created
    assert output_html.exists(), "Output HTML file was not created"
    
    # Verify contents
    with open(output_html, "r", encoding="utf-8") as f:
        content = f.read()
        
        # Check for expected template and content elements
        assert "<!DOCTYPE html>" in content
        assert "Table of Contents" in content
        assert "Colley Matrix" in content
        assert "Bradley-Terry" not in content
        # Ensure that markdown-it-py processed the table successfully
        assert "<table" in content


def test_plain_language_comes_first_and_technical_details_are_collapsed(tmp_path: Path) -> None:
    """The plain explanation and points table come before a closed Technical details block holding the math."""
    output_html = tmp_path / "algorithms.html"
    convert_markdown_to_html(Path(__file__).parent.parent / "docs" / "algorithms.md", output_html)
    content = output_html.read_text(encoding="utf-8")

    plain = content.index("How the Rankings Work, in Plain Language")
    table = content.index("Overtime win")
    technical = content.index("<summary>Technical details</summary>")
    matrix = content.index("The Colley Matrix Method", technical)
    assert plain < table < technical < matrix
    assert "<details>" in content and "<details open" not in content
    assert "0.667" in content[table:technical]
