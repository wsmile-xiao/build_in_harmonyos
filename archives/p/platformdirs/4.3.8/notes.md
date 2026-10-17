# platformdirs 4.3.8 适配笔记

## 编译环境
- 类型：纯 Python noarch
- 编译日期：2026-09-02
- Python：3.12
- 平台：OHOS arm64
- 状态：built

## 编译步骤
```bash
conan create archives/p/platformdirs/4.3.8 --build=missing
```
配方使用 `python-require` 类型，直接将 `src/platformdirs` 复制到 `lib/python3.12/site-packages`，不运行 Hatchling wheel 构建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | Conan 包 ID 报 `settings.os.version` 未定义 | OHOS profile 不提供该设置 | 在 recipe 和 test_package 中使用 `self.settings.rm_safe("os.version")` |
| 2 | pytest 临时目录 fixture 失败 | `/tmp` 只读且共享目录 UID 映射不一致 | 使用 `/data/storage/el2/base/cache` 并显式指定 `--basetemp` |

## 源码修改
无。

## 依赖版本
- 本配方按仓库现有 OHOS Python 3.12 运行时布局安装到 `lib/python3.12/site-packages`，不宣称跨 Python 小版本兼容。

## 验证结果
```text
PYTHONPATH=src python3 -m pytest tests -q --basetemp=/data/storage/el2/base/cache/platformdirs-pytest/base
446 passed, 36 skipped
conan create archives/p/platformdirs/4.3.8 --build=missing
消费者测试：OK
```

## 注意事项
上游 482 个用例中 36 个为非 Unix 平台参数化跳过项；全部可运行的 Unix/API 用例通过。
---

**编译结束**: 2026-09-02 11:33
**最终状态**: built
