# func_primary.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################


TOOL_PROCEDURE = """
┌──────────────────────────┐
│ SETUP: LLM + Tool list   │
└──────────┬───────────────┘
           ▼
┌──────────────────────────┐
│    Get user input        │◄────┐
└──────────┬───────────────┘     │
           ▼                     │
┌──────────────────────────┐     │
│ LLM prompted w/messages  │     │
└──────────┬───────────────┘     │
           ▼                     │
     Needs tools?                │
      │         │                │
    Yes         No               │
      │         │                │
      ▼         └────────────┐   │
┌─────────────┐              │   │
│Tool Response│              │   │
└─────┬───────┘              │   │
      ▼                      │   │
┌─────────────┐              │   │
│Execute tools│              │   │
└─────┬───────┘              │   │
      ▼                      ▼   │
┌─────────────┐          ┌───────────┐
│Add results  │          │  Normal   │
│to messages  │          │ response  │
└──────┬──────┘          └─────┬─────┘
       │                       ▲
       └───────────────────────┘

"""

## Tool - Generate llm function property dict
## Function property declatation
def fp_call_property(field_name: str, field_type: str, description: str) -> dict:
    """
    Generates a dictionary representing the properties for a given field.

    Parameters:
    field_name (str): The name of the field.
    field_type (str): The data type of the field.
    description (str): A description of what the field represents.

    Returns:
    dict: A dictionary containing the properties definition.
    """
    return {
        field_name: {
            "type": field_type,
            "description": description,
        }
    }

def fp_call_properties(field_name: list, field_type: list, description: list) -> dict:
    """
    Generates a dictionary representing the properties for a given field.

    Parameters:
    field_name (list of str): The name of the field.
    field_type (list of str): The data type of the field.
    description (list of sstr): A description of what the field represents.

    Returns:
    dict: A dictionary containing the properties definition.
    """
    
    properties = {}
    for i in range(len(field_name)):
        properties[field_name[i]] = {
            "type": field_type[i],
            "description": description[i],
        }
    
    return properties


## Tool - Generate llm function dict
## Function property declatation
def fp_call_decl_function(
        name: str, 
        description: str, 
        properties: dict, 
        required: list,
        ptype: str = "object") -> dict:
    """
    Generates a dictionary representing an LLM function declaration.

    Parameters:
    name (str): The name of the function.
    description (str): A description of the function's purpose and behavior.
    properties (dict): A dictionary defining the properties for the function's parameters.
    required (list): A list of required property names.

    Returns:
    dict: A dictionary formatted as an LLM function declaration.
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": ptype,
                "properties": properties,
                "required": required,
            },
        },
    }


## Example for llm function declaration
WIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_wikipedia_content",
        "description": (
            "Search Wikipedia and fetch the introduction of the most relevant article. "
            "Always use this if the user is asking for something that is likely on wikipedia. "
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


## Tool - Generate callback response to llm
## Tool-call callback function
def generate_cbck_response(status: str, message: str = None, content: str = None, **kwargs) -> dict:
    """
    Generates a standardized response dictionary.

    Parameters:
    status (str): The status of the response, e.g. "success" or "error".
    message (str, optional): A message providing details about the result.
    content (str, optional): Something that is going to be passed back to llm as the calling result.
    **kwargs: Additional key-value pairs to include in the response (for example, content, title, etc).

    Returns:
    dict: A dictionary representing the response.
    """
    response = {"status": status}
    if message is not None:
        response["message"] = message
    if status == "success":
        response["content"] = content
    response.update(kwargs)
    return response


# Example usage with the provided instance:
if __name__ == "__main__":
    function_name = "fetch_wikipedia_content"
    function_description = (
        "Search Wikipedia and fetch the introduction of the most relevant article. "
        "Always use this if the user is asking for something that is likely on wikipedia. "
        "If the user has a typo in their search query, correct it before searching."
    )
    properties = fp_call_property(
        "search_query",
        "string",
        "Search query for finding the Wikipedia article"
    )
    required_properties = ["search_query"]

    llm_function_dict = fp_call_decl_function(function_name, function_description, properties, required_properties)
    print(llm_function_dict)

