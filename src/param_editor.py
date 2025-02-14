# param_editor.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################

import ast
import re

# Parameters editor
class ParamEditor:
    def __init__(self, filename):
        """
        Initialize the GlobalVarEditor with the given Python file.
        It loads the file content, extracts global variable assignments,
        and saves both the variable dictionary and the file lines.
        """
        self.filename = filename
        self.var_dict = {}        # Dictionary to store variable names and their evaluated values
        self._lines = []          # List to store all lines from the file
        self._assignments = {}    # Mapping: variable name -> (line index, regex groups)
        self.load_globals()

    def load_globals(self):
        """
        Reads the file and extracts global variable assignments.
        For each non-comment, non-empty line it attempts to match an assignment.
        The regex is designed to capture:
            - Leading whitespace
            - Variable name
            - The assignment operator (with surrounding spaces)
            - The value expression (as a string)
            - The trailing comment (if any)
        The value expression is safely evaluated using ast.literal_eval.
        """
        with open(self.filename, 'r', encoding='utf-8') as f:
            self._lines = f.readlines()
        
        # Regex to capture a global variable assignment.
        # It captures:
        #   group(1): leading whitespace
        #   group(2): variable name
        #   group(3): the assignment operator including surrounding whitespace
        #   group(4): the variable value expression (non-greedy)
        #   group(5): trailing whitespace and comment (if any)
        assignment_regex = re.compile(r'^(\s*)(\w+)(\s*=\s*)(.*?)(\s*(#.*)?)$')
        
        for index, line in enumerate(self._lines):
            stripped = line.strip()
            # Skip empty lines or lines that are only comments
            if not stripped or stripped.startswith("#"):
                continue

            # Attempt to match an assignment
            match = assignment_regex.match(line)
            if match:
                var_name = match.group(2)
                var_value_str = match.group(4)
                try:
                    # Safely evaluate the literal value
                    var_value = ast.literal_eval(var_value_str)
                except Exception:
                    # If evaluation fails, store the original string (could log a warning)
                    var_value = var_value_str.strip()
                
                # Save the variable and its evaluated value
                self.var_dict[var_name] = var_value
                # Save the assignment information so we can update the file later.
                self._assignments[var_name] = (index, match.groups())
            else:
                # Warn if a non-comment line does not match the expected assignment format.
                print(f"Warning: Line {index + 1} does not match the expected assignment format: {line.strip()}")

    def apply_modifications(self):
        """
        Applies modifications from the var_dict back to the in-memory file lines,
        updating only the value part of each variable assignment.
        It then writes the updated lines back to the original file.
        """
        # Iterate over each recorded assignment.
        for var_name, (line_index, groups) in self._assignments.items():
            # groups breakdown:
            #   groups[0]: leading whitespace
            #   groups[1]: variable name
            #   groups[2]: assignment operator (with spaces)
            #   groups[3]: original value string (to be replaced)
            #   groups[4]: trailing whitespace and comment (if any)
            leading_ws = groups[0]
            name = groups[1]
            assign_operator = groups[2]
            # Strip any newline characters from the trailing part to avoid duplication.
            trailing_comment = groups[4].rstrip("\n\r")
            
            # Use the updated value from var_dict if present.
            if var_name in self.var_dict:
                new_value = self.var_dict[var_name]
                # Use repr() to get a valid Python literal representation of the new value.
                new_value_str = repr(new_value)
                
                # Check whether the original line ended with a newline.
                orig_line = self._lines[line_index]
                newline = "\n" if orig_line.endswith("\n") else ""
                
                # Reconstruct the assignment line preserving the original formatting.
                new_line = f"{leading_ws}{name}{assign_operator}{new_value_str}{trailing_comment}{newline}"
                self._lines[line_index] = new_line
    
        # Write the updated lines back to the file.
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.writelines(self._lines)


# Example usage:
if __name__ == "__main__":
    
    # Connect
    editor = ParamEditor("params2-simupy")
    
    # Print the currently extracted globals
    print("Original globals:")
    for key, value in editor.var_dict.items():
        print(f"  {key} = {value!r}")

    # Modify the variable values as needed.
    if "nathui_backend_search_no" in editor.var_dict:
        editor.var_dict["nathui_backend_search_no"] = editor.var_dict["nathui_backend_search_no"] + 1

    # Another example: change a string variable 'greeting'
    # if "greeting" in editor.var_dict:
    #    editor.var_dict["greeting"] = "Hello, world!"

    # Apply the modifications to the file.
    # editor.apply_modifications()
    # print("Modifications applied to the file.")
