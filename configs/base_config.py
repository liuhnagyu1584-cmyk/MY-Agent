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


# ============================================================
# 长期记忆配置
# ============================================================
MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "memory.json"
)
MEMORY_MAX_LOAD = 10  # 每次会话加载的最近记忆条数


# ============================================================
# 沙箱代码执行配置
# ============================================================

# 是否启用 Docker 沙箱（关闭后使用 subprocess 回退，安全性降低）
DOCKER_ENABLED = os.getenv("DOCKER_ENABLED", "true").lower() == "true"

# 沙箱默认超时（秒），范围 1-300
SANDBOX_DEFAULT_TIMEOUT = int(os.getenv("SANDBOX_DEFAULT_TIMEOUT", "30"))

# 沙箱最大内存（MB），范围 128-2048
SANDBOX_MAX_MEMORY = int(os.getenv("SANDBOX_MAX_MEMORY", "512"))

# 沙箱最大 CPU 核数，范围 0.1-4.0
SANDBOX_MAX_CPU = float(os.getenv("SANDBOX_MAX_CPU", "1.0"))

# 沙箱输出最大字节数（用于截断输出）
SANDBOX_MAX_OUTPUT = int(os.getenv("SANDBOX_MAX_OUTPUT", "1048576"))

