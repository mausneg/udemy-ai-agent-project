import os
import json

def load_mcp_config(*server_names):
    config_path = "mcp_config.json"
    
    with open(config_path, "r", encoding="utf-8") as f:
        all_config = json.load(f)
        
    if len(server_names) == 0:
        return all_config
    
    selected_config = {}
    for name in server_names:
        if name in all_config:
            selected_config.update({name: all_config[name]})
            
    return selected_config