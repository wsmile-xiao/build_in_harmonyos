# xapian-core 1.4.22 适配笔记

## 概述

xapian-core 是 Xapian 搜索引擎核心库，提供文档索引、查询、排序和匹配等 C++ API。本配方适配上游 1.4.22 版本，使用 Autotools 构建路径并补齐 HarmonyOS 平台识别、UUID 生成和测试脚本兼容处理。

## 适配要点

- 使用官方 release 包 `xapian-core-1.4.22.tar.xz`。
- 依赖 `zlib/1.3.1.1`。
- Autotools 配置参数：
  - `--disable-documentation`
  - `--disable-dependency-tracking`
- HarmonyOS 兼容处理：
  - `config.guess` 识别 HarmonyOS/linux-ohos。
  - `config.sub` 接受 linux-ohos triplet。
  - UUID 生成在 `/proc/sys/kernel/random/uuid` 不可用时 fallback 到 `/dev/urandom`。
  - 上游测试脚本使用配置 shell，避免硬编码 `/bin/sh`。
  - lockfile umask 测试改为按运行时实际 probe 文件权限判断，兼容 OHOS storage 权限掩码。
- OHOS 构建阶段显式注入 `clang`、`clang++`、`llvm-ar`、`llvm-ranlib`、`llvm-nm` 等工具。
- 兜底修复空 `include/xapian/version.h`，确保 `XAPIAN_VERSION`、`XAPIAN_REVISION` 和后端宏可用。

## 测试

- 上游测试入口：`make check`。
- test_package：
  - 构建 C++ smoke 程序。
  - 创建 in-memory database。
  - 添加文档并查询。
  - 校验匹配数量、文档内容和 `Xapian::version_string() == "1.4.22"`。

## 真机验证结果

验证命令：

```bash
conan create archives/x/xapian-core/1.4.22 --profile=ohos-aarch64 --build=missing
```

验证结论：

- `conan create`：EXIT=0。
- `configure`：通过。
- `make`：通过。
- `make check`：通过。
- `test_package build`：通过，`[100%] Built target test_xapian_core`。
- `test_package test`：通过，输出 `xapian-core smoke test passed: 1.4.22`。
