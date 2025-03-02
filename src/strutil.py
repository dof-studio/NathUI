# strutil.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import re

# String unquote
def str_unquote(s: str) -> str:
    '''
    Consider using str.strip() or this.

    Parameters
    ----------
    s : str
        A string that may contains " or ' at the beginning or end 

    Returns
    -------
    str
        A clear string that does not contains " or ' at the beginning or end

    '''
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s

def str_demarkdown(text):
    """
    Remove common markdown formatting symbols from a string.

    This function processes the input text and strips out various markdown elements,
    including code blocks, inline code, bold/italic markers, links, headers, blockquotes,
    list markers, and extra hyphens used as separators. The result is a cleaned text suitable
    for feeding into a text-to-speech engine.

    Parameters
    ----------
    text : str
        A string that may contain markdown formatting symbols.

    Returns
    -------
    str
        A cleaned string with markdown formatting removed.
    """
    # Remove code blocks that are wrapped in triple backticks, including any content within.
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove inline code that is wrapped in single backticks.
    text = re.sub(r'`([^`]+?)`', r'\1', text)
    
    # Remove markdown emphasis markers for bold and italic (e.g., **text**, *text*, __text__, _text_).
    text = re.sub(r'(\*\*|\*|__|_)(.*?)\1', r'\2', text)
    
    # Replace markdown links [text](url) with just the text portion.
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown headers by eliminating leading '#' characters (from one to six) and any following spaces.
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # Remove blockquotes by deleting the leading '>' and any following spaces at the beginning of lines.
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove list markers (such as '-', '*', '+') from the start of lines.
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    
    # Replace hyphens used as separators with a space to avoid merging words unintentionally.
    text = re.sub(r'\s*-\s*', ' ', text)
    
    # Replace multiple whitespace characters (including newlines) with a single space.
    text = re.sub(r'\s+', ' ', text)
    
    # Return the cleaned text after stripping leading/trailing whitespace.
    return text.strip()
