# params.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# Nathui Version Building No
nathui_version_building = "0410"

# Kernel Official Website (compile)
nathui_official_website = 'https://github.com/dof-studio/nathui'

# Kernel Bilibili Website (compile)
nathui_official_bilibili_website = 'https://space.bilibili.com/303266889'

# Kernel Notion Document (compile)
nathui_official_notion_doc = 'https://truthful-busby-322.notion.site/NathMath-LLM-18e45165050a80408586c3f2bf93ce68'

# Backend Url (constant) must NOT include "v1"
nathui_backend_url = 'http://192.168.204.1:1234'

# Backend API key (constant)
nathui_backend_apikey = 'lm-studio'

# Backend Model Name (variable)
nathui_backend_model = 'qwen2.5-vl-7b-instruct'

# Backend Default Sys Prompt (variable)
nathui_backend_default_sysprompt_CN = '你是一个人工智能助手。你需要准确、简洁地回答用户的问题。'
nathui_backend_default_sysprompt_EN = "You are an AI assistant to answer the user's questions precisely and concisely."

# Backend Default Search Engine
nathui_backend_default_search_engine = 'bing'

# Backend Search Query Number (variable)
nathui_backend_search_no = 5

# Middleware Servering Address (constant) must NOT include "v1" and "http"
nathui_backend_middleware_serve_address = "192.168.204.1"

# Middleware Starting Port
nathui_backend_middleware_starting_port = 14514

# Middleware Coercively Transform to content
nathui_backend_stream_coer_dereasoning_content = 0

# 本版本版本4.1更新：
# ` 工具调用！例如自己执行自己写的代码，以及自定义工具调用
#   甚至，，搜索/数据库工具可以被AI自己执行了？！！
# ` 音频多模态输出: 免费、快读地享用AI生成的自然语音
#
# 下版本4.2更新
# ` Advanced Audio Mode: 使用声音与模型交互，说话，然后等待模型
#   以语音来回复。
# ` Primo Audo Analyzer: 自动数据分析功能，AI可以在无监督的情况下
#   根据你的要求调用工具，修改代码，运行代码，分析你的数据，
#   直到达到你的要求的结果； 模型可以自行判断是否正确，是否继续分析；
#   一旦满意，自行停止
# 
# 之后版本4.3展望
# ` 事件图模式: 你可以建立一个树状图，每一个树状图分支代表一个对话分支，
#   你可以自己选择在哪一个分支继续提问，然后所有的提问历史
#   是该分支回溯到根节点的所有历史。
# ` 图片视频多模态的支持: 敬请期待 

