# fileopener.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################


import os
import platform
import subprocess

class FileOpener:
    """
    A class that checks if a file exists and opens it with the default application.
    Compatible with Windows, macOS, and Linux.
    """
    
    def __init__(self, file_path: str) -> None:
        """
        Initialize with the file path.
        
        Args:
            file_path (str): The absolute or relative path to the file.
        """
        self.file_path = file_path
        
    # Open a file by its default software
    def open_file(self, raise_if_nexist = True) -> bool:
        """
        Check if the file exists and open it using the system's default application.
        
        Returns:
            bool: True if the file exists and is opened successfully, False otherwise.
        """
        if not os.path.exists(self.file_path):
            if raise_if_nexist:
                raise Exception(f"File does not exist: {self.file_path}")
            return False
        
        try:
            system_name = platform.system()
            if system_name == "Windows":
                os.startfile(self.file_path)
            elif system_name == "Darwin":  # macOS
                subprocess.run(["open", self.file_path], check=True)
            else:  # Linux and others
                subprocess.run(["xdg-open", self.file_path], check=True)
            return True
        except Exception:
            # In production, consider logging the exception details.
            if raise_if_nexist:
                raise
            return False

# Example usage:
if __name__ == "__main__":
    # Replace 'example.txt' with the path to the file you want to open.
    file_path = r"D:\ToolsJs\NeteaseDownloader\NeteaseDownloader 0.0.1\assets\favicon.svg"
    opener = FileOpener(file_path)
    if opener.open_file():
        print(f"Opened {file_path} successfully.")
    else:
        print(f"Failed to open {file_path}.")