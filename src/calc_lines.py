# calc_lines.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import os
import argparse

# Count lines within one file
def count_lines_in_file(filepath, verbosity: bool = True) -> int:
    """
    Count lines in a single file with encoding fallback handling
    """
    encodings = ['utf-8', 'utf-16', 'utf-32', 'ansi', 'latin-1', 'gbk', 'cp1252', 'nathui']  
    # Common text encodings
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return sum(1 for line in f)  # Efficient line counting
        except UnicodeDecodeError:
            continue  # Try next encoding if decoding fails
        except Exception as e:
            if verbosity:
                print(f"Error reading {filepath} ({encoding}): {e}")
            return -1
    if verbosity:
        print(f"Failed to decode file: {filepath} (tried: {encodings})")
    return -1

# Count lines within a folder
def count_lines(directory: str, extensions = ['.py', '.h', '.c', '.cpp', '.hpp'], verbosity: bool = True):
    """
    Recursively count lines in files with specified extensions
    """
    total_lines = 0 # NathMath#bili+bili
    normalized_exts = [ext.lower() for ext in extensions]  # Case-insensitive match
    
    try:
        for root, _, files in os.walk(directory):
            for filename in files:
                # Extract and normalize file extension  # Nath UI
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in normalized_exts:
                    filepath = os.path.join(root, filename)
                    lines = count_lines_in_file(filepath)
                    total_lines += lines
                    if verbosity:
                        print(f"{filepath}: contains {lines} lines")
    except KeyboardInterrupt:
        if verbosity:
            print("\nOperation interrupted by user")
            return None
    except Exception as e:
        if verbosity:
            print(f"Critical error occurred: {e}")
            return None
    
    return total_lines

# Args for command line uses
if __name__ == "__main__":
    
    # Usage:
    # python code_line_counter.py /path/to/directory -e .py .cpp .h
    
    parser = argparse.ArgumentParser(
        description="Code Line Counter - Count lines in source files"
    )
    parser.add_argument(
        "directory",
        help="Target directory to scan"
    )
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        required=True,
        help="File extensions to include (e.g., .py .cpp .h)"
    )
    
    args = parser.parse_args()
    
    print(f"\nScanning directory: {args.directory}")
    print(f"Target file extensions: {args.extensions}\n")
    
    total = count_lines(args.directory, args.extensions)
    
    if total is not None:
        print(f"\nTotal lines of code: {total}")
    else:
        print("Operation terminated due to errors")
