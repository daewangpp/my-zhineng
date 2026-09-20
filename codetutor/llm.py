# -*- coding: utf-8 -*-
"""LLM 客户端层。

- LLMClient:requests 直连任意 OpenAI 兼容接口,零重依赖;
- MockLLMClient:无 API Key 时的演示模式 —— 借助真实沙箱运行结果做模式识别,
  保证完整流水线(诊断→修复→讲解→出题→归档)在无网/无 Key 时也能跑通演示。
"""
import json
import re
import time

import requests

import config


class LLMError(Exception):
    pass


class LLMClient:
    """OpenAI 兼容接口客户端。"""

    def __init__(self, api_key=None, base_url=None, model=None,
                 timeout=None, max_retries=None):
        self.api_key = api_key or config.API_KEY
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.model = model or config.MODEL
        self.timeout = timeout or config.TIMEOUT
        self.max_retries = max_retries if max_retries is not None else config.MAX_RETRIES

    def chat(self, messages, temperature=None, json_mode=True, max_tokens=None):
        """发送对话请求,返回 content 字符串。json_mode 时尽力解析为 dict。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": config.TEMPERATURE if temperature is None else temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    self.base_url + "/chat/completions",
                    headers=headers, json=payload, timeout=self.timeout,
                )
                if resp.status_code != 200:
                    raise LLMError("HTTP %s: %s" % (resp.status_code, resp.text[:300]))
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return self._maybe_json(content) if json_mode else content
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(0.8 * (attempt + 1))  # 快速退避重试
        raise LLMError("LLM 请求失败: %s" % last_err)

    @staticmethod
    def _maybe_json(content):
        """从模型输出中提取 JSON。

        注意:输出内部的代码块可能含 ``` 围栏,因此必须按以下顺序解析,
        避免被内部围栏截断:
        1) 整体直接解析(标准裸 JSON 直接命中);
        2) 剥掉首尾 ```json ... ``` 围栏后解析;
        3) 取最外层 { ... } 配对解析;
        4) 全部失败则返回 {"_raw": 原文}。
        """
        text = content.strip()
        # 1) 整体解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 2) 剥掉首尾围栏(仅当文本以围栏开头且以围栏结尾)
        if text.startswith("```") and text.endswith("```"):
            inner = re.sub(r"^```(?:json)?\s*", "", text)
            inner = re.sub(r"\s*```$", "", inner)
            try:
                return json.loads(inner.strip())
            except json.JSONDecodeError:
                pass
        # 3) 最外层花括号配对
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"_raw": content}


# ---------------------------------------------------------------------------
# Mock 模式:无 API Key 时保证系统可完整演示(界面/流水线/沙箱全部真实)
# ---------------------------------------------------------------------------

class MockLLMClient:
    """演示模式客户端:不调用远端模型,用规则+真实沙箱结果模拟各 Agent 输出。

    注意:该模式仅用于无 Key 时的流程演示与界面调试;
    正式使用请在 config.py 或环境变量中配置 API Key。
    """

    MOCK_TAG = "[演示模式] "

    def chat(self, messages, temperature=None, json_mode=True):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "诊断 Agent" in system:
            result = self._diagnose(user)
        elif "修复 Agent" in system:
            result = self._fix(user)
        elif "讲解 Agent" in system:
            result = self._explain(user)
        elif "出题 Agent" in system:
            result = self._quiz(user)
        else:
            result = {"_raw": self.MOCK_TAG + "未识别的角色"}
        return result if json_mode else json.dumps(result, ensure_ascii=False)

    # ---- 各角色模拟 ----

    def _diagnose(self, user):
        from codetutor.tools.sandbox import run_code, extract_error
        code = self._grab_code(user)
        sand = run_code(code)
        err_type, err_line = extract_error(sand.stderr) if sand.stderr else (None, None)
        mapping = {
            "IndexError": ("index_error", ["列表", "索引", "边界条件"], "索引超出列表范围,通常是循环边界或 len() 使用不当。"),
            "KeyError": ("key_error", ["字典", "键存在性"], "访问了字典中不存在的键,应先判断或使用 get()。"),
            "TypeError": ("type_error", ["数据类型", "类型转换"], "运算涉及不兼容的类型,常见于 input() 返回值未转换。"),
            "IndentationError": ("indent_error", ["缩进", "代码块"], "代码块缩进不一致。"),
            "RecursionError": ("recursion_error", ["递归", "基例"], "递归缺少终止条件或基例不可达。"),
            "NameError": ("name_error", ["变量作用域", "命名"], "使用了未定义的变量。"),
            "ZeroDivisionError": ("zero_division", ["异常处理", "边界条件"], "除数为 0,缺少前置判断。"),
            "AttributeError": ("attribute_error", ["对象属性", "None 值"], "对象没有该属性,常见于对 None 取成员。"),
        }
        if err_type and err_type in mapping:
            key, tags, cause = mapping[err_type]
        elif re.search(r"def\s+\w+\([^)]*=\s*\[\s*\]", code):
            key, tags, cause, err_type, err_line = "mutable_default", ["函数", "默认参数", "可变对象"], "使用了可变对象作为默认参数,多次调用间共享同一列表。", "LogicError", self._find_line(code, r"def\s+\w+\([^)]*=\s*\[")
        elif re.search(r"for\s+\w+\s+in\s+\w+\s*:", code) and re.search(r"\.(append|remove|pop)\(", code):
            key, tags, cause, err_type, err_line = "modify_while_iterate", ["列表", "迭代"], "在遍历列表的同时修改它,导致元素被跳过。", "LogicError", self._find_line(code, r"\.(append|remove|pop)\(")
        else:
            key, tags, cause = "logic_error", ["程序逻辑"], "代码可运行但结果不符合预期,需检查算法逻辑。"
            if not err_type:
                err_type, err_line = "LogicError", 1
        return {
            "error_type": err_type,
            "error_key": key,
            "error_line": err_line or 1,
            "root_cause": self.MOCK_TAG + cause,
            "knowledge_tags": tags,
            "brief": self.MOCK_TAG + "识别为 %s(第 %s 行附近)。" % (err_type, err_line or "?"),
        }

    def _fix(self, user):
        from codetutor.tools.sandbox import run_code
        code = self._grab_code(user)
        fixed = None
        summary = ""
        # 可变默认参数
        m_def = re.search(r"def\s+(\w+)\(([^)]*=\s*\[\s*\][^)]*)\)", code)
        if m_def:
            fname = m_def.group(1)
            param = None
            for p in m_def.group(2).split(","):
                if "=" in p:
                    param = p.split("=")[0].strip()
                    break
            fixed = re.sub(r"=\s*\[\s*\]", "=None", code, count=1)
            fixed = re.sub(
                r"(def\s+" + fname + r"\([^)]*\):\s*\n)",
                lambda m: m.group(1) + "    if " + param + " is None:\n"
                          + "        " + param + " = []\n",
                fixed, count=1)
            summary = "将可变默认参数改为 None,函数体内初始化"
        # input 类型转换
        elif re.search(r"input\(\)", code) and not re.search(r"(int|float)\(\s*input\(", code):
            fixed = re.sub(r"(?<!(int|float)\()input\(\)", "int(input())", code, count=1)
            summary = "为 input() 增加 int() 类型转换"
        if fixed is None:
            return {"fixed_code": code, "change_summary": self.MOCK_TAG + "该错误模式需真实模型修复",
                    "mock_cannot_fix": True}
        sand = run_code(fixed)
        return {"fixed_code": fixed, "change_summary": self.MOCK_TAG + summary,
                "expected_stdout": sand.stdout, "_sandbox_ok": sand.ok}

    def _explain(self, user):
        return {
            "concept": self.MOCK_TAG + "本题考查知识点:参见诊断中的知识点标签。",
            "why_common": self.MOCK_TAG + "初学者常因对语言机制的直觉性误解而犯此错。",
            "principle": self.MOCK_TAG + "正确写法背后的原理:遵循语言规范并对边界条件做显式处理。",
        }

    def _quiz(self, user):
        return {"questions": [
            {"title": "巩固题", "type": "改错",
             "question": self.MOCK_TAG + "请指出下列代码中与本次错误同类的问题(示例题)。",
             "answer": self.MOCK_TAG + "答案示例"},
            {"title": "迁移题", "type": "小实践",
             "question": self.MOCK_TAG + "编写一个 5 行以内的小程序,主动触发并捕获本次的错误类型。",
             "answer": self.MOCK_TAG + "答案示例"},
        ]}

    @staticmethod
    def _grab_code(text):
        m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
        return m.group(1).strip() if m else text

    @staticmethod
    def _find_line(code, pattern):
        for i, line in enumerate(code.splitlines(), 1):
            if re.search(pattern, line):
                return i
        return 1


def get_llm(prefer_real=True):
    """工厂函数:有 Key 用真实客户端,否则回退演示模式。"""
    if config.API_KEY and prefer_real:
        return LLMClient(), False
    print("[CodeTutor] 未检测到 API Key,进入演示模式(MockLLM)。")
    print("          在 config.py 或环境变量 CODETUTOR_API_KEY 中配置后即切换为真实模型。")
    return MockLLMClient(), True


def warmup():
    """预热 LLM 连接:服务启动时后台发一个微小请求,消除首个真实请求的冷启动延迟。"""
    if not config.API_KEY:
        return
    try:
        LLMClient().chat([{"role": "user", "content": "回复ok"}],
                         json_mode=False, max_tokens=5)
        print("[CodeTutor] LLM 预热完成")
    except Exception as e:  # noqa: BLE001
        print("[CodeTutor] LLM 预热失败(不影响使用): %s" % e)
