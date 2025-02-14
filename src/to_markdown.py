# to_markdown.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import pandas as pd

# Convert a pandas object to markdown format
def pandas_to_markdown(df: pd.DataFrame, index=False):
    # Handling column names and indexes
    columns = df.columns
    if index:
        columns = [''] + list(columns)
        data = [[i] + list(row) for i, row in df.iterrows()]
    else:
        data = [list(row) for _, row in df.iterrows()]
    
    # Build headers and separators
    header = "| " + " | ".join(map(str, columns)) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    # Generate data rows
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in data]
    
    # Merge into a complete table
    return "\n".join([header, separator] + rows)
