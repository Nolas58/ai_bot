import os
from dotenv import load_dotenv


load_dotenv()

OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
MODEL_NAME = os.getenv('MODEL_NAME')
VK_TOKEN = os.getenv('VK_TOKEN')
TG_TOKEN = os.getenv('TG_TOKEN')
