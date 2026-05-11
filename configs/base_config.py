import os
from dotenv import load_dotenv

load_dotenv()


MODEL_PROVIDER = "deepseek"
MODEL_NAME = "deepseek-v4-pro"
MODEL_BASE_URL = "https://api.deepseek.com"
MODEL_API_KEY = os.getenv("DEEPSEEK_API_KEY")

MAX_ITERATIONS = 20  # 最大迭代次数

# ============================================================
# 文件操作安全配置
# 优先级：FULL_ACCESS > WORKSPACE_ROOT > ALLOW_UNSAFE
# 通过 .env 文件或环境变量覆盖默认值
# ============================================================

# 终极开关：开启后无视一切限制（无沙箱、无黑名单、无大小限制）
FULL_ACCESS = os.getenv("FULL_ACCESS", "false").lower() == "true"

# 沙箱根目录：文件操作仅允许在此目录内进行
# 设为空字符串 "" 即取消沙箱限制，允许访问任意路径
WORKSPACE_ROOT = os.getenv(
    "WORKSPACE_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# 安全旁路：开启后跳过黑名单后缀、受保护文件/目录、文件大小限制
# 但沙箱限制（WORKSPACE_ROOT）仍然生效
ALLOW_UNSAFE = os.getenv("ALLOW_UNSAFE", "false").lower() == "true"


print(f"WORKSPACE_ROOT: {WORKSPACE_ROOT}")