# hf_cldownload.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import os
import time
from huggingface_hub import snapshot_download

# Replace with your actual model repository identifier on Hugging Face
model_id = "lmstudio-community/Phi-3.5-MoE-instruct-GGUF"
# Set the directory where you want the repository downloaded
local_dir = r"F:\AI-Models\2025\Phi-3.5-MoE-instruct-GGUF"
if os.path.exists(local_dir) == False:
    os.makedirs(local_dir)
# Optional: specify a cache directory for reusing downloaded files
cache_dir = r"F:\AI-Models\cache"
if os.path.exists(cache_dir) == False:
    os.makedirs(cache_dir)
# Optional: set your Hugging Face authentication token if needed
hf_token = "hf_..."
# Optional: specify proxy settings if your network requires them
proxies = {"http": "http://127.0.0.1:3128", "https": "http://127.0.0.1:3128"}

while True:
    try:
        snapshot_download(
            repo_id=model_id,
            revision="main",                   # Specify branch, commit hash, or tag
            cache_dir=cache_dir,               # Custom cache directory for efficiency
            local_dir=local_dir,               # Destination directory for the repo
            local_dir_use_symlinks=False,      # Use copies instead of symlinks (helpful on Windows)
            resume_download=True,              # Enable resuming of partially downloaded files
            # token=hf_token,                    # Authentication token for private repositories
            # library_name="my_custom_downloader",  # Custom identifier for analytics
            # library_version="1.0.0",           # Version information for your downloader
            # proxies=proxies,                   # Configure proxies if required
            ignore_patterns=["*.tmp", "*.log"] # Ignore temporary or log files to save bandwidth
        )
        print("Download completed successfully.")
        break  # Exit loop when finished
    except Exception as error:
        print(f"An error occurred during download: {error}")
        print("Waiting 10 seconds before retrying...")
        time.sleep(10)
