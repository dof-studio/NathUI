# mkdown_convertor.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import re
import sys
import time
import mdx_math # pip install python-markdown-math
import pymdownx # pip install pymdown-extensions
import markdown
import asyncio

DEFAULT_FONT_FAMILY = "Arial, sans-serif"
DEFAULT_FONT_SIZE = 22  # in pixels
DEFAULT_EXTRA_CSS = ""

MATHJAX_CONFIG = """ 
<script>
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']],
    processEscapes: true
  },
  svg: {
    fontCache: 'global'
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
  }
};
</script>
"""

MATHJAX_SCRIPT = """
<script type="text/javascript" id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
</script>
"""

# Generate a html from markdown
def convert_markdown_to_html(md_text: str, font_family: str, font_size: str, extra_css: str):
    # Use the math extension to process LaTeX mathematical expressions
    html_body = markdown.markdown(
        md_text,
        extensions=[
            'nl2br',
            'extra',
            'fenced_code', 
            'codehilite', 
            'meta',  
            'footnotes',      
            'def_list',
            'admonition', 
            'attr_list',
            'abbr',
            'tables',
            'sane_lists',
            'toc',
            'smarty',
            mdx_math.MathExtension(enable_dollar_delimiter=True, use_gitlab_delimiters = True)
        ]
    )
    
    # Constructing CSS style blocks
    style = f"""
    <style>
        body {{
            font-family: {font_family};
            font-size: {font_size}px;
            margin: 20px;
            line-height: 1.6;
        }}
        h1 {{ font-size: 32px; }}
        h2 {{ font-size: 28px; }}
        h3 {{ font-size: 24px; }}
        h4 {{ font-size: 20px; }}
        h5 {{ font-size: 18px; }}
        h6 {{ font-size: 16px; }}
        strong {{ font-weight: bold; }}
        em {{ font-style: italic; }}
        blockquote {{
            border-left: 4px solid #ccc;
            padding-left: 16px;
            margin: 10px 0;
            color: #666;
            font-style: italic;
        }}
        pre, code {{
            font-family: "Courier New", Courier, monospace;
        }}
        pre code {{
            display: block;
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            border: 1px solid #ddd;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        hr {{
            border: 0;
            height: 1px;
            background: #ccc;
            margin: 20px 0;
        }}
        {extra_css}
    </style>
    """
   
    # Assemble the complete HTML document and ensure that the MathJax script can process mathematical formulas
    html_full = f"""
    <html>
    <head>
        <meta charset="utf-8">
        {style}
        {MATHJAX_CONFIG}
        {MATHJAX_SCRIPT}
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    return html_full
