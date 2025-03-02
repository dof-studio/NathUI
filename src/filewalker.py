# filewalker.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# Des
#
# A class to traverse N levels (N≥1) of a specified folder, 
# returning a nested dictionary containing basic info of
# files/directories: relative path, size, type (file/folder), 
# last modified time.

import os
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

# FileWalker - walk around file system
class FileWalker:
    """
    Traverses a given directory up to a specified depth and collects basic file/folder information.
    
    Attributes:
        root (str): The root directory to start traversal.
        max_depth (int): Maximum depth to traverse. For example, if max_depth is 1, only the immediate 
                         files and folders inside the root are processed.
    """
    def __init__(self, root: str, max_depth: int) -> None:
        if not os.path.isdir(root):
            raise ValueError(f"Provided root path '{root}' is not a valid directory.")
        if max_depth < 1:
            max_depth = 1000000
        self.root = os.path.abspath(root)
        self.max_depth = max_depth
        
    # Traverse and return file/folder info
    def traverse(self) -> Dict[str, Dict[str, Any]]:
        """
        Traverse the directory up to max_depth and collect file and folder information.
        
        Returns:
            dict: A dictionary where each key is the relative path (to the root) of a file or folder,
                  and the value is another dictionary containing:
                      - 'relative_path': Relative path from the root.
                      - 'size': File size in bytes (for files; None for folders).
                      - 'type': 'file' or 'folder'.
                      - 'modification_time': Last modification time in ISO format.
        """
        result: Dict[str, Dict[str, Any]] = {}
        # Start traversal from the root's children. The root itself is level 0; its immediate children are level 1.
        self._traverse(self.root, current_level=1, result=result)
        return result

    # [Kernel] Traverse
    def _traverse(self, current_path: str, current_level: int, result: Dict[str, Dict[str, Any]]) -> None:
        """
        Recursively traverses the directory tree until the specified depth is reached.
        
        Args:
            current_path (str): The current directory path being traversed.
            current_level (int): The current depth level (root's immediate children are at level 1).
            result (dict): The dictionary collecting file/folder information.
        """
        try:
            with os.scandir(current_path) as it:
                for entry in it:
                    try:
                        rel_path = os.path.relpath(entry.path, self.root)
                        stat_info = entry.stat(follow_symlinks=False)
                        entry_info = {
                            'relative_path': rel_path,
                            'size': stat_info.st_size if entry.is_file(follow_symlinks=False) else None,
                            'type': 'file' if entry.is_file(follow_symlinks=False) else 'folder',
                            'modification_time': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                        }
                        result[rel_path] = entry_info
                    except Exception:
                        # In production, consider logging the error for this entry.
                        continue

                    # If the entry is a directory and we haven't reached the max_depth, traverse further.
                    if entry.is_dir(follow_symlinks=False) and current_level < self.max_depth:
                        self._traverse(entry.path, current_level + 1, result)
        except Exception:
            # If the current_path cannot be accessed (e.g., due to permissions), skip it.
            pass
        
    # [Util] Convert file dict into a pandas DataFrame
    @staticmethod
    def get_pd_dataframe(traversed_dict: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert a dictionary of dictionaries into a pandas DataFrame.
        Each key in the input dict becomes a row with a 'path' column, and
        the inner dictionary values become additional columns. Nested dictionaries
        or lists are converted to JSON strings.
        
        Parameters:
            data (dict): The dictionary of dictionaries to convert.
            
        Returns:
            pd.DataFrame: A DataFrame representing the flattened data.
        """
        rows = []
        for path, info in traversed_dict.items():
            row = {"path": path}
            for key, value in info.items():
                # Convert nested dicts or lists into JSON strings to maintain structure.
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value)
                else:
                    row[key] = value
            rows.append(row)
        return pd.DataFrame(rows)

    # [Util] Extract all names
    @staticmethod
    def get_all_names(traversed_dict: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Extract a list of names from a dictionary of dictionaries based on the dictionary.
        
        Parameters:
            traversed_dict (dict): A dictionary where each value is another dictionary.
        
        Returns:
            list: A list of names corresponding to the given archtecture.
        """
        return list(traversed_dict)
    
    # [Util] Extravt tree structure
    @staticmethod
    def get_tree_structure(traversed_dict: Dict[str, Dict[str, Any]], store_full_info: bool = False) -> Dict[str, Any]:
        """
        Build a nested tree structure from a flat dictionary whose keys are paths.
        Each folder becomes a dict with a 'files' list for immediate file entries and subfolders as keys.
        When store_full_info is True, the full info dictionary is stored for files and folders; otherwise, only the names are stored.
        
        Parameters:
            traversed_dict (dict): A dictionary with keys as paths (using "\\" as separator)
                                   and values containing info (including 'type').
            store_full_info (bool): If True, store the complete info for files and folders.
                                    If False, store only the name.
        
        Returns:
            dict: A nested dictionary representing the tree.
        """
        tree = {}
        for path, info in traversed_dict.items():
            parts = path.split("\\")
            current = tree
            for idx, part in enumerate(parts):
                is_last = (idx == len(parts) - 1)
                if not is_last:
                    # Create intermediate folder if missing.
                    if part not in current:
                        current[part] = {"info": None, "files": []} if store_full_info else {"files": []}
                    current = current[part]
                else:
                    if info.get("type") == "folder":
                        # Folder: create or update node.
                        if part not in current:
                            current[part] = {"info": info, "files": []} if store_full_info else {"files": []}
                        elif store_full_info and current[part].get("info") is None:
                            current[part]["info"] = info
                    else:
                        # File: add either full info or just the name to parent's 'files' list.
                        if "files" not in current:
                            current["files"] = []
                        if store_full_info:
                            current["files"].append(info)
                        else:
                            current["files"].append(part)
        return tree
    
    # [Util] Extract all values corresponding to a key
    @staticmethod
    def get_key_values(traversed_dict: Dict[str, Dict[str, Any]], key: str) -> List[Any]:
        """
        Extract a list of values from a dictionary of dictionaries based on the specified key.
        
        Parameters:
            traversed_dict (dict): A dictionary where each value is another dictionary.
            key (str): The key whose value will be extracted from each inner dictionary.
        
        Returns:
            list: A list of values from the dict corresponding to the given key.
        """
        return [inner[key] for inner in traversed_dict.values() if key in inner]

if __name__ == "__main__":
    # Example usage:
    # Replace 'your_directory_path_here' with the absolute or relative path to the target directory.
    test_directory = r"../../"
    max_depth = 1  # You can set this to 1, 2, or any desired level.
    
    traverser = FileWalker(test_directory, max_depth)
    tree_info = traverser.traverse()
    
    # Print out the collected file and folder information.
    for rel_path, info in tree_info.items():
        print(f"->{rel_path}: {info}")
        
    traverser.get_all_names(tree_info)
