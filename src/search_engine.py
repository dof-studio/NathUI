# search_engine.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import re
import requests
import brotli
from urllib.parse import unquote
from bs4 import BeautifulSoup, Comment
from googlesearch import search  # pip install googlesearch-python

from website_dump import Website_Dump

# Global variables defined outside the class
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/92.0.4515.159 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en,zh-CN;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.bing.com/",
    "DNT": "1",  # Do Not Track request
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}
REQUEST_TIMEOUT = 10  # seconds

# Generic Web crawler for search engine
class WebCrawler:
    
    # Constructor
    def __init__(self, verbose: bool = True):
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        self.verbose = verbose
        self.website_dump = Website_Dump()
        pass
    
    # Google search
    def perform_google_search(self, query: str, k: int) -> list:
        """
        Uses the googlesearch module to retrieve the first k search results.
        Assumes that the returned results are organic (non-ad) websites.
        
        return: a list of urls
        """
        urls = []
        try:
            for url in search(query, num_results=k):
                urls.append(url)
                if len(urls) >= k:
                    break
        except Exception as e:
            if self.verbose == False:
                print(f"Error during Google search: {e}")
        return urls
    
    # Bing search
    def perform_bing_search(self, query: str, k: int) -> list:
        """
        Scrapes Bing's search results page to retrieve the first k organic URLs using CSS selectors.
        This version handles potential encoding issues, including Brotli compression.
        
                
        return: a list of urls
        """
        urls = []
        try:
            bing_url = "https://www.bing.com/search"
            params = {"q": query, "count": k}            # By NathMath@bilibili
            response = requests.get(bing_url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                if self.verbose:
                    print(f"Bing search request failed: Status code {response.status_code}")
                return urls

            # Check if the response is Brotli-compressed. Requests normally handles gzip/deflate automatically.
            encoding = response.headers.get("Content-Encoding", "")

            if 'br' in encoding:
                try:
                    decompressed = brotli.decompress(response.content)
                    html_text = decompressed.decode('utf-8', errors='replace')
                except Exception as de:
                    if self.verbose:
                        print("Error decompressing Brotli content:", de)
                    html_text = response.text
            else:
                html_text = response.text

            soup = BeautifulSoup(html_text, "html.parser")
            # Use a CSS selector to target the anchor tags within <h2> inside <li class="b_algo">
            links = soup.select("li.b_algo h2 > a")
            if not links and self.verbose:
                print("No results found with the updated HTML structure. Consider checking the raw HTML.")

            for link in links:
                href = link.get("href")
                if href:
                    urls.append(href)
                    if len(urls) >= k:
                        break
        except Exception as e:
            if self.verbose:
                print(f"Error during Bing search: {e}")
        return urls

    # Yahoo search
    def perform_yahoo_search(self, query: str, k: int) -> list:
        """
        Scrapes Yahoo's search results page to retrieve the first k organic URLs using CSS selectors.
        This version handles potential encoding issues (including Brotli compression) and decodes Yahoo redirection URLs.
        
        return: a list of urls
        """
        urls = []
        try:
            yahoo_url = "https://search.yahoo.com/search"
            params = {"p": query, "n": k}
            response = requests.get(yahoo_url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                if self.verbose:
                    print(f"Yahoo search request failed: Status code {response.status_code}")
                return urls

            encoding = response.headers.get("Content-Encoding", "")
            if 'br' in encoding:
                try:
                    decompressed = brotli.decompress(response.content)
                    html_text = decompressed.decode('utf-8', errors='replace')
                except Exception as de:
                    if self.verbose:
                        print("Error decompressing Brotli content:", de)
                    html_text = response.text
            else:
                html_text = response.text

            soup = BeautifulSoup(html_text, "html.parser")
            # Yahoo's organic search results are typically contained in <div id="web">
            # Each result's title is in an <h3 class="title"> element with an <a> tag.
            links = soup.select("div#web h3.title a")
            if not links and self.verbose:
                print("No results found with the updated HTML structure. Consider checking the raw HTML.")

            for link in links:
                href = link.get("href")
                if href:
                    # Handle Yahoo redirection links correctly.
                    resolved_href = WebCrawler.resolve_yahoo_redirect(href)
                    urls.append(resolved_href)
                    if len(urls) >= k:
                        break
        except Exception as e:
            if self.verbose:
                print(f"Error during Yahoo search: {e}")
        return urls
    
    # API: Crawl a website to get the useful content
    def crawl_website(self, url: str) -> str:
        """
        Fetches the website content from a given URL, extracts the main content,
        cleans it by removing unnecessary tags (scripts, styles, headers, footers,
        navigation, etc.), and returns the cleaned text.
        """
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                if not self.verbose:
                    print(f"Failed to fetch {url}: Status code {response.status_code}")
                return ""
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove HTML comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
    
            # Prefer the <main> tag if available, otherwise fall back to <body>
            container = soup.find("main") or soup.body
            if container is None:
                return ""
            
            # Remove unwanted tags from the container
            for tag in container.find_all([
                "script", "style", "header", "footer", "nav", "aside", 
                "noscript", "iframe", "form"
            ]):
                tag.decompose()
            
            # Extract text and clean up whitespace
            text = container.get_text(separator=' ')
            cleaned_text = " ".join(text.split())
            return cleaned_text
    
        except Exception as e:
            if not self.verbose:
                print(f"Error crawling {url}: {e}")
            return ""
        
    # API: Dump a website into a pdf with automatic name
    def dump_website(self, url: str) -> str:
        """
        Dump a website into a pdf and return the filename.
        """
        return self.website_dump.auto_save_pdf(url)
        
    # API: Search and crawl the first k websites
    def crawl_from_search(self, query: str, k: int, search_engine: str = "bing") -> list:
        """
        Combines search and crawl. Depending on the search_engine parameter,
        it uses either Google or Bing to retrieve URLs, crawls them, and returns a list
        of cleaned text data.
        """
        results = []
        if search_engine.lower() == "bing":
            urls = self.perform_bing_search(query, k)
        elif search_engine.lower() == "yahoo":    
            urls = self.perform_yahoo_search(query, k)
        else:
            # By NathMath@bilibili
            # by default: google search
            urls = self.perform_google_search(query, k)

        for url in urls:
            if self.verbose:
                print(f"Crawling: {url}")
            cleaned_text = self.crawl_website(url)
            if cleaned_text:
                results.append(cleaned_text)
        return results

    # Truncate too long strings
    @staticmethod
    def truncate(content: str, max_len: int = 65536):
        return content[:max_len]
    
    # Concate multiple contents into one single string
    @staticmethod
    def concat(search_result: list, concat_format: str = "###Document No{}\n\n", max_len: int = 65536) -> str:
        """
        Concat the list of string into a single string.
        """
        formated_string = ""
        
        for i in range(len(search_result)):
            formated_string += concat_format.format(i+1) + search_result[i]
            
        return WebCrawler.truncate(formated_string, max_len)

    # Resolve Yahoo redirection links
    @staticmethod
    def resolve_yahoo_redirect(url: str) -> str:
        """
        Checks if the URL is a Yahoo redirection link and extracts the final destination URL from the "RU=" segment.
        If not, returns the original URL.
        """
        # Yahoo redirection URLs typically contain '/RU=<encoded_url>/'.
        match = re.search(r'/RU=([^/]+)/', url)
        if match:
            encoded_url = match.group(1)
            return unquote(encoded_url)
        return url
    

# Test cases to validate the framework
if __name__ == "__main__":
    crawler = WebCrawler()

    query = "latest advancements in artificial intelligence"
    k = 5  # Number of websites to crawl
    
    # Test with Google search
    print("Using Google Search")
    google_data = crawler.crawl_from_search(query, k, search_engine="google")
    for index, content in enumerate(google_data, start=1):
        print(f"\n--- Google Content from Website {index} ---\n")
        print(content[:500] + "\n")  # Print the first 500 characters for brevity

    # Test with Bing search
    print("Using Bing Search")
    bing_data = crawler.crawl_from_search(query, k, search_engine="bing")
    for index, content in enumerate(bing_data, start=1):
        print(f"\n--- Bing Content from Website {index} ---\n")
        print(content[:500] + "\n")  # Print the first 500 characters for brevity
        
    # Test with Yahoo search
    print("Using Yahoo Search")
    yahoo_data = crawler.crawl_from_search(query, k, search_engine="yahoo")
    for index, content in enumerate(yahoo_data, start=1):
        print(f"\n--- Yahoo Content from Website {index} ---\n")
        print(content[:500] + "\n")  # Print the first 500 characters for brevity
        