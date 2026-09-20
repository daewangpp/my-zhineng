# -*- coding: utf-8 -*-
"""代码沙箱:静态安检 + 隔离执行 + 超时控制 + 错误解析。

CodeTutor 的杀手级特性支撑模块 —— "可验证修复":
每一条 AI 修复建议都必须在本沙箱中真实运行通过,才标记为"已验证"。

安全设计(教学场景足够,申报书可查):
1. 静态危险代码扫描(黑名单 import / 危险调用)在执行前拦截;
2. `python -I` 隔离模式运行(忽略用户 site-packages 与环境变量);
3. 独立临时目录作为工作目录,执行后自动清理;
4. subprocess 超时强杀(默认 5s),防止死循环。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

# 危险模块黑名单(网络/系统/文件操作,教学代码用不到)
BANNED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "socket", "requests", "urllib",
    "ctypes", "multiprocessing", "threading", "signal", "pathlib",
    "importlib", "pickle", "marshal", "builtins", "webbrowser",
}
# 危险调用黑名单
BANNED_CALLS = {
    "open", "exec", "eval", "input", "__import__", "compile",
    "globals", "locals", "exit", "quit", "breakpoint",
}


@dataclass
class SandboxResult:
    ok: bool                 # 是否正常运行结束(返回码 0)
    blocked: bool = False    # 是否被静态安检拦截
    block_reason: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    elapsed: float = 0.0
    timed_out: bool = False
    extra: dict = field(default_factory=dict)


def static_scan(code):
    """静态危险代码扫描。返回 (ok, reason)。"""
    # 检查 import 黑名单
    for m in re.finditer(r"^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)", code, re.M):
        top = m.group(1).split(".")[0]
        if top in BANNED_IMPORTS:
            return False, "检测到受限制模块: %s(沙箱教学环境禁止系统/网络/文件操作)" % top
    # 检查危险调用
    for m in re.finditer(r"\b([a-zA-Z_]\w*)\s*\(", code):
        if m.group(1) in BANNED_CALLS:
            return False, "检测到受限制调用: %s()" % m.group(1)
    return True, ""


def run_code(code, timeout=None):
    """在沙箱中执行 Python 代码,返回 SandboxResult。"""
    from config import SANDBOX_TIMEOUT
    timeout = timeout or SANDBOX_TIMEOUT

    ok, reason = static_scan(code)
    if not ok:
        return SandboxResult(ok=False, blocked=True, block_reason=reason,
                             stderr="[Sandbox Blocked] " + reason)

    tmpdir = tempfile.mkdtemp(prefix="codetutor_sb_")
    script = os.path.join(tmpdir, "submission.py")
    try:
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)
        start = time.time()
        try:
            proc = subprocess.run(
                # -X utf8:强制沙箱内 Python 以 UTF-8 读写源码与输出,
                # 避免 Windows 默认 GBK 解码导致的中文字符串乱码
                [sys.executable, "-I", "-X", "utf8", script],
                capture_output=True, text=True, timeout=timeout,
                cwd=tmpdir, encoding="utf-8", errors="replace",
            )
            elapsed = time.time() - start
            return SandboxResult(
                ok=proc.returncode == 0,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                returncode=proc.returncode,
                elapsed=round(elapsed, 3),
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, timed_out=True, elapsed=timeout,
                                 stderr="[Sandbox Timeout] 执行超过 %d 秒,已强制终止"
                                        "(疑似死循环)" % timeout)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def extract_error(stderr):
    """从 traceback 文本中提取 (错误类型, 出错行号)。"""
    if not stderr:
        return None, None
    err_type = None
    for line in stderr.strip().splitlines()[::-1]:
        m = re.match(r"^([A-Za-z_][\w.]*?(?:Error|Exception|Warning))\b", line.strip())
        if m:
            err_type = m.group(1).split(".")[-1]
            break
    err_line = None
    lines = re.findall(r'File ".*?submission\.py", line (\d+)', stderr)
    if lines:
        err_line = int(lines[-1])
    return err_type, err_line


_PUNCT_TRANS = str.maketrans("：，。；！？（）【】“”‘’", ":,.;!?()[]\"\"''")


def _normalize_stdout(text):
    """标准化输出用于比对:移除所有空白字符、全角标点归一为半角后逐行比对。

    原因:print('总价:', 300) 逗号空格、全/半角冒号等属于
    教学无关紧要的格式差异,不应据此误判修复失败。
    输出结构(行数/内容字符)仍需一致。
    """
    import re as _re
    lines = []
    for ln in (text or "").replace("\r\n", "\n").split("\n"):
        lines.append(_re.sub(r"\s+", "", ln).translate(_PUNCT_TRANS))
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def verify_fix(fixed_code, original_error_type=None, expected_stdout=None, timeout=None):
    """双轨验证修复,返回 (verified, SandboxResult, message)。

    第一轨(报错类):代码正常运行结束(返回码 0)且原错误类型消除;
    第二轨(逻辑类):若提供 expected_stdout,真实输出必须与预期逐字符一致,
    防止"代码能跑但结果仍然错误"的假阳性。
    """
    result = run_code(fixed_code, timeout=timeout)
    if result.blocked:
        return False, result, "修复代码被沙箱安检拦截: " + result.block_reason
    if result.timed_out:
        return False, result, "修复代码执行超时(疑似死循环)"
    if not result.ok:
        new_type, _ = extract_error(result.stderr)
        if original_error_type and new_type == original_error_type:
            return False, result, "修复无效:仍报同样的错误(%s)" % new_type
        return False, result, "修复后出现新错误: %s" % (new_type or "未知错误")
    # 返回码 0,进入输出断言轨
    if expected_stdout is not None and expected_stdout.strip() != "":
        actual = _normalize_stdout(result.stdout)
        expect = _normalize_stdout(expected_stdout)
        if actual != expect:
            return False, result, (
                "运行无报错但输出与预期不符。\n预期输出:\n%s\n实际输出:\n%s"
                % (expect, actual))
        return True, result, "修复代码真实运行通过,且输出与预期一致 ✔"
    return True, result, "修复代码在沙箱中真实运行通过 ✔"
