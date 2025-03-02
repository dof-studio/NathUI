# func_defaults.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

import debug
import params
from strutil import str_unquote
from search_engine import WebCrawler
from visitor import is_file, file_visitor
from filewalker import FileWalker
from fileopener import FileOpener
from codeinterpretor_python import CodeEvaluatorPython

# Default functions []
# 
# Web Search tool 
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search_on_internet",
        "description": (
            "Search on the Internet to obtain the most relevant information about a certain concept or news. "
            "Always use this if the user is asking explicitly for searching on the internet or the user is asking for a concept that you are not famaliar with. "
            "If the user has a typo in their search query, correct it before searching."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Search query for finding a concept or news.",
                },
            },
            "required": ["search_query"],
            "author": ["Nathmath"]
        },
    },
}
#
# Web Search implementation
def web_search_on_internet(search_query:str) -> dict:
    """
    Search on the internet for a given search_query
    """
    
    try:
        webcrawler = WebCrawler()
        searched_result = webcrawler.crawl_from_search(search_query,
                    k = params.nathui_backend_search_no,
                    search_engine = params.nathui_backend_default_search_engine)

        content = webcrawler.concat(searched_result)
        return {
            "status": "success",
            "content": content,
            "title": search_query,
        }

    except Exception as e:
        return {"status": "error", "message": "Web searching error: " + str(e)}


# Default functions []
# 
# General Visit tool
DATA_VISITOR_TOOL = {
    "type": "function",
    "function": {
        "name": "data_visitor_online_or_local",
        "description": (
            "This function can perform data fetching either from an explicitly specified online url, or from a local file or folder."
            "Always use this if the user is asking explicitly for `visiting` or `访问` an online address, or accessing to data specified by a file path or folder path. "
            "Make sure to copy the exact online url address or file paths as the argument that the user specified."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Online address or local file/folder's absolute path",
                },
            },
            "required": ["address"],
            "author": ["Nathmath"]
        },
    },
}
#
# Data Vistor implementation
def data_visitor_online_or_local(address: str) -> dict:
    """
    Visit an online address or local file path.
    """
    
    try:
        # Unquote and strip if necessary
        # : Really important or it will give an error
        # : By NathMath at platform bilibili
        splited = str_unquote(address.strip()) # correct sequence of calling
        
        # Get type
        content_type = is_file(splited)
        
        # If a file, read it
        if content_type == 1:
            file_content = file_visitor(splited, as_markdown=True)
            return {
                "status": "success",
                "content": file_content,
                "title": splited,
            }
        
        # If a url, visit it
        elif content_type == 2:
            webcrawler = WebCrawler()
            web_content = webcrawler.crawl_website(splited)
            return {
                "status": "success",
                "content": web_content,
                "title": splited,
            }
        
        # If a folder, get the table of its immediate content
        elif content_type == 3:
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
            return {
                    "status": "success",
                    "content": fdr_content,
                    "title": splited,
                } 
        
        # Else, abort with None
        else:
            return {"status": "error", "message": "Visitor error: " + f"Invalid input arg {splited}"}
        
    except Exception as e:
         return {"status": "error", "message": "Web searching error: " + str(e)}


# Default functions []
# 
# File Opener tool
FILE_OPENER_TOOL = {
    "type": "function",
    "function": {
        "name": "local_file_opener",
        "description": (
            "You have the permission to access and open a file. "
            "This function can open a file or start a program that is stored locally."
            "Always use this if the user is asking explicitly for `opening`, `starting`, or `打开` a local file specified by a given file path or the lastest file path in the chat history. "
            "Make sure to copy the exact file path as the argument that the user specified."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "Local file's absolute path of the file to open or start",
                },
            },
            "required": ["address"],
            "author": ["Nathmath"]
        },
    },
}
#
# File Opener implementation
def local_file_opener(address:str) -> dict:
    """
    Open a local file or program by default.
    """
    
    try:
        fileopener = FileOpener(address)
        fileopener.open_file()
        
        return {
            "status": "success",
            "content": f"I have opened the file: {address}",
            "title": address,
            "response": f"File '{address}' has been opened!",
        }

    except Exception as e:
        return {"status": "error", "message": "File Opener error: " + str(e)}


# Default functions []
# 
# Python Code executor
PYTHON_EXECTUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "python_code_executor",
        "description": (
            "You have the access to execute, to run Python code and get the result. "
            "This function accepts some Python code and can execute the code to get the printed result. "
            "Always use this if the user is asking for `executing`, `running`, or `运行` some python code that is provided or generated in the latest chat history. "
            "Make sure to copy the exct Python code as the argument. "
            "Make sure to print the result in the code to get it. "
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "python_code": {
                    "type": "string",
                    "description": "Complete Python code to execute, maybe given, to generate now, or generated in chat history",
                },
            },
            "required": ["python_code"],
            "author": ["Nathmath"]
        },
    },
}
#
# Python Code executor implementation
def python_code_executor(python_code:str) -> dict:
    """
    Execute python code and return the result (errors and plots).
    """
    
    try:
        evaluator = CodeEvaluatorPython()
        result = evaluator.run_code(python_code)
        r_output = result["output"]
        r_error = result["error"]
        r_result = result["result"]
        r_plot = result.get("plots", None)
        
        # Generated dict
        ret = {
            "status": "success",
            "content": f"""
            ###Code: {python_code} \n\n
            
            Result: \n
            ###Captured Output: 
                {r_output}, \n
            ###Captured Errors: 
                {r_error}, \n
            ###Evaluation Result: 
                {r_result}, \n
            """
            ,
            "title": "Python Code",
        }
        
        if r_plot is not None:
            ret["plot"] = r_plot # in base64 form
        return ret

    except Exception as e:
        return {"status": "error", "message": "Python Executor error: " + str(e)}
