# strutil.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

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
