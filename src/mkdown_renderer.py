# mkdown_renderer.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import sys
import markdown
import mdx_math # pip install python-markdown-math
import pymdownx # pip install pymdown-extensions
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView

# Global configuration variables
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
DEFAULT_FONT_FAMILY = "Arial, sans-serif"
DEFAULT_FONT_SIZE = 22  # in pixels
DEFAULT_EXTRA_CSS = ""  # additional custom CSS if needed

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

class MarkdownRenderer(QMainWindow):
    def __init__(self, md_text, title="", font_family=DEFAULT_FONT_FAMILY, 
                 font_size=DEFAULT_FONT_SIZE, extra_css=DEFAULT_EXTRA_CSS):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.browser = QWebEngineView(self)
        self.setCentralWidget(self.browser)
        self.font_family = font_family
        self.font_size = font_size
        self.extra_css = extra_css
        self.html_content = self._convert_markdown(md_text)
        self._load_html()

    def _convert_markdown(self, md_text):
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
                mdx_math.MathExtension(enable_dollar_delimiter = True, use_gitlab_delimiters = True)
            ]
        )
        
        # Constructing CSS style blocks
        style = f"""
        <style>
            body {{
                font-family: {self.font_family};
                font-size: {self.font_size}px;
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
            {self.extra_css}
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

    def _load_html(self):
        # Load the constructed HTML content into the web engine view.
        self.browser.setHtml(self.html_content)

def go_renderer(markdown_md: str, title: str = "", font_family: str = DEFAULT_FONT_FAMILY,
                font_size: int = DEFAULT_FONT_SIZE, extra_css: str = DEFAULT_EXTRA_CSS):
    app = QApplication(sys.argv)
    try:
        window = MarkdownRenderer(markdown_md, title, font_family, font_size, extra_css)
        window.show()
        sys.exit(app.exec_())
    except:
        pass  # User closed the window

def test_renderer():
    # Sample markdown text including all requested features.
    sample_md = "\n\n为了计算W(t)、W(s)和W(u)之间的协方差矩阵，我们假设数据是按样本排列的，其中每行代表一个样本，各列为不同的时间点。具体步骤如下：\n\n1. **读取数据**：获得W(t)、W(s)和W(u)三个向量。\n   \n   \\[\n   W(t) = [w_{1t}, w_{2t}, ..., w_{nt}]^T\n   \\]\n   \n   \\[\n   W(s) = [w_{1s}, w_{2s}, ..., w_{ns}]^T\n   \\]\n   \n   \\[\n   W(u) = [w_{1u}, w_{2u}, ..., w_{nu}]^T\n   \\]\n\n2. **计算每个变量的均值**：\n\n   \\[\n   \\mu_t = \\frac{1}{n} \\sum_{i=1}^n w_{it}\n   \\]\n   \n   \\[\n   \\mu_s = \\frac{1}{n} \\sum_{i=1}^n w_{is}\n   \\]\n   \n   \\[\n   \\mu_u = \\frac{1}{n} \\sum_{i=1}^n w_{iu}\n   \\]\n\n3. **构造协方差矩阵**：\n\n   协方差矩阵是一个3x3的矩阵，每个元素C_{ij}表示变量X和Y之间的协方差（或样本协方差）。\n\n   - **Variances**：\n     \\[\n     C_{11} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)^2\n     \\]\n     \n     \\[\n     C_{22} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)^2\n     \\]\n     \n     \\[\n     C_{33} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)^2\n     \\]\n\n   - **Covariances**：\n     \\[\n     C_{12} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{is} - \\mu_s)\n     \\]\n     \n     \\[\n     C_{13} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{iu} - \\mu_u)\n     \\]\n     \n     \\[\n     C_{23} = \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)(w_{iu} - \\mu_u)\n     \\]\n\n4. **构造协方差矩阵**：\n\n   \\[\n   Covariance Matrix =\n   \\begin{bmatrix}\n   C_{11} & C_{12} & C_{13} \\\\\n   C_{21} & C_{22} & C_{23} \\\\\n   C_{31} & C_{32} & C_{33}\n   \\end{bmatrix}\n   \\]\n\n**LaTeX表示的协方差矩阵**：\n\n```latex\n\\text{Covariance Matrix } = \n\\begin{bmatrix}\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)^2 & \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{is} - \\mu_s) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{iu} - \\mu_u) \\\\\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)(w_{it} - \\mu_t) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)^2 & \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)(w_{iu} - \\mu_u) \\\\\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)(w_{it} - \\mu_t) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)(w_{is} - \\mu_s) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)^2\n\\end{bmatrix}\n```\n\n**Markdown表示的协方差矩阵**：\n\n```markdown\n\\text{Covariance Matrix } = \n\\begin{bmatrix}\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)^2 & \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{is} - \\mu_s) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{it} - \\mu_t)(w_{iu} - \\mu_u) \\\\\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)(w_{it} - \\mu_t) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)^2 & \\frac{1}{n-1} \\sum_{i=1}^n (w_{is} - \\mu_s)(w_{iu} - \\mu_u) \\\\\n\\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)(w_{it} - \\mu_t) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)(w_{is} - \\mu_s) & \\frac{1}{n-1} \\sum_{i=1}^n (w_{iu} - \\mu_u)^2\n\\end{bmatrix}\n```\n\n这个矩阵展示了W(t)、W(s)和W(u)之间的所有协方差关系，包括各自变量之间的相关性。\n\n以下是整理的一张微分表：\n\n| **标题**        | **导数公式**                                                                 |\n|-----------------|-----------------------------------------------------------------------------|\n| 基本导数法则    | \\( \\frac{d}{dx} c = 0 \\) (常数的导数是零)                            |\n| 导数性质        | 如果 \\( f(x) \\) 是可导函数，那么 \\( f'(x) \\) 存在且定义为：\\( f'(x) = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h} \\) |\n| 导数的四则运算   | 若 \\( f(x) \\) 和 \\( g(x) \\) 都是可导函数，则：                  |\n|               | 1. 加法法则：\\( (f + g)'(x) = f'(x) + g'(x) \\)             |\n|               | 2. 减法法则：\\( (f - g)'(x) = f'(x) - g'(x) \\)            |\n|               | 3. 乘法规则：\\( (f \\cdot g)'(x) = f'(x)g(x) + f(x)g'(x) \\)       |\n|               | 4. 商法则：\\( \\left(\\frac{f}{g}\\right)'(x) = \\frac{f'(x)g(x) - f(x)g'(x)}{(g(x))^2} \\)     |\n| 隐函数求导      | 若 \\( y \\) 可以用参数方程表示为 \\( x(t) \\) 和 \\( y(t) \\)，则：           |\n|               | 1. 参数形式的隐函数求导法则：\\( \\frac{dy}{dx} = \\frac{\\frac{dy}{dt}}{\\frac{dx}{dt}} \\)         |\n|                | (分母必须不为零)                                           |\n| 参数方程求导     | 若 \\( x = x(t) \\) 和 \\( y = y(t) \\)，则：                           |\n|               | 1. 求 \\( dy/dx \\) 或 \\( dx/dy \\) 的方法。                          |\n| 高阶导数          | 若 \\( f(x) \\) 在某点可导，则一阶导数为 \\( f'(x) \\)，二阶导数为：       |\n|               | 1. \\( (f')' = f'' \\)；2. \\( (f \\cdot g)'' = f''g + 2f'g' + fg'' \\)  （莱布尼茨法则）     |\n\n希望这份微分表对你有帮助"
    sample_md += "\n\nThe documentation describes **CryptoMessager**, an open-source toolkit designed for conducting encrypted communication and online meetings. Below is a structured and organized summary of the information provided:\n\n---\n\n### 1. **Introduction**\n- **Primary Functionality**:  \n  - A user-friendly toolkit for encrypting and decrypting text and files while ensuring privacy and security.\n- **Features**:  \n  - Built-in command line interface with shortcuts (Ctrl + C for copy, Ctrl + V for paste).\n  - Automatic encryption/decryption using shortcuts that are imperceptibly fast during copying and pasting in the GUI.\n\n---\n\n### 2. **Special Notifications**\n- **Important Points**:  \n  - Do not transmit any SMS code over the internet, as it may be intercepted.\n  - Use a unique identifier (e.g., a random string) to encrypt messages intended for external recipients.\n  - Avoid using third-party services or untrusted internet sources for encryption.\n\n---\n\n### 3. **Features**\n- **Encryption and Decryption**:  \n  - Uses the DOF Studio Hybrid-Minus Algorithm set for secure encryption/decryption.\n  - Supports multi-step layering of encryption to enhance security.\n  - Can encrypt files, folders, and even full documents (e.g., text or file structures).\n- **Partial Ciphertext Support**:  \n  - Allows users to decrypt only a portion of the message while preserving the rest for further analysis.\n- **Advanced Features**:  \n  - File format support: Microsoft Word, PowerPoint, Excel.\n  - Integration with minichatter for secure P2P communication.\n  - Automatic updates and versioning support (e.g., rolling updates every six months).\n- **Security Improvements**:  \n  - Added SMS code verification to ensure authenticity of messages from untrusted sources.\n\n---\n\n### 4. **Basic Features**\n- **Encryption Method**:  \n  - Uses Hybrid-Minus Algorithm set by DOF Studio.\n  - Time complexity: O(log N), where N is the size of the message.\n- **Encryption Process**:  \n  - Combines multiple encryption steps for enhanced security, with a time consumption range from 16x to 20x.\n\n---\n\n### 5. **Notifications**\n- **Important Warnings**:  \n  - Do not transmit SMS codes over the internet as they may be intercepted by third-party services.\n  - Use unique identifiers for messages intended for external recipients.\n  - Do not use untrusted or proprietary encryption tools for secure communication.\n\n---\n\n### 6. **Features and Implementation**\n- **Dynamic Encryption**:  \n  - The system automatically detects the need to encrypt files based on their content.\n- **Command Line Interface (CLI)**:  \n  - CLI support is available, with commands that can be executed via help or by pressing a key combination.\n- **Multi-Language Support**:  \n  - The tool supports multiple languages including Japanese, Korean, and English.\n\n---\n\n### 7. **Version and Support**\n- **Standard Support**:  \n  - Stable version: `v0.0.1.3`.\n  - Long-period support until `v2.6.0` (with possible updates every six months).\n- **Military Use**:  \n  - For military use, a separate license (Apache-2.0 with Non-Military Use Restriction) is required.\n\n---\n\nThis documentation provides a comprehensive overview of CryptoMessager's features, implementation, and security considerations, making it suitable for users looking to protect their communications and meetings with encrypted tools."

    go_renderer(sample_md, title="Markdown Renderer with Full Features")
    
# Test
if __name__ == "__main__":
    test_renderer()
