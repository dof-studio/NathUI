# codeinterpretor_python.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################


import io
import sys
import contextlib
import traceback
import base64
from io import BytesIO

class CodeEvaluatorPython:
    """
    A class to evaluate a given Python code string after trimming it, capturing all outputs, errors,
    and any matplotlib plots generated during execution. Pre-imports a wide range of common libraries,
    including data analysis and development libraries.
    """
    
    def __init__(self) -> None:
        # Import common libraries for general development and data analysis.
        import os, math, datetime, re, random, json
        import numpy
        import numpy as np
        import pandas
        import pandas as pd
        import matplotlib
        # Use a non-interactive backend for matplotlib to capture plots without displaying them.
        matplotlib.use("Agg")
        import matplotlib
        import matplotlib.pyplot as plt
        import seaborn
        import scipy
        import sympy
        import requests
        import itertools
        import collections
        import logging
        import typing
        import sklearn

        # Store the imported libraries in the evaluation environment.
        self.env = {
            "os": os,
            "sys": sys,
            "math": math,
            "datetime": datetime,
            "re": re,
            "random": random,
            "json": json,
            "np": np,
            "numpy": np,
            "pd": pd,
            "pandas": pd,
            "plt": plt,
            "matplotlib": matplotlib,
            "seaborn": seaborn,
            "scipy": scipy,
            "sympy": sympy,
            "requests": requests,
            "itertools": itertools,
            "collections": collections,
            "logging": logging,
            "typing": typing,
            "sklearn": sklearn,
        }
    
    def run_code(self, code_str: str) -> dict:
        """
        Evaluate the provided code string after trimming it, and capture its outputs, errors,
        and any matplotlib plots generated.
        
        Args:
            code_str (str): The Python code string to evaluate.
        
        Returns:
            dict: A dictionary with keys 'result', 'output', 'error', and 'plots' where:
                  - 'result' is the return value of eval() if applicable (None for exec code),
                  - 'output' is the captured stdout output,
                  - 'error' is any error messages or traceback captured,
                  - 'plots' is a list of base64-encoded PNG images of the matplotlib plots.
        """
        # Trim the input code string.
        code_str = code_str.strip()
        
        # Prepare StringIO objects to capture stdout and stderr.
        output_capture = io.StringIO()
        error_capture = io.StringIO()
        result = None
        
        # Redirect stdout and stderr to capture outputs and errors.
        with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(error_capture):
            try:
                try:
                    # Try compiling the code as an expression.
                    compiled_code = compile(code_str, "<string>", "eval")
                    result = eval(compiled_code, self.env)
                except SyntaxError:
                    # If not an expression, compile as statements.
                    compiled_code = compile(code_str, "<string>", "exec")
                    exec(compiled_code, self.env)
            except Exception:
                # Capture the full traceback into error_capture.
                traceback.print_exc(file=error_capture)
        
        # Retrieve captured output and errors.
        output = output_capture.getvalue()
        error = error_capture.getvalue()
        
        # Capture any matplotlib plots generated during code execution.
        plots = []
        try:
            # Import matplotlib.pyplot from our evaluation environment.
            plt = self.env.get("plt", None)
            if plt:
                # Iterate over all figure numbers.
                for fig_num in plt.get_fignums():
                    fig = plt.figure(fig_num)
                    buf = BytesIO()
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    encoded = base64.b64encode(buf.getvalue()).decode('utf-8')
                    plots.append(encoded)
                # Close all figures to free resources.
                plt.close('all')
        except Exception:
            # If any error occurs while capturing plots, ignore it.
            pass

        return {"result": result, "output": output, "error": error, "plots": plots}

# Example usage:
if __name__ == "__main__":
    evaluator = CodeEvaluatorPython()
    # Example code that prints output, creates a matplotlib plot, and returns a value.
    code_string = """
import torch
print("Hello, World!")
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2, 3], [4, 5, 6])
plt.title("Sample Plot")
x = 42
x
"""
    result = evaluator.run_code(code_string)
    print("Captured Output:")
    print(result["output"])
    print("Captured Error:")
    print(result["error"])
    print("Evaluation Result:")
    print(result["result"])
    if result["plots"]:
        print("Captured Plots (base64 encoded PNG):")
        for idx, plot in enumerate(result["plots"], 1):
            print(f"Plot {idx}: {plot[:100]}...")  # printing only first 100 characters for brevity
    else:
        print("No plots captured.")