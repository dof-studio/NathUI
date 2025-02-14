# dethink.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import re

def think_output_split(text : str):
    """
    Extract the content between the <think>...</think> tags and other parts of the text.
    Return a tuple (think_content, remaining_content):
    - think_content is the text between the <think> and </think> tags (excluding leading and trailing spaces).
    - remaining_content is all the content of the original text except the <think>...</think> part (excluding leading and trailing spaces).
    If the <think> tag is not found, return ("", text).
    """
    pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
    match = pattern.search(text)
    if match:
        think_content = match.group(1).strip()
        # Delete the matched <think>...</think> part from the original text
        remaining_content = text[:match.start()] + text[match.end():]
        
        # Think, Output
        return think_content, remaining_content.strip()
    else:
        return "", text.strip()
    