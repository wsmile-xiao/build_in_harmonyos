# wcwidth 0.2.12 测试报告

- 项目：wcwidth 0.2.12
- 测试日期：2026-09-02
- 测试环境：HarmonyOS Conan OHOS aarch64 profile
- 测试类型：上游 pytest 官方测试套件 + Conan 消费者测试

## 测试摘要

| 指标 | 数值 | 百分比 |
|---|---:|---:|
| 上游测试总数 | 36 | 100% |
| 上游通过 | 36 | 100% |
| 上游失败 | 0 | 0% |
| 上游跳过 | 0 | 0% |
| 消费者断言 | 6 | 100% |
| 消费者通过 | 6 | 100% |

## 测试命令与结果

```text
python3 -m pytest -o addopts='' -q
36 passed in 0.09s

python3 test_package/test_wcwidth.py
wcwidth consumer checks: 6/6 passed
```

Conan `conan-verify` 的 G1、G2、G3、G4、L2、L4、L5 全部通过；W3 本地 CI 模拟通过。

## 测试结论

✅ 纯 Python 包构建、安装和消费者导入验证通过。未修改上游测试源码、断言或测试数据。

## 已知限制

上游 tox.ini 默认包含 pytest-cov 参数；当前环境未安装 pytest-cov，因此使用 `-o addopts=''` 禁用仅覆盖率相关的默认参数。该操作不改变测试逻辑，36 个上游测试仍全部执行。
