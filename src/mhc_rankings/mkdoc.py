import os
import re
import argparse
from pathlib import Path
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from jinja2 import Environment, FileSystemLoader

def slugify(text):
    """Convert text into a valid HTML id attribute."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def extract_text_from_tokens(tokens, start_idx):
    """Extract raw text from inline tokens until the heading closes."""
    title = ""
    for j in range(start_idx, len(tokens)):
        if tokens[j].type == 'heading_close':
            break
        if tokens[j].type == 'inline':
            title += tokens[j].content
    return title

def convert_markdown_to_html(input_path, output_path=None):
    """Parse Markdown, extract TOC, and render styled HTML."""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: File '{input_path}' not found.")
        return

    if output_path:
        out_file = Path(output_path)
    else:
        out_file = input_file.with_suffix('.html')

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Initialize markdown-it-py with tables support
    md = MarkdownIt("commonmark", {"html": True}).enable("table").use(dollarmath_plugin, double_inline=True)
    env = {}
    tokens = md.parse(content, env)
    
    toc = []
    # Identify headings, build TOC, and assign IDs to heading tokens
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            level = int(token.tag[1]) # 'h1' -> 1
            title = extract_text_from_tokens(tokens, i + 1)
            
            if title:
                slug = slugify(title)
                # Assign ID to the heading token
                token.attrSet('id', slug)
                toc.append({
                    'level': level,
                    'title': title,
                    'slug': slug
                })

    html_content = md.renderer.render(tokens, md.options, env)

    # Convert mdit-py-plugins dollarmath output back to MathJax delimited strings
    html_content = re.sub(r'<span[^>]*class="math inline"[^>]*>(.*?)</span>', r'\\(\1\\)', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<div[^>]*class="math inline"[^>]*>(.*?)</div>', r'\\[\1\\]', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<div[^>]*class="math block"[^>]*>(.*?)</div>', r'\\[\1\\]', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<span[^>]*class="math block"[^>]*>(.*?)</span>', r'\\[\1\\]', html_content, flags=re.DOTALL)

    # Determine document title (use first H1 if available, else filename)
    doc_title = input_file.stem.replace('_', ' ').title()
    for item in toc:
        if item['level'] == 1:
            doc_title = item['title']
            break

    # Load Jinja template
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('doc.html')

    # Render final HTML
    final_html = template.render(
        title=doc_title,
        toc=toc,
        html_content=html_content
    )

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Successfully generated '{out_file}'")

def main():
    parser = argparse.ArgumentParser(description='Convert Markdown to a styled HTML document with a TOC sidebar.')
    parser.add_argument('input_md', help='Path to the input Markdown file.')
    parser.add_argument('-o', '--output', help='Path to the output HTML file. Defaults to input file with .html extension.')
    args = parser.parse_args()

    convert_markdown_to_html(args.input_md, args.output)

if __name__ == '__main__':
    main()
