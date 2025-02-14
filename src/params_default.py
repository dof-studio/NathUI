# params.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# Kernel Official Website (compile)
nathui_official_website = "https://github.com/dof-studio/nathui"

# Kernel Bilibili Website (compile)
nathui_official_bilibili_website = "https://space.bilibili.com/303266889"

# Kernel Notion Document (compile)
nathui_official_notion_doc = "https://truthful-busby-322.notion.site/NathMath-LLM-18e45165050a80408586c3f2bf93ce68"

# Backend Url (constant)
nathui_backend_url = "http://192.168.204.1:1234" # must NOT include "v1"

# Backend API key (constant)
nathui_backend_apikey = "lm-studio"

# Backend Model Name (variable)
nathui_backend_model = "gemma-2-9b-it@q4_k_m"

# Backend Default Sys Prompt (variable)
nathui_backend_default_sysprompt_CN = "你是一个人工智能助手。你需要准确、简洁地回答用户的问题。"
nathui_backend_default_sysprompt_EN = "You are an AI assistant to answer the user's questions precisely and concisely."

# Backend Default Search Engine
nathui_backend_default_search_engine = "bing"

# Backend Search Query Number (variable)
nathui_backend_search_no = 5

# Middleware Starting Port
nathui_backend_middleware_starting_port = 14514

# Middleware Coercively Transform to content
nathui_backend_stream_coer_dereasoning_content = 0

# 下个版本4.1更新：
#
# ` 工具调用！例如自己执行自己写的代码，以及自定义工具调用
#   甚至，，搜索/数据库工具可以被AI自己执行了？！！
#
# ` 前缀续写功能，你可以让AI从你给定的前文继续生成(webui的continue)
#   当然你们用webui也可以，
#   但是前缀续写功能将极大程度上支持让AI自动化进行数据分析的能力，
#   例如等待NathUI对大语言模型生成的代码跑完了之后，前缀续写会让
#   NathUI把结果反馈给模型，模型可以自行判断是否正确，是否继续分析。

