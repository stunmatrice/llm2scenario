from functools import partial
from typing import Any, Dict, List, Mapping, Optional, Set
from langchain_core.callbacks import CallbackManagerForLLMRun

import openai 

from langchain_core.language_models.llms import LLM

# 或者通过创建OpenAI客户端对象时设置API密钥 
client = openai.OpenAI(api_key='123456',base_url='http://127.0.0.1:23333/v1')

class InternLM3(LLM): 
    # def __init__(self, model, messages): 
    #     self.model = model 
    #     self.messages = messages

    def _call(self, prompt:str,stop: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForLLMRun] = None,**kwargs: Any) -> str: 
        text = None
        response = client.chat.completions.create( 
            model='internlm3-8b-instruct-awq', # 指定使用的模型版本 
            messages= [{'role': 'user', 'content': prompt}] # 用户输入的信息 
        ) # 获取响应并打印结果 
        return response.choices[0].message.content
    
    @property
    def _llm_type(self) -> str: 
        return "internlm3_8b-instruct-awq"

# # 创建聊天请求 
# response = client.chat.completions.create( 
#     model='internlm3-8b-instruct-awq', # 指定使用的模型版本 
#     messages=[{'role': 'user', 'content': '1+1'}] # 用户输入的信息 
# ) # 获取响应并打印结果 

# print(response.choices[0].message.content)
# for chunk in response: 
#     print(chunk.choices[0].delta.content, end="", flush=True)