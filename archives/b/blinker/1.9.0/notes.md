# blinker 1.9.0 适配笔记

## 编译环境
- 构建系统: python3（纯 Python 源码包）
- 编译日期: 2026-09-05
- 编译器: 未使用
- 状态: built

## 编译步骤
1. 从官方 PyPI sdist 获取 blinker 1.9.0。
2. 校验 SHA256：`b4ce2265a7abece45e7cc896e98dbebe6cead56bcf805a3d23136d145f5445bf`。
3. 将 `src/blinker` 复制到 Python site-packages 目录。
4. 将上游 `tests/test_context.py`、`tests/test_signals.py` 和 `tests/test_symbol.py` 随包保存到测试资源目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 初次 pytest 收集异步用例失败 | 测试环境未启用 pytest-asyncio 的 auto 模式 | 测试命令显式增加 `-o asyncio_mode=auto` |

## 源码修改
无。适配未修改上游源码。

## 依赖版本
- 运行时：Python >=3.9；上游 `requires_dist` 为空。
- 测试工具：pytest 8.3.3、pytest-asyncio 0.24.0。

## 验证结果

```text
上游测试：25 passed in 0.24s
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Python Conan 配方 |
| conandata.yml | 官方 PyPI sdist URL 与 SHA256 |
| test_package/ | 完整上游测试及 25 用例清单 |

## 注意事项
- blinker 是纯 Python noarch 包，不需要 C/C++ 编译器或第三方运行时库。
- test_package 必须安装并启用 pytest-asyncio，否则 `test_async_receiver` 无法执行。
---

**编译结束**: 2026-09-06 20:37
**最终状态**: built
