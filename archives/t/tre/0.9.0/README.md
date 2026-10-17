# TRE 0.9.0 — 鸿蒙 (OpenHarmony) aarch64 适配

TRE 是一个轻量级、兼容 POSIX 的正则表达式库，支持近似（模糊）匹配和 agrep CLI 工具。

## 当前版本

- 软件版本: 0.9.0
- 构建日期: 2026-07-28
- 构建系统: autotools（configure + make）
- 编译器: clang 15（OHOS aarch64）
- 状态: built
- 上游: https://github.com/laurikari/tre

## Conan 配方

v8.7 配方（`conanfile.py` + `conandata.yml` + `test_package/`）

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

### 补丁

- 0001-config.sub.patch — E007: aarch64-linux-ohos triplet 支持
- 0002-configure.patch — E097: HMDFS umask 077→022 + TMPDIR mktemp

### 验证

- conan create: PASS (100% tests passed)
- make check: 3/4 套件通过（wretest 4/53447 locale 限制）

### 产物

- libtre.a / libtre.so
- tre.h / regex.h / tre.pc
- agrep（近似 grep 命令行工具）
