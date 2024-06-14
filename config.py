import yaml
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

with open('config.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())