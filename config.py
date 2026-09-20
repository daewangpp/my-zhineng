# -*- coding: utf-8 -*-
"""CodeTutor 全局配置。

支持任意 OpenAI 兼容接口(DeepSeek / 智谱GLM / 通义 / Moonshot 等)。
优先读取环境变量,也可直接修改本文件。
"""
import os

# ---- LLM 配置(OpenAI 兼容接口)----
# 环境变量优先:CODETUTOR_API_KEY / CODETUTOR_BASE_URL / CODETUTOR_MODEL
API_KEY = os.environ.get("CODETUTOR_API_KEY",
                         "")
BASE_URL = os.environ.get("CODETUTOR_BASE_URL", "https://vmrouter.vip/v1")
MODEL = os.environ.get("CODETUTOR_MODEL", "qwen3.5-flash")

# 当前使用中转站(vmrouter.vip),实测 qwen3.5-flash 稳定;
# 该中转站还提供 deepseek-v4-flash(间歇性限流)/glm-4.7/kimi-k3 等 59 个模型可切换。
# 其他可选端点:
#   DeepSeek 官方: https://api.deepseek.com/v1        model=deepseek-chat
#   智谱GLM:      https://open.bigmodel.cn/api/paas/v4  model=glm-4-flash(免费)
#   Moonshot:     https://api.moonshot.cn/v1         model=moonshot-v1-8k

TIMEOUT = 45          # 单次请求超时(秒):快速失败重试,避免冷启动卡死
MAX_RETRIES = 2       # 请求失败重试次数
TEMPERATURE = 0.3     # 低温保证结构化输出稳定

# ---- 沙箱配置 ----
SANDBOX_TIMEOUT = 5   # 代码执行超时(秒)
FIX_MAX_ATTEMPTS = 2  # 修复Agent最大重试次数

# ---- 数据目录 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "knowledge_base", "python_errors.jsonl")
DB_PATH = os.path.join(BASE_DIR, "data", "codetutor.db")
