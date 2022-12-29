from manager import Config
config = {
    "what2eat_path": Config.get_config("what2eat", "WHAT2EAT_PATH"),
    "superusers": Config.get_config("what2eat","SUPERUSERS"),
    "eating_limit": Config.get_config("what2eat","EATING_LIMIT"),
}