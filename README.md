# CodeTutor · 程序员的 AI 错题搭子

> 不止帮你改对,更让你下次不再错。
> 多智能体协作 · 沙箱真实运行验证 · 个人错题档案 · 艾宾浩斯复习闭环

## 项目简介

CodeTutor 是面向编程初学者的 AI 学习搭子。粘贴报错代码,系统由 5 个专业智能体协作完成:**诊断根因 → 修复代码(沙箱真实执行验证)→ 三段式讲解 → 归档个人错题本并按遗忘曲线推送复习**;**"举一反三"变式练习按需生成**(用户点击才触发出题 Agent),主流水线响应更快、Token 更省。

与通用 AI 编程助手"生成即结束"不同,CodeTutor 的**每一条修复建议都在隔离沙箱中真实运行验证通过后才交付**,未通过验证的方案会被明确标记——解决初学者"AI 的答案不敢信"的核心痛点。

## 系统架构

```
                     ┌──────────────────────────┐
                     │   Web UI (Flask 单页应用)  │
                     └─────────────┬────────────┘
                     ┌─────────────▼────────────┐
                     │  Orchestrator 编排器       │
                     │  流水线调度/降级兜底/状态传递 │
                     └─┬────┬────┬─────────────┘
        ┌──────────────┘    │    └──────────┐
 ┌──────▼──────┐  ┌────────▼┐ ┌─▼──────┐  ┌─▼────────┐     ┌──────────┐
 │ Diagnoser   │  │ Fixer   │ │Explainer│  │Archivist │     │ Quizzer  │
 │ 诊断( RAG ) │→│ 修复+重试│→│ 三段讲解 │→│ 归档调度  │     │ 变式出题  │
 └──────┬──────┘  └────┬────┘ └────────┘  └────┬─────┘     └────┬─────┘
 ┌──────▼──────┐  ┌────▼─────────┐      ┌──────▼──────┐        │
 │ 报错知识库    │  │ Sandbox 沙箱  │      │ SQLite 档案  │◄───────┘
 │ TF-IDF 检索 │  │ 安检/隔离/超时│      │ 艾宾浩斯复习 │  按需触发
 └─────────────┘  └──────────────┘      └─────────────┘ (用户点击)
```

## 在线体验

公网访问(Cloudflare Tunnel 穿透本地服务):
**https://avenue-physical-introduction-par.trycloudflare.com**

一键启动(服务+隧道):`powershell -File start_public.ps1`

## 评委复现指南(3 分钟跑起来)

**环境要求**:Windows / macOS / Linux + Python 3.8 及以上,无任何其他依赖。

```bash
# 1. 解压源码,进入项目目录
cd codetutor

# 2. 安装依赖(仅 2 个纯 Python 库)
pip install requests flask

# 3. 启动(无需任何配置,无需 API Key)
python web_app.py
# 浏览器访问 http://127.0.0.1:5050
```

**无需 API Key 即可体验完整流程**:未配置 Key 时系统自动进入演示模式
(MockLLM 以真实沙箱结果驱动),诊断 / 沙箱验证 / 归档 / Web 界面全部真实可用。
推荐演示入口:`http://127.0.0.1:5050/?demo=0`(自动运行完整案例)。

**体验真实大模型能力**(可选):编辑 `config.py` 填入任意 OpenAI 兼容接口的 Key
(DeepSeek / 智谱 GLM 免费额度均可),重启服务即切换为真实模式。

**实验复现**:`python scripts/run_evaluation.py` 自动跑 10 个标准用例并生成评估报告。

常见问题:
- `python` 命令不存在 → 换用 `py`(Windows)或 `python3`(macOS/Linux);
- 端口被占用 → 修改 `web_app.py` 末尾 `port=5050` 为其他端口;
- 命令行体验 → `python main.py --demo`。

## 快速开始(开发者)

```bash
# 1. 安装依赖(仅 requests + flask)
pip install requests flask

# 2. 配置 LLM(可选):config.py 支持环境变量覆盖:
#    CODETUTOR_API_KEY / CODETUTOR_BASE_URL / CODETUTOR_MODEL
#    兼容端点:DeepSeek 官方 https://api.deepseek.com/v1(deepseek-chat)、
#    智谱 https://open.bigmodel.cn/api/paas/v4(glm-4-flash 免费)等

# 3. 启动 Web 界面
py web_app.py        # 浏览器访问 http://127.0.0.1:5050

# 4. 命令行模式
py main.py --demo                # 内置演示
py main.py --file bug.py -e "报错描述"
py main.py --stats               # 我的学情
py main.py --review              # 今日复习

# 5. 运行实验评估(生成 reports/evaluation_report.md)
py scripts/run_evaluation.py
```

> 未配置 API Key 时系统自动进入**演示模式**(MockLLM,以真实沙箱结果驱动),
> 完整流程与界面可正常体验;配置 Key 后即为完整真实能力。

## 目录结构

```
codetutor/
├── config.py               # 全局配置(LLM 接口/沙箱参数)
├── main.py                 # CLI 入口
├── web_app.py              # Flask Web 入口
├── codetutor/              # 核心包
│   ├── llm.py              #   LLM 客户端(真实 + Mock)
│   ├── prompts.py          #   提示词中心
│   ├── orchestrator.py     #   多智能体编排器
│   ├── agents/             #   诊断/修复/讲解/出题/档案 5 个 Agent
│   ├── tools/
│   │   ├── sandbox.py      #   代码沙箱(安检+隔离执行+超时+错误解析)
│   │   └── knowledge.py    #   报错知识库 TF-IDF 检索(RAG)
│   └── memory/
│       └── archive.py      #   SQLite 错题档案 + 艾宾浩斯复习调度
├── knowledge_base/         # 15 条 Python 高频报错模式(JSONL)
├── tests/                  # 10 个标准评估用例 + 冒烟测试
├── scripts/                # 实验评估脚本
└── reports/                # 评估报告输出
```

## 技术要点

| 技术 | 实现 |
|---|---|
| 多智能体编排 | 自研轻量流水线框架:5 个职责单一 Agent + 状态上下文传递 + 单环节失败降级 |
| 可验证修复 | 静态危险扫描 → `python -I` 隔离执行 → 超时强杀 → 原报错消除判定 → 失败反馈重试(≤2 次) |
| RAG 知识库 | 自建 15 条报错模式库,纯 Python TF-IDF 检索,引用条目全程可溯源 |
| 长期记忆 | SQLite 存储错题档案(错误类型/知识点/代码快照),艾宾浩斯 [1,2,4,7,15] 天复习调度 |
| LLM 接入 | OpenAI 兼容协议,支持 DeepSeek / 智谱 GLM / 通义等,结构化 JSON 输出约束 |
