
import os 
import chromadb
import json

data_set_path = r"D:\data_set\chromadb"
collection_name = "ScenariosPlacement"

chroma_client = chromadb.PersistentClient(path=data_set_path)
collection = chroma_client.get_or_create_collection(name=collection_name)

# 

def load_file_to_chroma(file_name):
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            print(type(data))
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return
        

def load_placement_file(file_name='ScenariosPlacement.json'):
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            return data['scenarios'][0]
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

# load_file_to_chroma('ScenariosPlacement.json')