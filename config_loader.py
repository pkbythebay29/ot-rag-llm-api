import yaml

CONFIG_PATH = "config/system.yaml"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)
