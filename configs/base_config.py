import os
from dotenv import load_dotenv

load_dotenv()


MODEL_PROVIDER = "deepseek"
MODEL_NAME = "deepseek-v4-pro"
MODEL_BASE_URL = "https://api.deepseek.com"
MODEL_API_KEY = os.getenv("DEEPSEEK_API_KEY")

MAX_ITERATIONS = 20 # 最大迭代次数
