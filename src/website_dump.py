# website_dump.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import os
import re
import email
import base64
import pdfkit # pip install pdfkit
import datetime
import subprocess
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed

from debug import nathui_chorme_path

# Default chorme path
default_chorme_path = nathui_chorme_path

# Replace invalid path-characters in a string
def sanitize_path_name(name: str, replacement: str = "_") -> str:
    """
    Replaces all invalid characters in a string that cannot be part of a file path name.

    :param name: The input string to sanitize.
    :param replacement: The character to replace invalid characters with.
    :return: A sanitized string.
    """
    # Define a regex pattern to match invalid characters for file paths
    invalid_chars_pattern = r'[<>:"/\\|?*]'
    
    # Replace invalid characters with the specified replacement character
    sanitized_name = re.sub(invalid_chars_pattern, replacement, name)
    
    # Ensure the sanitized name doesn't have trailing or leading spaces
    sanitized_name = sanitized_name.strip()
    
    return sanitized_name

# Convert hmtml to pdf
def convert_mhtml_to_pdf(
    mhtml_file: str, 
    pdf_file: str, 
    chromedriver_path: str, 
    timeout: int = 10, 
    pagesize: tuple = (11, 8.5),
    landscape: bool = True,
    printBackground: bool = True,
    displayHeaderFooter: bool = False,
    marginTop: float = 0.4,
    marginBottom: float = 0.4,
    marginLeft: float = 0.4,
    marginRight: float = 0.4,
    scale: float = 0.9,
    pageRanges: str = "",
    headerTemplate: str = "",
    footerTemplate: str = "",
    preferCSSPageSize: bool = False
):
    # Resolve absolute paths for the MHTML file and output PDF.
    mhtml_path = os.path.abspath(mhtml_file)
    pdf_path = os.path.abspath(pdf_file)
    
    # Configure Chrome options.
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Initialize the Chrome driver.
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(timeout)
    
    try:
        # Load the local MHTML file using a file URI.
        file_uri = "file:///" + mhtml_path.replace("\\", "/")
        driver.get(file_uri)
        
        # Set up the print options for PDF generation.
        print_options = {
            "landscape": landscape,                   # Horizontal layout.
            "printBackground": printBackground,       # Print background graphics.
            "paperWidth": pagesize[0],                # Paper width in inches.
            "paperHeight": pagesize[1],               # Paper height in inches.
            "displayHeaderFooter": displayHeaderFooter,  # Include header/footer.
            "marginTop": marginTop,                   # Top margin.
            "marginBottom": marginBottom,             # Bottom margin.
            "marginLeft": marginLeft,                 # Left margin.
            "marginRight": marginRight,               # Right margin.
            "scale": scale,                           # Scaling factor.
            "pageRanges": pageRanges,                 # Specific pages to print.
            "headerTemplate": headerTemplate,         # HTML template for header.
            "footerTemplate": footerTemplate,         # HTML template for footer.
            "preferCSSPageSize": preferCSSPageSize    # Prefer CSS-defined page size if available.
        }
        
        # Execute the command to render the page as PDF.
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        
        # Decode the base64 PDF data and write it to the output file.
        pdf_data = base64.b64decode(result.get("data", ""))
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)
    finally:
        driver.quit()

# Web Mhtml (specially adjusted versin)
class Website_Mhtml:
    def __init__(self, driver_path: str, headless: bool = True, init_time: int = 5, wait_time: int = 5):
        """
        Initialize the WebsiteDumper class with options for Chrome WebDriver.

        :param driver_path: Path to the Chrome WebDriver executable.
        :param headless: Boolean to determine if the browser should run in headless mode.
        :param wait_time: Time to wait for resources to load (in seconds).
        """
        self.driver_path = driver_path
        self.headless = headless
        self.init_time = init_time
        self.wait_time = wait_time
        self.driver = None
        self.errored_sites = []

    def _setup_driver(self):
        """
        Set up the Selenium WebDriver with Chrome options.
        """
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--save-page-as-mhtml")
        
        service = Service(self.driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def _scroll_to_load_resources(self):
        """
        Scrolls through the webpage step by step to ensure all lazy-loaded resources are loaded.
        """
        scroll_times = 10
        scroll_pause_time = 0.20  # Pause between scrolls (seconds)
        scroll_step = 500  # Number of pixels to scroll by each step
        
        # Scorll down for some times
        for tm in range(scroll_times):
            # Scroll down by a specific step
            self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(scroll_pause_time)  # Pause to allow resources to load
        
        # Scroll up for a specified number of times
        for tm in range(scroll_times):
            # Scroll up by a specific step (negative value for upward scrolling)
            self.driver.execute_script(f"window.scrollBy(0, {-scroll_step});")
            time.sleep(scroll_pause_time)  # Pause to allow resources to adjust
 
    def dump_website(self, url: str, output_path: str, retries: int = 5):
        """
        Dumps the website at the specified URL into an MHTML file.

        :param url: The URL of the website to dump.
        :param output_path: The file path where the MHTML file will be saved.
        :param retries: Number of retry attempts for MHTML capture.
        :raises ValueError: If the URL is invalid or output path is not writable.
        """
        if not url.startswith("http"):
            raise ValueError("Invalid URL. Make sure it starts with 'http' or 'https'.")
        if not os.access(os.path.dirname(output_path), os.W_OK):
            raise ValueError("Output path is not writable.")
        
        attempt = 0
        while attempt < retries:
            try:
                if self.driver is None:
                    self._setup_driver()
                self.driver.get(url)
                
                # Wait for resources
                time.sleep(self.init_time)  # Initial wait for basic resources to load
                
                # Scroll through the page to load all resources
                self._scroll_to_load_resources()
                
                # Wait for resources
                time.sleep(self.wait_time)  # Ending wait for basic resources to load
                
                # Capture the webpage as an MHTML file
                mhtml_data = self.driver.execute_cdp_cmd("Page.captureSnapshot", {"format": "mhtml"})["data"]
                with open(output_path, "wb") as file:
                    file.write(mhtml_data.encode("utf-8"))
                print(f"Website successfully dumped to: {output_path}")
                return  # Exit after successful dump
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(1)  # Small delay before retry
                
        self.errored_sites.append(url)
        # print(f"Failed to dump {url} after {retries} attempts.")

    def close(self):
        """
        Closes the WebDriver if it's running.
        """
        if self.driver:
            self.driver.quit()
            self.driver = None

    @staticmethod
    def dump_websites_in_parallel(driver_path: str, urls_and_paths: list, headless: bool = True, init_time: int = 5, wait_time: int = 5, retries: int = 5, max_workers: int = 4):
        """
        Dumps multiple websites into MHTML files in parallel.

        :param driver_path: Path to the Chrome WebDriver executable.
        :param urls_and_paths: List of tuples (URL, output_path).
        :param headless: Boolean to determine if the browser should run in headless mode.
        :param wait_time: Time to wait for resources to load (in seconds).
        :param retries: Number of retry attempts for each MHTML capture.
        :param max_workers: Maximum number of parallel threads.
        """
        def process_task(url, output_path):
            dumper = Website_Mhtml(driver_path, headless=headless, init_time=init_time, wait_time=wait_time)
            dumper.dump_website(url, output_path, retries=retries)
            dumper.close()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_task, url, output_path) for url, output_path in urls_and_paths]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error during parallel execution: {e}")

# Webdump Class
class Website_Dump:
    
    # Constructor
    def __init__(self, verbose: bool = True, chrome_executable_path: str = default_chorme_path):
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        self.verbose = verbose
        self.backend = Website_Mhtml(chrome_executable_path, headless=True, init_time=0.5, wait_time=0.5)
        self.chrome_executable_path = chrome_executable_path
    
    # Convert mhtml to pdf
    def convert_mhtml_to_pdf(self, mhtml_file, pdf_file):
        convert_mhtml_to_pdf(mhtml_file, pdf_file, self.chrome_executable_path, timeout = 10)
    
    # Save as mhtml and as pdf
    def save_as_pdf(self, url: str, output_file: str):
        
        try:
        
            # Save as mhtml
            # NathMath @ bilibili
            self.backend.dump_website(url, output_file + ".mhtml")
            self.backend.close()
            
            # Convert to pdf
            self.convert_mhtml_to_pdf(output_file + ".mhtml", output_file)
            
            return output_file
            
        except:
            return ""
        
    def auto_save_pdf(self, url: str):
        # Generate datetime
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S")
        
        # Generate folder
        if os.path.exists("./__visits__") == False:
            os.makedirs("./__visits__")
        
        # Generate pdf in ./__visits__
        output_file = "./__visits__/dumped_website_" + now + "_" + sanitize_path_name(url[:64]) + ".pdf"
        
        return self.save_as_pdf(url, output_file)
    
if __name__ == "__main__":
    dumper = Website_Dump(verbose=True)
    test_url = "https://zh.wikipedia.org/zh-sg/%E7%BE%8E%E5%9C%8B%E9%81%8B%E9%80%9A"
    dumper.auto_save_pdf(test_url)
    