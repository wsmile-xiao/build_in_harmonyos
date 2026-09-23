# trurl

> curl 官方 URL 解析与改写命令行工具（tr for URLs）。

## 简介

trurl 是 curl 官方出品的小型命令行工具，用于解析、抽取与改写 URL。
它复用 libcurl 的 URL 解析器（与 curl 命令行行为完全一致），
面向 shell 脚本作者：抽取 scheme/host/port/path/query 等组件、
改写 host、追加查询参数等都可离线完成，无需发起网络请求。

0.16.1（2025-05-12）为当前上游最新 release，本次适配采用 CMake 构建，
仅依赖仓库内已沉淀的 `curl/8.15.0`（提供 libcurl）。

## OHOS 适配要点

- CMake 构建：`TRURL_MANUAL=OFF`（免 Perl man 页依赖）、
  `TRURL_COMPLETION_ZSH=OFF`、`TRURL_TESTS=OFF` 后在 `build()` 内
  手动运行上游 `test.py` 并解析机器证据，避免 CMake 测试目标对
  Python 查找的强依赖。
- 上游测试为 Python 驱动（`test.py` + `tests.json`），真机用
  `HMBS_PYTHON3`/`python3` 运行 `--trurl=<构建产物>`，解析
  `Failed/Passed/Skipped/Total` 并输出 `HMBS_UPSTREAM_TEST_RESULT`。
- 纯命令行包（`package_type = "application"`），只交付 `bin/trurl`，
  不提供开发库；`test_package` 用 POSIX shell 离线断言 6 项真实
  URL 解析/改写行为。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| curl | 8.15.0 | 提供 libcurl（含头文件与共享库），trurl 唯一构建依赖 |

## 功能验证

```bash
trurl --url https://curl.se/we/are.html --get '{path}'
# 期望输出: /we/are.html
trurl --url https://curl.se --set host=example.com
# 期望输出: https://example.com/
trurl --version
# 期望输出: trurl version 0.16.1（含 libcurl 版本与特性列表）
```

## 参考

- [官方文档](https://curl.se/trurl/)
- [源码仓库](https://github.com/curl/trurl)
- [0.16.1 Release](https://github.com/curl/trurl/releases/tag/trurl-0.16.1)
