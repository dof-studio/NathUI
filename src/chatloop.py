# chatloop.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# Please install OpenAI SDK first: `pip3 install openai`

import itertools
import pickle
import json
import shutil
import os
import sys
import threading
import time
import pandas as pd
import urllib.parse
import urllib.request

from openai import OpenAI
from typing import Any, List, Dict, Optional

import debug
import params
from buffer import Buffer
from strutil import str_unquote
from search_engine import WebCrawler
from visitor import is_file, file_visitor
from filewalker import FileWalker
from mkdown_renderer import go_renderer
from sqlite import SQLiteClient, QueryExecutionError
from sqparse import SQLiteParser
from dethink import think_output_split as tos
from debug import nathui_global_debug, nathui_global_lang
from func_defaults import WEB_SEARCH_TOOL, web_search_on_internet
from func_defaults import DATA_VISITOR_TOOL, data_visitor_online_or_local
from func_defaults import FILE_OPENER_TOOL, local_file_opener
from func_defaults import PYTHON_EXECTUTE_TOOL, python_code_executor

# Legacy definition, will be removed in the future
messages = []
responses = []

# Legacy Function to search on wikipedia
def fetch_wikipedia_content(search_query:str) -> dict:
    """
    Fetches wikipedia content for a given search_query
    """
    
    try:
        # Search for most relevant article
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_query,
            "srlimit": 1,
        }

        url = f"{search_url}?{urllib.parse.urlencode(search_params)}"
        with urllib.request.urlopen(url) as response:
            search_data = json.loads(response.read().decode())

        if not search_data["query"]["search"]:
            return {
                "status": "error",
                "message": f"No Wikipedia article found for '{search_query}'",
            }

        # Get the normalized title from search results
        normalized_title = search_data["query"]["search"][0]["title"]

        # Now fetch the actual content with the normalized title
        content_params = {
            "action": "query",
            "format": "json",
            "titles": normalized_title,
            "prop": "extracts",
            "exintro": "true",
            "explaintext": "true",
            "redirects": 1,
        }

        url = f"{search_url}?{urllib.parse.urlencode(content_params)}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        pages = data["query"]["pages"]
        page_id = list(pages.keys())[0]

        if page_id == "-1":
            return {
                "status": "error",
                "message": f"No Wikipedia article found for '{search_query}'",
            }

        content = pages[page_id]["extract"].strip()
        return {
            "status": "success",
            "content": content,
            "title": pages[page_id]["title"],
        }

    except Exception as e:
        return {"status": "error", "message": "Wiki searching error: " + str(e)}


# Template wiki tool
WIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_wikipedia_content",
        "description": (
            "Search Wikipedia and fetch the introduction of the most relevant article. "
            "Always use this if the user is asking explicitly for searching on wikipedia. "
            "If the user has a typo in their search query, correct it before searching."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Search query for finding the Wikipedia article",
                },
            },
            "required": ["search_query"],
        },
    },
}


# Class for displaying the state of model processing
class Spinner:
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.busy = False
        self.delay = 0.1
        self.message = message
        self.thread = None

    def write(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def _spin(self):
        while self.busy:
            self.write(f"\r{self.message} {next(self.spinner)}")
            time.sleep(self.delay)
        self.write("\r\033[K")  # Clear the line

    def __enter__(self):
        self.busy = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.busy = False
        time.sleep(self.delay)
        if self.thread:
            self.thread.join()
        self.write("\r")  # Move cursor to beginning of line


# Modern chatloop class, processing and interacting with the backend
class Chatloop:
    
    # Export Data (static)
    @staticmethod
    def _export_data(data, filepath) -> bool:
        try:
            directory = os.path.dirname(filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            return False
        
    # Import Data (static)
    @staticmethod
    def _import_data(filepath, default=None) -> any:
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return default
        except Exception as e:
            return default   
    
    # Init
    def __init__(self, webcrawler = WebCrawler(), use_external: None | str | Any = None):

        # Define system prompt
        if nathui_global_lang == "CN":
            system_prompt = params.nathui_backend_default_sysprompt_CN
        else:
            system_prompt = params.nathui_backend_default_sysprompt_EN
        
        # Ongoing chat
        self.ongoing = False
        
        # Construct modelling
        self.model = params.nathui_backend_model
        self.client = OpenAI(base_url = params.nathui_backend_url + "/v1", 
                        api_key = params.nathui_backend_apikey)
        
        # System prompt
        self.system_prompt = system_prompt
        
        # Inference Params
        self.infer_param = {
                "temperature": 0.5,
                "max_tokens": 4096,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0
                }
        
        # Generating with tool calls or not
        self.use_tools = False
        
        # Supported tools
        # Can be customized and appended by calling 
        # self.append_supported_tools
        self.tools = [
            WEB_SEARCH_TOOL, # Official tool NathUI supports
                             # search on the internet to get realtime data (non-cached)
            DATA_VISITOR_TOOL, # Official tool NathUI supports
                               # visit an online or local address to fetch data
            FILE_OPENER_TOOL,  # Official tool NathUI supports
                               # open a local file by its path
            PYTHON_EXECTUTE_TOOL, # Official tool NathUI supports
                                  # run a generated or given python tool
            ]
        self.tool_dict = {
            "web_search_on_internet"  : web_search_on_internet,
            "data_visitor_online_or_local": data_visitor_online_or_local,
            "local_file_opener" : local_file_opener,
            "python_code_executor": python_code_executor,
            }
        
        # Web crawler
        self.webcrawler = webcrawler

        # Search Engine
        self.search_engine = params.nathui_backend_default_search_engine
        
        # SQLite parameters
        self.default_table = "user_primary"
        self.sqlite_client = SQLiteClient("./__database__/user_database.db")
        self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
        self.sqlite_version = self.sqlite_parser.version
        self.search_no = params.nathui_backend_search_no
        self.__author__ = "DOF-Studio/NathMath@bilibili"
        self.__license__ = "Apache License Version 2.0"
        
        # visit cache (dictionary)
        self.visit_cache = {}
        
        # search cache (dictionary)
        self.search_cache = {}
        
        # command line buffer
        self.command_buffer = Buffer()
        
        # a renderer api function
        self.use_external = use_external 
        
        # chatting round
        self.round_number = 0
        
        # Realtime string returned by the backend
        self.collected_content = ""
        
        # Responses (tuple: tool_calls, message)
        self.responses = []
        
        # Chat history with actual input/output when using functions
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Chat history that will be displayed to the user (without showing funcion details)
        self.original_messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Default visit prompt
        if nathui_global_lang == "CN":
            self.visit_prompt = "请根据我提供的文档或者网页来回答用户提出的问题，使用Markdown输出。 文档可能较为混杂，请深度思考并提炼有用的内容。 "
        else:
            self.visit_prompt = "Giventhe following document or website that the user provided, answer in detail and answer the question using Markdown. The document may be confusing and unformatted, please think deeply and extract useful content."
        
        # Default search prompt
        if nathui_global_lang == "CN":
            self.search_prompt = "详细总结下面的内容来回答用户提出的问题，使用Markdown输出。 忽略你无法分析的文档。 "
        else:
            self.search_prompt = "Summarize the following content in detail and answer the question using Markdown. Ignore documents you cannot read. "
    
    # Display Introduction
    def display_intro(self, print_device = print):
        # Display usage. Only in debug mode
        if nathui_global_debug == True:
            if nathui_global_lang == "CN":
                if str(print_device) == str(print):
                    print_device("AI助理: ", end="")
                print_device(r"你好，我是你的私人AI助理. 今天我能如何帮助你呢，我的主人？@NathMath Nath-UI")
                print_device(r"特殊的指令将列举如下")
                print_device(r"键入 '\quit' 以结束对话")
                print_device(r"键入 '\syntax' 以打印这个介绍")
                print_device(r"键入 '\delete' 以删除上一轮的聊天内容")
                print_device(r"键入 '\deleteall' 以删除本次聊天的所有轮的聊天内容")
                print_device(r"键入 '\toolcall' 以启用或禁用工具调用(需要模型支持)")
                # deprecated
                # print_device(r"键入 '\visit `...`' 以访问网站地址或者本地文件")
                print_device(r"键入 '\visit `...`  \visit `prompt`' 以访问网站地址或者本地文件并将`prompt`内容设置为访问问答提示词")
                # deprecated
                # print_device(r"键入 '\search `...`' 以使用搜索功能进行检索")
                print_device(r"键入 '\search `...` \search `prompt`' 以使用搜索功能进行检索并将`prompt`内容设置为搜素问答提示词")
                print_device(r"键入 '\locate `dbpath` \locate `table`' 以连接一个新的外部SQLite数据库文件`dbpath`的表`table`")
                print_device(r"键入 '\connect' 以连接默认的数据库，如果不存在那么会创建")
                print_device(r"键入 '\connect `table` \connect' 以连接给定的数据库`table`，如果不存在那么会创建")
                print_device(r"键入 '\insert `...` \insert `data`' 以向当前数据库新增主键为`...`的数据`data`")
                print_device(r"键入 '\update `...` \update `data`' 以向当前数据库修改主键为`...`的数据`data`")
                print_device(r"键入 '\query `...` \query `prompt`' 从当前数据库以标准SQL语法获取数据，并将`prompt`内容设置为数据库访问问答提示词")
                print_device(r"键入 '\select `...` \select `prompt`' 从当前数据库以DSL语法获取数据，并将`prompt`内容设置为数据库访问问答提示词")
                
            else:  
                if str(print_device) == str(print):
                    print_device("Assistant: ", end="")
                print_device(r"Hi! I am your private AI assistant. How can I help you, my master? @NathMath Nath-UI")
                print_device(r"Special Commands are listed below")
                print_device(r"Type '\quit' to exit")
                print_device(r"Type '\syntax' to print this welcome again")
                print_device(r"Type '\delete' to delete the previous chat content in the last round")
                print_device(r"Type '\deleteall' to delete all of the previous chat contents")
                print_device(r"Type '\toolcall' to enable or disable the tool (requires model support)")
                # deprecated
                # print_device(r"Type '\visit `...`' to visit the website or local file, read the content and response")
                print_device(r"Type '\visit `...`  \visit `prompt`' to visit the website or local file, read the content and response, setting `prompt` as visit prompt")
                # deprecated
                # print_device(r"Type '\search `...`' to search ... on the internet'")
                print_device(r"Type '\search `...` \search `prompt`' to search `...` on the internet and set `prompt` as your search prompt")
                print_device(r"Type '\locate `dbpath` \locate `table`' to locate to a table `table` of a new external SQLite database file named `dbpath`")
                print_device(r"Type '\connect' to connect to the default database, and create it if it does not exist")
                print_device(r"Type '\connect `table` \connect' to connect to the given database `table`, which will be created if it does not exist")
                print_device(r"Type '\insert `...`  \insert `data`' to add data `data` with primary key `...` to the current database")
                print_device(r"Type '\update `...`  \update `data`' to update data `data` with primary key `...` to the current database")
                print_device(r"Type '\query `...` \query `prompt`' to get data from the current database using standard SQL syntax, and set the `prompt` content to the database access question prompt")
                print_device(r"Type '\select `...`  \select `prompt`' to get data from the current database using DSL syntax, and set the `prompt` content to the database access question prompt")
            
            return None
        
    # Fetch loaded model names
    def fetch_loaded_models(self) -> list:
        # Retrieve the list of available models from the OpenAI API
        models_response = self.client.models.list()
        model_list = []
        for model in list(models_response):
            model_list.append(model.id)
        return model_list
        
    # Reattach to a new model
    def reattach_new_model(self, new_model, base_url = params.nathui_backend_url, api_key = params.nathui_backend_apikey):
        self.model = new_model
        self.client = OpenAI(base_url = base_url + "/v1", 
                        api_key = api_key)
        
    # Reset whether to use tools or not
    def reset_use_tool(self, use_tool_bool: bool = False) -> None:
        if isinstance(use_tool_bool, bool):
            self.use_tools = use_tool_bool
        return None
        
    # Append tools to support (call reset_use_tool before querying)
    def append_supported_tools(self, appended_list: List[Dict], func_name_list: List[str], func_list: List) -> None:
        if isinstance(appended_list, list):
            for i in range(len(appended_list)):
                self.tools.append(appended_list[i])
                self.tool_dict[func_name_list[i]] = func_list[i]
        return None
                
    # Clear lastround history
    def clear_lastround(self, keep_system_prompt: bool = True) -> None:
        
        # Reset system prompts

        # Clear last response
        if len(self.responses) > 0:
            self.responses = self.responses[0:-1]

        # Chat history with actual input/output when using functions
        if len(self.messages) > 1:
            # 1 for system prompt
            mlen = len(self.messages)
            nwlen = 1
            for i in range(mlen - 1, -1, -1):
                if self.messages[i]["role"] != "user":
                    continue
                else:
                    nwlen = i
                    break
            self.messages = self.messages[0:nwlen]
        
        # Chat history that will be displayed to the user (without showing funcion details)
        if len(self.original_messages) > 1:
            # 1 for system prompt
            mlen = len(self.original_messages)
            nwlen = 1
            for i in range(mlen - 1, -1, -1):
                if self.original_messages[i]["role"] != "user":
                    continue
                else:
                    nwlen = i
                    break
            self.original_messages = self.original_messages[0:nwlen]
        
    # Clear chatting history
    def clear_messages(self, keep_system_prompt: bool = True) -> None:
        
        # Reset system prompts
        # Define system prompt
        if nathui_global_lang == "CN":
            self.system_prompt = params.nathui_backend_default_sysprompt_CN
        else:
            self.system_prompt = params.nathui_backend_default_sysprompt_EN
        
        # Clear all responses
        self.responses = []

        # Chat history with actual input/output when using functions
        if keep_system_prompt:
            self.messages = [
                {"role": "system", "content": self.system_prompt}
            ]
        else:
            self.messages = []
        
        # Chat history that will be displayed to the user (without showing funcion details)
        if keep_system_prompt:
            self.original_messages = [
                {"role": "system", "content": self.system_prompt}
            ]
        else:
            self.original_messages = []
        
    # Clear caches
    def clear_caches(self) -> None:
        self.search_cache = {}
        self.visit_cache = {}
        
    # Export chatting history
    def save_messages(self, path: str | None) -> bool | list:
        if path is not None:
            return self._export_data(["NathUI~Savefile~", self.messages, self.original_messages, self.responses], path)
        else:
            return ["NathUI~Savefile~", self.messages, self.original_messages, self.responses]
    
    # Import chatting history
    def load_messages(self, path_or_obj: str | object) -> list:
        
        if isinstance(path_or_obj, str):
            path = path_or_obj
            message_list = self._import_data(path)
            if message_list is not None:
                if message_list[0] == "NathUI~Savefile~":
                    self.messages = message_list[1]
                    self.original_messages = message_list[2]
                    self.responses = message_list[3]
            # Otherwise, do nothing
            return self.messages
        else:
            message_list = path_or_obj
            if message_list[0] == "NathUI~Savefile~":
                self.messages = message_list[1]
                self.original_messages = message_list[2]
                self.responses = message_list[3]
            # Otherwise, do nothing
            return self.messages
        
    # System prompt Getter
    def system_prompt_get(self) -> str:
        '''
        Return a copy of the current system prompt.
        '''
        return self.system_prompt.strip()
    
    # System prompt Setter
    def system_prompt_set(self, new_system_prompt:str) -> str:
        '''
        Set current system prompt with a new one.
        '''
        self.system_prompt = new_system_prompt.strip()
        return self.system_prompt.strip()
        
    # Inference parameters Getter
    def infer_params_get(self) -> dict:
        '''
        Return a copy of the current inference parameters.
        '''
        return self.infer_param.copy()
        
    # Inference parameters Setter
    def infer_params_set(self, param_dict: dict) -> dict:
        '''
        Set current inference parameters with new values
        '''
        for key in param_dict.keys():
            if self.infer_param.get(key, None) is not None:
                self.infer_param[key] = param_dict[key]
            else:
                # Not allowed to add other params
                pass
        return self.infer_param.copy()
    
    # Handle visit
    def handle_visit(self, splited:str, visit_command:str | None = None) -> str | None:
        '''
        Handle visit commands for all conditions.
        @ visit_command: reserved for future use.
        '''
        
        # Unquote and strip if necessary
        # : Really important or it will give an error
        # : By NathMath at platform bilibili
        splited = str_unquote(splited.strip()) # correct sequence of calling
        
        # Get type
        content_type = is_file(splited)
        
        # If a file, read it
        if content_type == 1:
            # Note, pdf DOES NOT support OCR
            # @todo
            # Use another model like qwen2.5-vl to handle OCR in 
            # the future
            if self.visit_cache.get(splited) is not None:
                # cached
                file_content = self.visit_cache.get(splited)
            else:
                file_content = file_visitor(splited, as_markdown=True)
                self.visit_cache[splited] = file_content
            return file_content
        
        # If a url, visit it
        elif content_type == 2:
            # Method 1
            # Dump the website into pdf and view
            # website_pdf_path = self.webcrawler.dump_website(splited)
            # return file_visitor(website_pdf_path, as_markdown=False)
            # something like this
            
            # Method 2
            # Just crawl the website (much faster!)
            if self.visit_cache.get(splited) is not None:
                # cached
                web_content = self.visit_cache.get(splited)
            else:
                web_content = self.webcrawler.crawl_website(splited)
                self.visit_cache[splited] = web_content
            return web_content
        
        # If a folder, get the table of its immediate content
        elif content_type == 3:
            # Get the information of the content in the folder
            if self.visit_cache.get(splited) is not None:
                # cached
                fdr_content = self.visit_cache.get(splited)
            else:
                nath_walker = FileWalker(splited, 1)
                nath_structure = nath_walker.traverse()
                nath_dataframe = nath_walker.get_pd_dataframe(nath_structure)
                # Columns to fetch may be subject to change in the future
                nath_columns = ["path", "type", "size"] # "modification_time"
                nath_dataframe = nath_dataframe[nath_columns]
                # Combine into plaintext
                fdr_content = ""
                for i in range(nath_dataframe.shape[0]):
                    fdr_content += "'" + nath_dataframe["path"].iloc[i] + "', "
                    fdr_content += str(nath_dataframe["type"].iloc[i]) + ", "
                    fdr_content += str(nath_dataframe["size"].iloc[i]) + "\n"                
                # Cache it
                self.visit_cache[splited] = fdr_content
                
            return fdr_content
        
        # Else, abort with None
        else:
            return None
    
    # Handle sqlite locate requests
    def handle_locate(self, dbfilepath:str, table_name:str, catch_except:bool = True) -> None:
        '''
        Handle relotating requests to an external SQLite database.
        @catch_except: always left to be True please.
        '''
        # Strip
        dbfilepath = str_unquote(dbfilepath.strip()) 
        table_name = str_unquote(table_name.strip()) 
        
        # Initialize the relocated database first
        if os.path.exists(dbfilepath) == False:
            self.handle_error(f"Database file {dbfilepath} does not exist.")
        try:
            self.default_table = table_name
            self.sqlite_client = SQLiteClient(dbfilepath)
            self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
        except QueryExecutionError as e:
            # This means table already exists
            if catch_except:
                pass
            else:
                raise
        
        # Connect to or creating a new table then
        try:
            self.sqlite_parser.create_table(
                table_name = table_name.strip(),
                columns = [
                    {"name": "key",     "type": str, "primary": True},
                    {"name": "content", "type": str},
                    {"name": "version", "type": int}
                ],
                safemode = False)
        except QueryExecutionError as e:
            # This means table already exists
            if catch_except:
                pass
            else:
                raise
        return
    
    # Handle sqlite connect requests
    def handle_connect(self, table_name:str, catch_except:bool = True) -> None:
        '''
        Handle connecting requests to SQLite database.
        @catch_except: always left to be True please.
        '''
        
        # If table existing, return
        # If table non-existing, create a standard 
        # {key: str, value: str, version: int} table
        try:
            self.sqlite_parser.create_table(
                table_name = table_name.strip(),
                columns = [
                    {"name": "key",     "type": str, "primary": True},
                    {"name": "content", "type": str},
                    {"name": "version", "type": int}
                ],
                safemode = False)
        except QueryExecutionError as e:
            # This means table already exists
            if catch_except:
                pass
            else:
                raise
        return
    
    # Handle sqlite insert requests
    def handle_insert(self, row_data: list | dict, catch_except:bool = True) -> None:
        '''
        Handle inserting requests to SQLite database.
        @catch_except: always left to be True please.
        '''
        
        # If table existing, return
        # If table non-existing, create a standard 
        # {key: str, value: str, version: int} table
        try:
            self.sqlite_parser.insert(
                data=row_data,
                table_name=self.default_table)
            
        # @todo, to identify more specific error types
        except Exception as e:
            # This means data already exists
            if catch_except:
                pass
            else:
                raise
        return
    
    # Handle sqlite update requests
    def handle_update(self, row_data: list | dict, catch_except:bool = True) -> None:
        '''
        Handle updatinging requests to SQLite database.
        @catch_except: always left to be True please.
        '''
        
        # If table existing, return
        # If table non-existing, create a standard 
        # {key: str, value: str, version: int} table
        try:
            self.sqlite_parser.update(
                data=row_data,
                table_name=self.default_table)
            
        # @todo, to identify more specific error types
        except Exception as e:
            # This means data already exists
            if catch_except:
                pass
            else:
                raise
        return
    
    # Handle sqlite select requests
    def handle_select(self, query: str, to_markdown:bool = False, catch_except:bool = True) -> str:
        '''
        Handle selecting requests to SQLite database.
        @to_markdown: to convert markdown or plaintext.
        @catch_except: always left to be True please.
        '''
        # If table existing, return
        # If table non-existing, create a standard 
        # {key: str, value: str, version: int} table
        data = ""
        try:
            data = self.sqlite_parser.select(query)
            data = self.sqlite_parser.to_pandas(data)
            
            # Single content
            if data.shape[0] == 1:
                return str(data["content"].iloc[0])
            
            # Multiple content
            else:
                if to_markdown:
                    return str(data["content"].to_markdown())
                else:
                    plaintext = ""
                    for i in range(data.shape[0]):
                        plaintext += data["key"].iloc[i] + ": "
                        plaintext += data["content"].iloc[i] + "\n\n\n"
                    return plaintext
            
        # @todo, to identify more specific error types
        except Exception as e:
            # This means data already exists
            if catch_except:
                pass
            else:
                raise
        return data
    
    # Handle sqlite query requests
    def handle_query(self, query: str, to_markdown:bool = False, catch_except:bool = True) -> str | None:
        '''
        Handle custom SELECT requests to SQLite database.
        @to_markdown: to convert markdown or json.
        @catch_except: always left to be True please.
        '''
        # strip query
        query = query.strip()
        
        # SELECT query? return something
        if query.upper().startswith("SELECT"):
            # If table existing, return
            # If table non-existing, create a standard 
            # {key: str, value: str, version: int} table
            data = ""
            try:
                data = self.sqlite_client.fetch_all(query, ())
                data = self.sqlite_parser.to_pandas(data)

                # No 'content' restriction
                if to_markdown:
                    return str(data.to_markdown())
                else:
                    return str(data.to_json())
                
            except QueryExecutionError as e:
                # This means data already exists
                if catch_except:
                    pass
                else:
                    raise
            return data
        
        # NON-SEKECT query? return None and needs additional process
        else:
            try:
                self.sqlite_client.execute(query, ())
            except QueryExecutionError as e:
                # This means data already exists
                if catch_except:
                    pass
                else:
                    raise
            return None
    
    # General logic to handle special commands
    def handle_special_commands(self, user_input) -> str | dict | None:
        
        # must clear the input
        user_input = user_input.strip()
        
        # must handle special escape r"\\\\" into r"\"
        user_input = user_input.replace(r"\\\\", "\\\\")
        
        # must clear the command buffer
        self.command_buffer._clear()
        
        # Quit
        if user_input.lower() == r"\quit" or user_input.lower() == r"\\quit":
            if nathui_global_debug == True:
                print("User quitted") # Nath UI
            return None
        
        # Syntax
        elif user_input.lower() == r"\syntax" or user_input.lower() == r"\\syntax":
            self.display_intro(print_device=self.command_buffer._print)
            return {r"\usage": r"\syntax"}
        
        # It is a FREE and OPEN SOURCED software
        # See github.com/dof-studio/NathUI
            
        # Delete
        elif user_input.lower() == r"\delete" or user_input.lower() == r"\\delete":
            if nathui_global_debug == True:
                print("User deleted")
            if len(self.messages) > 1:
                self.messages = self.messages[:1]
                self.original_messages = self.original_messages[:1]
            return {r"\usage": r"\delete"}
                
        # Delete all
        elif user_input.lower() == r"\deleteall" or user_input.lower() == r"\\deleteall":
            if nathui_global_debug == True:
                print("User deleted all") # Nath UI
            self.messages = [self.messages[0]]
            self.original_messages = [self.original_messages[0]]
            return {r"\usage": r"\deleteall"}
        
        # Enabling or Disabling toolcall
        elif user_input.lower() == r"\toolcall" or user_input.lower() == r"\\toolcall":
            if nathui_global_debug == True:
                print("User switched toolcall to " + str(not self.use_tools)) # Nath UI
            self.use_tools = not self.use_tools
            return {r"\usage": r"\toolcall", r"\result": str(self.use_tools)}
        
        # Visit without prompt
        elif user_input.lower().startswith(r"\visit") and user_input.lower().find(r"\visit", 6) < 0:
            # Get everything left as the search query
            visit_query = user_input[7:].strip()
            
            # Get the visited content from requests
            user_input = self.handle_visit(visit_query, None)
            if user_input is None:
                # Invalid input
                return {}
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : visit_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Visit Content")
            # NathMath@bili+bili ~ DOF-S?tudio!
            return self.visit_prompt + visit_query + "? " + user_input + "{Document} : " + user_input
        
        # Visit without prompt
        elif user_input.lower().startswith(r"\\visit") and user_input.lower().find(r"\\visit", 7) < 0:
            # Get everything left as the search query
            visit_query = user_input[8:].strip()
            
            # Get the visited content from requests
            user_input = self.handle_visit(visit_query, None)
            if user_input is None:
                # Invalid input
                return {}
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : visit_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Visit Content")
            # NathMath@bili+bili ~ DOF-S?tudio!
            return self.visit_prompt + visit_query + "? " + user_input + "{Document} : " + user_input
        
        # Visit with custom prompt
        elif user_input.lower().startswith(r"\visit") and user_input.lower().find(r"\visit", 6) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, visit_query, custom_prompt = user_input.split(r"\visit")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Get the visited content from requests
            user_input = self.handle_visit(visit_query, None)
            if user_input is None:
                # Invalid input
                return {}
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : visit_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Visit Content")
            return custom_prompt + visit_query + "? " + user_input + "{Document} : " + user_input
        
        # Visit with custom prompt
        elif user_input.lower().startswith(r"\\visit") and user_input.lower().find(r"\\visit", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, visit_query, custom_prompt = user_input.split(r"\\visit")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Get the visited content from requests
            user_input = self.handle_visit(visit_query, None)
            if user_input is None:
                # Invalid input
                return {}
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : visit_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Visit Content")
            return custom_prompt + visit_query + "? " + user_input + "{Document} : " + user_input
         
        # Search without prompt
        elif user_input.lower().startswith(r"\search") and user_input.lower().find(r"\search", 7) < 0:
            # Get everything left as the search query
            search_query = user_input[7:].strip()
            
            # Get the searched data in a str
            clean_query = str_unquote(search_query.strip())
            
            # First try cache
            if self.search_cache.get(clean_query) is not None and len(clean_query) > 0:
                user_input = self.search_cache[clean_query]
            # Cache unhit
            else:
                user_input = self.webcrawler.crawl_from_search(clean_query, search_engine= self.search_engine, k = self.search_no)
                self.search_cache[clean_query] = user_input
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : search_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Search Content")
            return self.search_prompt + clean_query + "? " + self.webcrawler.concat(user_input)
        
        # Search without prompt
        elif user_input.lower().startswith(r"\\search") and user_input.lower().find(r"\\search", 8) < 0:
            # Get everything left as the search query
            search_query = user_input[8:].strip()
            
            # Get the searched data in a str
            clean_query = str_unquote(search_query.strip())
            
            # First try cache
            if self.search_cache.get(clean_query) is not None and len(clean_query) > 0:
                user_input = self.search_cache[clean_query]
            # Cache unhit
            else:
                user_input = self.webcrawler.crawl_from_search(clean_query, search_engine= self.search_engine, k = self.search_no)
                self.search_cache[clean_query] = user_input
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : search_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Search Content")
            return self.search_prompt + clean_query + "? " + self.webcrawler.concat(user_input)
        
        # Search with custom prompt
        elif user_input.lower().startswith(r"\search") and user_input.lower().find(r"\search", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, search_query, custom_prompt = user_input.split(r"\search")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Get the searched data in a str
            clean_query = str_unquote(search_query.strip())
            
            # First try cache
            if self.search_cache.get(clean_query) is not None and len(clean_query) > 0:
                user_input = self.search_cache[clean_query]
            # Cache unhit
            else:
                user_input = self.webcrawler.crawl_from_search(clean_query, search_engine= self.search_engine, k = self.search_no)
                self.search_cache[clean_query] = user_input
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : search_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Search Content")
            return custom_prompt + clean_query + "? " + self.webcrawler.concat(user_input)
        
        # Search with custom prompt
        elif user_input.lower().startswith(r"\\search") and user_input.lower().find(r"\\search", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, search_query, custom_prompt = user_input.split(r"\\search")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Get the searched data in a str
            clean_query = str_unquote(search_query.strip())
            
            # First try cache
            if self.search_cache.get(clean_query) is not None and len(clean_query) > 0:
                user_input = self.search_cache[clean_query]
            # Cache unhit
            else:
                user_input = self.webcrawler.crawl_from_search(clean_query, search_engine= self.search_engine, k = self.search_no)
                self.search_cache[clean_query] = user_input
            
            if nathui_global_debug == True:
                self.display_interim_content({
                    "status" : "success",
                    "title" : search_query,
                    "content" : user_input,
                    "message" : ""
                    }, name = "Search Content")
            return custom_prompt + clean_query + "? " + self.webcrawler.concat(user_input)
        
        # Connect to an external SQLite database
        elif user_input.lower().startswith(r"\locate") and user_input.lower().find(r"\locate", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, dbfilepath, table_name = user_input.split(r"\locate")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try locating
            self.handle_locate(dbfilepath, table_name)
            
            # Process connection
            return {r"\usage": r"\locate", "to": dbfilepath+"->"+table_name}
        
        # Connect to an external SQLite database
        elif user_input.lower().startswith(r"\\locate") and user_input.lower().find(r"\\locate", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, dbfilepath, table_name = user_input.split(r"\\locate")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try locating
            self.handle_locate(dbfilepath, table_name)
            
            # Process connection
            return {r"\usage": r"\locate", "to": dbfilepath+"->"+table_name}
        
        # Connect to default local database
        elif user_input.lower().startswith(r"\connect") and user_input.lower().find(r"\connect", 8) < 0:
            
            # Try connecting to default database
            self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
            
            # Process connection
            self.handle_connect(self.default_table, True)
            return {r"\usage": r"\connect", "to": self.default_table}
        
        # Connect to default local database
        elif user_input.lower().startswith(r"\\connect") and user_input.lower().find(r"\\connect", 9) < 0:
            
            # Try connecting to default database
            self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
            
            # Process connection
            self.handle_connect(self.default_table, True)
            return {r"\usage": r"\connect", "to": self.default_table}
        
        # Connect to a custom local database
        elif user_input.lower().startswith(r"\connect") and user_input.lower().find(r"\connect", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, custom_table_name, end_nothing = user_input.split(r"\connect")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try connecting to the local database
            self.default_table = custom_table_name.strip()
            self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
            
            # Process connection
            self.handle_connect(self.default_table, True)
            return {r"\usage": r"\connect", "to": self.default_table}
        
        # Connect to a custom local database
        elif user_input.lower().startswith(r"\\connect") and user_input.lower().find(r"\\connect", 9) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, custom_table_name, end_nothing = user_input.split(r"\\connect")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try connecting to the local database
            self.default_table = custom_table_name.strip()
            self.sqlite_parser = SQLiteParser(self.sqlite_client, self.default_table)
            
            # Process connection
            self.handle_connect(self.default_table, True)
            return {r"\usage": r"\connect", "to": self.default_table}
        
        # Insert a new record to the local database
        elif user_input.lower().startswith(r"\insert") and user_input.lower().find(r"\insert", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, pkey, content = user_input.split(r"\insert")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try to insert a new record
            self.handle_insert(
                [
                    {"key": str(pkey).strip(), "content": str(content).strip(), "version": int(self.sqlite_version)}    
                ])
            
            return {r"\usage": r"\insert", "key": pkey}
        
        # Insert a new record to the local database
        elif user_input.lower().startswith(r"\\insert") and user_input.lower().find(r"\\insert", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, pkey, content = user_input.split(r"\\insert")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try to insert a new record
            self.handle_insert(
                [
                    {"key": str(pkey).strip(), "content": str(content).strip(), "version": int(self.sqlite_version)}    
                ])
            
            return {r"\usage": r"\insert", "key": pkey}
        
        # Update with a new record to the local database
        elif user_input.lower().startswith(r"\update") and user_input.lower().find(r"\update", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, pkey, content = user_input.split(r"\update")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try to insert a new record
            self.handle_update(
                [
                    {"key": str(pkey).strip(), "content": str(content).strip(), "version": int(self.sqlite_version)}    
                ])
            
            return {r"\usage": r"\update", "key": pkey}
        
        # Update with a new record to the local database
        elif user_input.lower().startswith(r"\\update") and user_input.lower().find(r"\\update", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, pkey, content = user_input.split(r"\\update")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # Try to insert a new record
            self.handle_update(
                [
                    {"key": str(pkey).strip(), "content": str(content).strip(), "version": int(self.sqlite_version)}    
                ])
            
            return {r"\usage": r"\update", "key": pkey}
        
        # Select an existing record from the local database
        elif user_input.lower().startswith(r"\select") and user_input.lower().find(r"\select", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, select_clause, prompt = user_input.split(r"\select")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # the internal parser will handle all of this
            select_query = r"\select " + select_clause.strip() + r" \select"
            
            # Try to select from the database
            try:
                selected = self.handle_select(select_query)

                return "[Answer Question]" + prompt + " based on [Document for Reference] " + selected
            except Exception as e:
                self.handle_error(e)
                return {}
        
        # Select an existing record from the local database
        elif user_input.lower().startswith(r"\\select") and user_input.lower().find(r"\\select", 8) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, select_clause, prompt = user_input.split(r"\\select")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # the internal parser will handle all of this
            # Keeps the same
            select_query = r"\select " + select_clause.strip() + r" \select"
            
            # Try to select from the database
            try:
                selected = self.handle_select(select_query)

                return "[Answer Question]" + prompt + " based on [Document for Reference] " + selected
            except Exception as e:
                self.handle_error(e)
                return {}
        
        # Query custom requesting to the local database
        elif user_input.lower().startswith(r"\query") and user_input.lower().find(r"\query", 6) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, query_clause, prompt = user_input.split(r"\query")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # the internal query is what is is
            select_query = query_clause.strip()
            
            # Try to select from the database
            try:
                selected = self.handle_query(select_query)
                
                # If a non-select query
                if selected is None:
                    return {r"\usage": r"\query", "query": select_query}
                
                # NathMath@bilibili and DOF Studio!
                return "[Answer Question]" + prompt + " based on [Document for Reference] " + selected
            except Exception as e:
                self.handle_error(e)
                return {}
        
        # Query custom requesting to the local database
        elif user_input.lower().startswith(r"\\query") and user_input.lower().find(r"\\query", 7) > 0:
            # belike 
            # r"\visit https:/1.html \visit alrady".split(r"\visit")
            # Out[66]: ['', ' https:/1.html ', ' alrady']
            try:
                nothing, query_clause, prompt = user_input.split(r"\\query")
            except:
                self.handle_error(f"Invalid prompt: {user_input}")
                return {}
            
            # the internal query is what is is
            select_query = query_clause.strip()
            
            # Try to select from the database
            try:
                selected = self.handle_query(select_query)
                
                # If a non-select query
                if selected is None:
                    return {r"\usage": r"\query", "query": select_query}
                
                # NathMath@bilibili and DOF Studio!
                return "[Answer Question]" + prompt + " based on [Document for Reference] " + selected
            except Exception as e:
                self.handle_error(e)
                return {}
        
        return user_input
    
    # Convert NathUI chatbrowser chat history to the internal type
    def convert_external_chat_history(self, standard_external_history: list) -> bool | None:
        '''
        Convert external chat history into chatloop type and
        1. convert commands to actual data
        2. load into the backend
        Standard chatting history: List_obj[index][role] = message
        '''
        
        # Empty? return False
        if len(standard_external_history) == 0:
            return False
        
        # Clear existing data
        self.clear_messages(keep_system_prompt=False)
        
        for i, turn in enumerate(standard_external_history):
            
            # contains system
            if "system" in turn:
                self.messages.append({})
                self.original_messages.append({})
                # 
                self.system_prompt = turn["system"]
                self.messages[-1] = {"role": "system", "content": turn["system"]}
                self.original_messages[-1] = {"role": "system", "content": turn["system"]}
                
            # contains user
            if "user" in turn:
                
                # If it is the last latest turn, append reply, otherwise no
                if i + 1 == len(standard_external_history):
                    user_ret = self.api_chat_once(turn["user"], chat = False, append_input_front=True, append_control_response=True)
                else:
                    user_ret = self.api_chat_once(turn["user"], chat = False, append_input_front=True, append_control_response=False)
                
                # If user_ret is NoneType, then cast the latest response as assistant
                # And it is the last latest turn
                if user_ret is None and i + 1 == len(standard_external_history):
                    self.messages[-2]["role"] = "user"
                    self.original_messages[-2]["role"] = "user"
                    tools_, response = self.responses[-1]
                    turn["assistant"] = response
                    # And it will trigger the next one if clause
                else:
                    self.messages[-1]["role"] = "user"
                    self.original_messages[-1]["role"] = "user"
                    
            if "assistant" in turn:
                # DOES NOT SUPPORT TOOL CALLS, so None
                self.responses.append((None, turn["assistant"]))
                self.process_response(turn["assistant"], turn["user"])
                # To avoid renaming problems without a system prompt
                self.messages[-1]["role"] = "assistant"
                self.original_messages[-1]["role"] = "assistant"
                self.round_number += 1
                
        # Debug mode : output it
        if debug.nathui_global_debug:
            print(self.messages)
                    
        return True
    
    # Convert openai chat history to the internal type
    def convert_openai_chat_history(self, openai_chat_history: Dict[str, Any]) -> Dict[str, Any]:
        '''
        Convert external chat history into chatloop type and
        1. convert commands to actual data
        2. load into the backend
        3. Return the replaced messages
        Openai Chat History is like:
        {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, who won the world series in 2020?"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        '''
        
        # ######
        # still subject to change: 
        # For command turns, we do not need to add them to the model
        
        # Empty? return {}
        if len(openai_chat_history) == 0:
            return {}
        
        # Clear existing data
        self.clear_messages(keep_system_prompt=False)
        
        # Last user input
        last_user_content = ""
        
        # You must do this to avoid openai_chat_history to be referenced
        offset = 0
        for i in range(len(openai_chat_history["messages"])):
            
            # Get turn
            turn = openai_chat_history["messages"][i]
            
            # contains system
            if turn["role"] == "system":
                self.messages.append({})
                self.original_messages.append({})
                # 
                self.system_prompt = turn["content"]
                self.messages[i + offset] = {"role": "system", "content": turn["content"]}
                self.original_messages[i + offset] = {"role": "system", "content": turn["content"]}
                
            # contains user
            elif turn["role"] == "user":
                # If it is the last latest turn, append reply, otherwise no
                if i + 1 == len(openai_chat_history["messages"]):
                    user_ret = self.api_chat_once(turn["content"], chat = False, append_input_front=True, append_control_response=True)
                else:
                    user_ret = self.api_chat_once(turn["content"], chat = False, append_input_front=True, append_control_response=False)
                
                # User input has been recorded
                self.messages[i + offset]["role"] = "user"
                self.original_messages[i + offset]["role"] = "user"
                    
                # Set the last user content
                last_user_content = self.messages[i + offset]["content"]
                
                # Append responses if used commands
                # And it is the last latest turn
                if user_ret is None and i + 1 == len(openai_chat_history["messages"]):
                    
                    # Offset += 1 since it had done the response
                    offset += 1
                    self.round_number += 1
                    
            elif turn["role"] == "assistant":
                # DOES NOT SUPPORT TOOL CALLS, so None
                self.responses.append((None, turn["content"]))
                self.process_response(turn["content"], last_user_content)
                # 
                # To avoid renaming problems without a system prompt
                self.messages[i + offset]["role"] = "assistant"
                self.original_messages[i + offset]["role"] = "assistant"
                self.round_number += 1
        
        openai_chat_history_copy = openai_chat_history.copy()
        openai_chat_history_copy["messages"] = self.messages
        return openai_chat_history_copy
    
    # Main API to conduct one round of chat
    def api_chat_once(self, external_round_input: str | None = None, 
                      chat: bool = True, 
                      append_input_front: bool = False,
                      append_control_response: bool = False) -> None:
        '''
        Parameters:
            
        external_round_input: if str, then use this as the input
        
        chat                : if True, then chat, otherwise, just process and append the input
        '''
        
        # Get input or get input from console
        user_input = external_round_input
        if self.use_external is None or external_round_input is None:
            user_input = input("\nYou: ").strip()
            
        ########################################
        
        # Process special Commands
        processed_input = self.handle_special_commands(user_input)
        
        # Quit triggered
        if processed_input is None:
            self.ongoing = False
            return None
        
        # If front append, then force to append
        if append_input_front == True:
            # Cotrol commands
            if isinstance(processed_input, str) == False and isinstance(processed_input, dict) == True:
                self.messages.append({"role": "user", "content": user_input})
                self.original_messages.append({"role": "user", "content": user_input})
            # Ordinary ones (including select/search/visit)
            else:
                self.messages.append({"role": "user", "content": processed_input})
                self.original_messages.append({"role": "user", "content": user_input})
                
        # Non-chatting commands triggered -> DO NOT CHAT AND BLOCK DIRECTLY
        if isinstance(processed_input, str) == False:
            
            # If dict -> parse
            if isinstance(processed_input, dict):
                
                # function processing function
                def next_step(tool_:str, response_:str, input_:str): 
                    
                    # Response added but DO NOT add input
                    self.responses.append((tool_, response_))
                    
                    # Process response but DO NOT add output
                    self.process_response(
                        response_, 
                        input_,
                        append_response = append_control_response)
                    
                    return None
                
                # If r"\usage" is None
                if processed_input.get(r"\usage") is None:
                    return None
                
                # If r"\usage" = "\syntax" 
                if processed_input.get(r"\usage") == r"\syntax":
                    next_step("", self.command_buffer.buffer, user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\delete" 
                elif processed_input.get(r"\usage") == r"\delete":
                    next_step("", "`Previous Chat Deleted`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\deleteall" 
                elif processed_input.get(r"\usage") == r"\deleteall":
                    next_step("", "`Chat History Deleted`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\toolcall" 
                elif processed_input.get(r"\usage") == r"\toolcall":
                    next_step("", "`Toolcall switched to " + processed_input.get(r"\result") + "`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\locate" 
                elif processed_input.get(r"\usage") == r"\locate":
                    next_step("", f"`Relocated and connected to database: {processed_input.get('to')}`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\connect" 
                elif processed_input.get(r"\usage") == r"\connect":
                    next_step("", f"`Connected to table: {processed_input.get('to')}`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\insert" 
                elif processed_input.get(r"\usage") == r"\insert":
                    next_step("", f"`Inserted by key: {processed_input.get('key')}`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\update" 
                elif processed_input.get(r"\usage") == r"\update":
                    next_step("", f"`Updated by key: {processed_input.get('key')}`", user_input)
                    self.round_number += 1
                    return None
                
                # If r"\usage" = "\query" 
                elif processed_input.get(r"\usage") == r"\query":
                    next_step("", f"`Executed SQL Query: {processed_input.get('query')}`", user_input)
                    self.round_number += 1
                    return None
                
                # Otherwise, if is a dict, stop here and return
                else:
                    # Error occurred
                    next_step("", "`Negative. Errors Happened Internally`", user_input)
                    self.round_number += 1
                    return None
                
            # Otherwise, give it a back to original
            else:
                # To be compatible with legacy versions
                processed_input = user_input
        
        # Append User Input not frontly
        if append_input_front == False:
            self.messages.append({"role": "user", "content": processed_input})
            self.original_messages.append({"role": "user", "content": user_input})
        
        ########################################
            
        #######################################################################
        # 
        # Chat starts here
        
        if chat is None or chat == False:
            return True
        
        try:
            with Spinner("Thinking..."):
                tool_calls, response = self.request_onetime_response()
            # OR
            #   tool_calls, response = self.request_stream_response()
            
            # Append responses
            #####
            #####
            ## responses always increase as 1
            ## while messages may not since tool calling requires more spaces
            self.responses.append((tool_calls, response))
                
            # Append Assistant will be handled by process_response()
            if tool_calls:
                # If requesting tool_calls
                self.process_tool_calls(tool_calls)
                self.round_number += 1
            else:
                # Normal response (print and append)
                self.process_response(response, user_input)
                self.round_number += 1
                
            return True
       
        except Exception as e:
            self.handle_error(e)
            self.round_number += 1
            return None

    # Main API to call a loop chat
    def api_chat_loop(self, external_round_input: str | None = None):
        self.display_intro()
        self.ongoing = True
        while True:
            if self.ongoing == True:
                self.api_chat_once(external_round_input = external_round_input)
            else:
                break
    
    # Handle returned special tool-call response
    def handle_triggered_tool_calls(self, tool_calls) -> Any:
        
        ### It should support ALL tool-calls and appended strings of 
        ### fetched result, which will be then passed to llm
        
        # [ChatCompletionMessageToolCall(
        #  id='332043923', 
        #  function=Function(
        #   arguments='{"search_query":"Kaspersky"}', 
        #   name='fetch_wikipedia_content'
        #    ), 
        #   type='function'
        #   )
        # ]
        
        # Debug, triggered tool calls
        if debug.nathui_global_debug == True:
            print("Tool Called: ", tool_calls)
        
        for tool_call in tool_calls:
            cid = tool_call.id
            name = tool_call.function.name
            func = tool_call.type
            if func != "function":
                # omit non-function objects
                continue
            args = json.loads(tool_call.function.arguments)
            
            # Find if we have this function
            result = ""
            if self.tool_dict.get(name, None) is not None:
                callabl_ = self.tool_dict[name]
                result = callabl_(**args)
            else:
                # If we couldn't find, continue
                continue
            
            # Debug, display interim result
            if debug.nathui_global_debug == True:
                self.display_interim_content(result)
            
            ### Called messages will be appended here
            self.messages.append(
                {"role": "tool",
                 "content": json.dumps(result), 
                 "tool_call_id": cid}
                )
            self.original_messages.append(
                {"role": "tool",
                 "content": json.dumps(result), 
                 "tool_call_id": cid}
                )
        
        return result
    
    # Process returned response (render or print)
    def process_response(self, content:str, original_input:str, append_response:str = True):
        # Use standard renderer
        if callable(self.use_external):
            # Think Output Split
            think, output = tos(content)
            self.use_external(output, original_input)
            
        # No renderer
        elif self.use_external == "No Renderer":
            # Do Not Render and split
            pass
            
        # Directly print the response
        else:
            # Think Output Split
            think, output = tos(content)
            print("\nAssistant:" + output)
            
        # Append overall response 
        #
        # Now we use content instead of output to preserve overall data
        # If you want to reduce context offload, save output to both instead
        # By NathMath_at_bilibili, DOF Studio
        if append_response:
            self.messages.append({"role": "assistant", "content": content})
            self.original_messages.append({"role": "assistant", "content": content})
    
    # Get one-time response and return whole
    def request_onetime_response(self, model = None):
        # Get response
        
        # if model is None, use self.model
        if model is None:
            model = self.model
        
        # It is a FREE and OPEN SOURCED software
        # See github.com/dof-studio/NathUI
        
        # NOT USING TOOL
        if self.use_tools == False:
            response = self.client.chat.completions.create(
                model=model, 
                messages=self.messages,
                **self.infer_param)
            return response.choices[0].message.tool_calls, response.choices[0].message.content
            
        # TOOL-CALL ENABLED
        else:
            response = self.client.chat.completions.create(
                model=model, 
                messages=self.messages,
                tools=self.tools,
                **self.infer_param)
            
            if response.choices[0].message.tool_calls:
                # Handle all tool calls
                tool_calls = response.choices[0].message.tool_calls
                
                # Add 
                # @todo 
                # Handle this to external storages like NathUI
                # Add all tool calls to messages
                self.messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )
                self.original_messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )

                # Call tool and append called messages
                result = self.handle_triggered_tool_calls(tool_calls)
                
                # Does not need to generate again
                if result.get("response", None) is not None:
                    # The response is the response
                    return None, result.get("response")
                
                # Request again
                response = self.client.chat.completions.create(
                    model=model, 
                    messages=self.messages,
                    **self.infer_param)
                return response.choices[0].message.tool_calls, response.choices[0].message.content
            
            else:
                return response.choices[0].message.tool_calls, response.choices[0].message.content
    
    # Get and Print Stream Response to device (STD print() like devide)
    def request_stream_response(self, print_device = print, model = None):   
        # Get streamed response
        
        # if model is None, use self.model
        if model is None:
            model = self.model
            
        # NOT USING TOOL
        if self.use_tools == False:
            
            # Try to get the stream response
            stream_response = self.client.chat.completions.create(
                model=model, 
                messages=self.messages, 
                stream=True, 
                **self.infer_param)
            self.collected_content = ""
            for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print_device(content, end="", flush=True)
                    self.collected_content += content      
                    
            # It is a FREE and OPEN SOURCED software
            # See github.com/dof-studio/NathUI
            print_device("\n") #
            
            return None, self.collected_content
            
        # TOOL-CALL ENABLED
        else:
            # Try to get the stream response
            stream_response = self.client.chat.completions.create(
                model=model, 
                messages=self.messages, 
                tools=self.tools,
                stream=True, 
                **self.infer_param)
            self.collected_tool_calls = ""
            self.collected_content = ""
            for chunk in stream_response:
                # Normal content
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print_device(content, end="", flush=True)
                    self.collected_content += content 
                # Tool calls
                if chunk.choice[0].delta.tool_calls:
                    tool_content = chunk.choices[0].delta.content
                    self.collected_tool_calls += tool_content
                    
            # If we have non-empty tool_calls
            if self.collected_tool_calls != "":
                # Handle all tool calls
                tool_calls = self.collected_tool_call
                
                # Add 
                # @todo 
                # Handle this to external storages like NathUI
                # Add all tool calls to messages
                self.messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )
                self.original_messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )
                
                # Call tool and append called messages
                result = self.handle_triggered_tool_calls(tool_calls)
                
                # Does not need to generate again
                if result.get("response", None) is not None:
                    # The response is the response
                    return None, result["response"]
                
                # Request again
                stream_response = self.client.chat.completions.create(
                    model=model, 
                    stream=True, 
                    messages=self.messages,
                    **self.infer_param)
                
                for chunk in stream_response:
                    # Normal content
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print_device(content, end="", flush=True)
                        self.collected_content += content 
                
                print_device("\n") # endl
                return tool_calls, self.collected_content
                
            else:
                # It is a FREE and OPEN SOURCED software
                # See github.com/dof-studio/NathUI
                
                print_device("\n") # endl
                return None, self.collected_content
                    
    # Display fetched data, like browsing or file
    def display_interim_content(self, result: str | list, name = "Search Content"):
        # Only enabled in 
        # result should at least be a dict with
        # result["status"] = "success"
        # result["title"] = str: title
        # result["content"] = str: original result
        # result["message"] = str: error information
        if nathui_global_debug == True:
            terminal_width = shutil.get_terminal_size().columns
            print("\n" + "=" * terminal_width)
            if result["status"] == "success":
                print(f"\n{name}: {result['title']}")
                print("-" * terminal_width)
                if isinstance(result["content"], str) == True:
                    print(result["content"][0:128] + "...")
                elif isinstance(result["content"], list) == True:
                    for elm in result["content"]:
                        print(elm[0:128] + "...")
                else:
                    print(result["content"])
            else:
                print(f"\nError fetching {name}: {result['message']}")
            print("=" * terminal_width + "\n")

    # If there is a class error
    def handle_error(self, error):
        # Always print
        print(f"\nError chatting with Nath UI!\n\n"
              f"Please ensure:\n"
              f"1. LM Studio server is running at localhost:1234 (hostname:port)\n"
              f"2. Model '{self.model}' is downloaded\n"
              f"3. Model '{self.model}' is loaded, or that just-in-time model loading is enabled\n\n"
              f"Error details: {str(error)}\n"
              f"Contact NathMath@bilibili for more assistance\n")
        # Do not exit(1)
        return None


# Legacy Chatloop that is NOT updated
def chat_loop():
    """
    Main chat loop that processes user input and handles tool calls.
    """
    
    global responses, messages
    responses = []
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant to answer my questions concisely."
                "Starts with my master and then answer"
            ),
        }
    ]

    # Special Input
    print(
        "Assistant: "
        "Hi! I can access Wikipedia to help answer your questions about history, "
        "science, people, places, or concepts - or we can just chat about "
        "anything else!"
    )
    print("(Type '\quit' to exit)")
    print("(Type '\delete' to delete the previous chat round)")
    print("(Type '\deleteall' to delete all of the previous chat rounds)")
    print("(Type '\search ...' to search on the internet')")
    
    # Search Engine
    webcrawler = WebCrawler()
    search_prompt = "Summarize the following content in detail to answer the question using Markdown: "

    while True:
        user_input = input("\nYou: ").strip()
        original_input = user_input + " "
        
        if user_input.lower() == "\quit":
            print("User quitted")
            break
        
        elif user_input.lower() == "\delete":
            print("User deleted")
            if len(messages) > 1:
                messages = messages[0:len(messages)]
            continue
        
        elif user_input.lower() == "\deleteall":
            print("User deleted all")
            messages = [messages[0]]
            continue
        
        elif user_input.lower().startswith("\search"):
            with Spinner("Searching..."):
                to_search = user_input[7:]
                user_input = webcrawler.perform_google_search(to_search, 5)
                user_input = search_prompt + to_search + "? " + webcrawler.concat(user_input)
                
        messages.append({"role": "user", "content": user_input})
        client = OpenAI(base_url = params.nathui_backend_url + "/v1", 
                        api_key = params.nathui_backend_apikey)
        try:
            with Spinner("Thinking..."):
                response = client.chat.completions.create(
                    model=params.nathui_backend_model,
                    messages=messages
                )
            responses.append(response)

            if response.choices[0].message.tool_calls:
                # Handle all tool calls
                tool_calls = response.choices[0].message.tool_calls

                # Add all tool calls to messages
                messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )

                # Process each tool call and add results
                for tool_call in tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    result = fetch_wikipedia_content(args["search_query"])

                    # Print the Wikipedia content in a formatted way
                    terminal_width = shutil.get_terminal_size().columns
                    print("\n" + "=" * terminal_width)
                    if result["status"] == "success":
                        print(f"\nWikipedia article: {result['title']}")
                        print("-" * terminal_width)
                        print(result["content"])
                    else:
                        print(
                            f"\nError fetching Wikipedia content: {result['message']}"
                        )
                    print("=" * terminal_width + "\n")

                    messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(result),
                            "tool_call_id": tool_call.id,
                        }
                    )

                # Stream the post-tool-call response
                print("\nAssistant:", end=" ", flush=True)
                stream_response = client.chat.completions.create(
                    model=params.nathui_backend_model, messages=messages, stream=True
                )
                collected_content = ""
                for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        collected_content += content
                print()  # New line after streaming completes
                messages.append(
                    {
                        "role": "assistant",
                        "content": collected_content,
                    }
                )
            
            else:
                # Handle regular response
                # response.choices[0].message.content
                # response.choices[0].message.reasoning_content
                go_renderer(response.choices[0].message.content, original_input)
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                    }
                )

        except Exception as e:
            print(
                f"\nError chatting with the LM Studio server!\n\n"
                f"Please ensure:\n"
                f"1. LM Studio server is running at 0.0.0.0:1234 (hostname:port)\n"
                f"2. Model is downloaded\n"
                f"3. Model is loaded, or that just-in-time model loading is enabled\n\n"
                f"Error details: {str(e)}\n"
                "See https://lmstudio.ai/docs/basics/server for more information"
            )
            exit(1)


# Legacy External model list retriver
def model_list() -> dict:
    chat = Chatloop()
    return chat.fetch_loaded_models()


if __name__ == "__main__":
    # Displayer : default printing device
    cl = Chatloop(use_external=go_renderer)
    
    # Enable tool_calls
    cl.reset_use_tool(True)
    
    # Chat now
    cl.api_chat_loop()
    
    
    
    
    