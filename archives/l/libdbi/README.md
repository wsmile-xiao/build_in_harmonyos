# libdbi — Database Independent Abstraction Layer

libdbi implements a database-independent abstraction layer in C, similar to the DBI/DBD layer in Perl.

## Available Versions

| Version | Status | Date |
|---------|--------|------|
| 0.9.0-r5 | built | 2026-06-02 |

## Description

libdbi provides a database-independent abstraction layer for writing database applications in C. It provides a simple and clean API that allows developers to use different database backends without changing their code.

## Dependencies

None (pure C library, only requires libc).

## Links

- Source: https://sourceforge.net/projects/libdbi/
- License: LGPL-2.1

## HarmonyOS Compatibility

- ✅ 编译成功（autotools + clang 15.0.4）
- ✅ ELF 签名完整（.note.ohos.ident + .codesign）
- ✅ pkg-config 元数据正确
- ✅ 核心库 API 功能正常
- ⚠️ dbi_initialize_r 需指定驱动目录（默认路径不存在）

## Known Limitations

1. `dbi_initialize_r(NULL, &inst)` 返回 -1：默认驱动目录 `/usr/lib/dbd/` 在鸿蒙平台不存在，需安装驱动插件或指定路径
2. 旧式 API (`dbi_initialize`, `dbi_shutdown`) 已标记 deprecated，推荐使用 `_r` 线程安全版本
3. ldconfig 不可用，共享库通过 LD_LIBRARY_PATH 或 RPATH 定位
