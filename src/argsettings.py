# argsettings.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# It is a FREE and OPEN SOURCED software
# See github.com/dof-studio/NathUI

# Backend #####################################################################

from param_editor import ParamEditor

# Collect inputs from user input
def collect_inputs(param_names: list, prompts: list) -> dict:
    # Check that both lists have the same length
    if len(param_names) != len(prompts):
        raise ValueError("Parameter names list and prompt messages list must have the same length.")
    
    # Initialize an empty dictionary to store the inputs
    result = {}
    
    # Iterate over parameter names and their corresponding prompts simultaneously
    for name, prompt in zip(param_names, prompts):
        
        # Prompt the user and store the input value in the dictionary
        result[name] = input(prompt).strip()
    
    return result

# Nath UI param settings
def nathui_param_settings(has_model: bool = True):
    
    # Example list of parameter names
    names = ["nathui_backend_url",
             "nathui_backend_middleware_serve_address",
             "nathui_backend_apikey",]
    if has_model:
        names.append("nathui_backend_model")
    
    # Example list of prompt messages for each parameter
    prompt_texts = [
        "输入LM Studio/OpenAI后端地址: ",
        "输入Nath Middleware服务地址: ",
        "输入LM Studio/OpenAI的密钥: "
    ]
    if has_model:
        prompt_texts.append("输入LM Studio/OpenAI的模型名称: ")
    
    # Collect user inputs based on the provided lists
    user_inputs_dict = collect_inputs(names, prompt_texts)
    
    # post-process
    # 1. nathmiddleware should not contain :
    if "nathui_backend_middleware_serve_address" in names:
        values = names["nathui_backend_middleware_serve_address"].split(":")
        if len(values) == 1:
            pass
        elif len(values) == 2:
            if values[0] == "http" or values[0] == "https":
                # values[0] is http/https
                names["nathui_backend_middleware_serve_address"] = values[1]
            elif int(values[1]) > 0:
                # values[1] is port
                names["nathui_backend_middleware_serve_address"] = values[0]
        else:
            raise Exception("Invalid nath middleware url, do not add http or port number!")
    
    # Change the parameters
    editor = ParamEditor("params.py")
    for name in names: 
        editor.var_dict[name] = user_inputs_dict[name]
        
    # Apply the modifications to the file.
    editor.apply_modifications()

if __name__ == "__main__":
    
    nathui_param_settings()

