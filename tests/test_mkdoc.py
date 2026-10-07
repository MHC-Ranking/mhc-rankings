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
        assert "Bradley-Terry" in content
        # Ensure that markdown-it-py processed the table successfully
        assert "<table" in content
