import yaml

with open('config.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())