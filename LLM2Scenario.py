
import openai 
import json
import re

# 或者通过创建OpenAI客户端对象时设置API密钥 
client = openai.OpenAI(api_key='123456',base_url='http://127.0.0.1:23333/v1')

def scenario_structure(scenario_description):
    prompt = f"""Your task is to convert a natural language description of a traffic scenario into a standardized JSON format.

            The top-level key of the JSON must be "scenario", and its value must be an array. Each element in this array represents one vehicle, with two fields:
            - "role": The role of the vehicle.
            - The main vehicle is labeled as "ego".
            - Other vehicles are labeled sequentially as "npc1", "npc2", etc.
            - "behavior": A textual description of the vehicle's driving behavior over time.
            - Behavior must be described in chronological segments.
            - Each segment must clearly specify a **time duration**.
            - Example: "Accelerate to 20 km/h over 5 seconds", "Maintain speed for 10 seconds".

            The scenario description is: 
            {scenario_description}
            Ensure that all behaviors include time information and are described in clear, concise English. 
            Output only the final JSON object in the correct structure. Do not include any additional text or explanation.
            """
    
    # print(prompt)

    response = client.chat.completions.create( 
        model='internlm3-8b-instruct-awq',
        messages=[{'role': 'user', 'content': prompt}]  
    ) 
    # print(response.choices[0].message.content)

    json_str = response.choices[0].message.content
    match = re.search(r'\{.*\}', json_str, re.DOTALL)
    if match:
        try:
            # 尝试解析提取出的JSON字符串
            scenario_dict = json.loads(match.group(0))
            #print(scenario_dict)
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
    else:
        print("No valid JSON found in the response.")
    return scenario_dict

# scenario_structure("A car is driving on a straight road. A pedestrian is crossing the road.")