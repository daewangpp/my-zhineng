# CodeTutor 实验评估报告

- 评估时间:2026-09-19 20:36
- 模式:真实 LLM
- 用例数:40(报错类 20 / 逻辑类 15 / 综合类 5,含 4 个正确代码用例)
- 总耗时:3447 秒

## 总体指标

| 指标 | 结果 | 说明 |
|---|---|---|
| 诊断准确率 | **35/36 = 97%** | 错误类型与标准答案匹配 |
| 修复正确率(客观断言) | **40/40 = 100%** | 修复代码沙箱真实运行,输出逐字符比对作者编写的标准输出 |
| 系统自报验证通过率 | 40/40 = 100% | 系统内双轨验证(不报错+输出断言)判定通过 |
| **误报数** | **0(必须=0)** | 自报通过但客观判定错误 —— 假阳性,零容忍 |
| 诚实标记数 | 0 | 客观失败且系统如实标记未通过 |
| 修复平均尝试次数 | 0.90 次 | 沙箱反馈重试机制有效性 |

## 分用例明细

| 用例 | 诊断类型 | 期望类型 | 诊断 | 客观修复 | 自报验证 | 自报vs客观 | 重试 |
|---|---|---|---|---|---|---|---|
| A01 列表索引越界 | IndexError | IndexError | ✔ | ✔ | ✔ | 一致 | 1 |
| A02 字典键不存在 | KeyError | KeyError | ✔ | ✔ | ✔ | 一致 | 2 |
| A03 字符串数字混合运算 | NoError | TypeError | ✘ | ✔ | ✔ | 一致 | 0 |
| A04 sort() 返回值误用 | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A05 递归缺少基例 | RecursionError | RecursionError | ✔ | ✔ | ✔ | 一致 | 1 |
| A06 除零错误 | ZeroDivisionError | ZeroDivisionError | ✔ | ✔ | ✔ | 一致 | 1 |
| A07 变量未定义 | NoError | - | —(正确代码) | ✔ | ✔ | 一致 | 0 |
| A08 对 None 调用 append | AttributeError | AttributeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A09 缩进错误 | IndentationError | IndentationError | ✔ | ✔ | ✔ | 一致 | 1 |
| A10 字符串不可变修改 | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A11 int() 转换失败 | ValueError | ValueError | ✔ | ✔ | ✔ | 一致 | 1 |
| A12 对整数取 len | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A13 空列表取首元素 | IndexError | IndexError | ✔ | ✔ | ✔ | 一致 | 1 |
| A14 函数内修改全局变量 | UnboundLocalError | UnboundLocalError | ✔ | ✔ | ✔ | 一致 | 1 |
| A15 字符串拼接整数 | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A16 format 参数不足 | IndexError | IndexError | ✔ | ✔ | ✔ | 一致 | 1 |
| A17 修改元组元素 | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A18 字典键大小写错误 | KeyError | KeyError | ✔ | ✔ | ✔ | 一致 | 1 |
| A19 变量遮蔽内置函数 | TypeError | TypeError | ✔ | ✔ | ✔ | 一致 | 1 |
| A20 字典遍历时删除 | RuntimeError | RuntimeError | ✔ | ✔ | ✔ | 一致 | 1 |
| B01 可变默认参数陷阱 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B02 遍历时删除列表元素 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B03 列表别名而非拷贝 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B04 差一错误 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B05 is 与 == 混用 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B06 整数除法误用 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B07 类变量被所有实例共享 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B08 字符串 replace 未接收返回值 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B09 return 缩进位置错误 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B10 最大值初始值错误 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B11 闭包捕获循环变量 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B12 空列表布尔判断 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B13 累乘初始值为 0 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B14 嵌套列表浅拷贝 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| B15 循环内重复初始化累加器 | NoError | - | —(正确代码) | ✔ | ✔ | 一致 | 0 |
| C01 冒泡排序边界错误 | NoError | - | —(正确代码) | ✔ | ✔ | 一致 | 0 |
| C02 双错误混合 | IndexError | IndexError | ✔ | ✔ | ✔ | 一致 | 1 |
| C03 字符串格式化类型错误 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| C04 计数器未正确累加 | LogicError | LogicError | ✔ | ✔ | ✔ | 一致 | 1 |
| C05 找最大值索引错误 | NoError | - | —(正确代码) | ✔ | ✔ | 一致 | 0 |

## 结论
1. 修复正确性以**作者编写的客观输出断言**为准,不采信系统自报;
2. 误报数必须保持 0 —— '可验证修复'机制承诺:凡标记✔的修复,输出必然与预期逐字符一致;
3. 含 4 个正确代码用例用于考察误诊率;修复失败用例均被如实标记,不静默交付。