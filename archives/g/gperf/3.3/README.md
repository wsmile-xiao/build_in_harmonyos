# gperf 3.3 — 鸿蒙 PC conan 制品

GNU gperf（**完美哈希函数生成器**）：给定关键字列表，生成无冲突的 C/C++ 查找代码。

> **下游用途**：eudev 的**硬构建依赖**。eudev 构建期由 `keyboard-keys.txt` 经 AWK
> 生成 `keyboard-keys-from-name.gperf`，再由 gperf 生成 `keyboard-keys-from-name.h`
> （列入 `BUILT_SOURCES`）—— **无法从 tarball 绕过**（官方 eudev tarball 既不含
> `.gperf` 也不含 `.h`）。故本包是 eudev（及 apt 的 `find_package(Udev)` 链）的前置。

## 出包（鸿蒙 PC）

```bash
conan create archives/g/gperf/3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 源

```
https://ftp.gnu.org/gnu/gperf/gperf-3.3.tar.gz
sha256 fd87e0aba7e43ae054837afd6cd4db03a3f2693deb3619085e6ed9d8d9604ad8   (1831294 字节)
```

> 可用版本（ftp.gnu.org/gnu/gperf/）：`3.0.3` / `3.0.4` / `3.1` / `3.2` / `3.2.1` / **`3.3`**
> （镜像 `ftpmirror.gnu.org/gperf/` 内容相同）

## OHOS 适配要点

| # | 措施 | 原因 |
|---|------|------|
| 1 | **仅需 `config.guess` 的 HarmonyOS patch** | gperf 3.3 的 `build-aux/config.sub` **已原生支持** `linux-ohos*`（实测 `config.sub aarch64-unknown-linux-ohos` 直接通过）→ 无需为 config.sub 生成 patch。**动手前先实测**，避免无谓补丁（本库最终只 1 个 patch，而非常规 2 个）|
| 2 | `TMPDIR` 指向 conan build 目录 | main 上 3.1 的 notes 记录：**HMDFS 会令 configure 的 heredoc 创建临时文件失败**，当时被迫**手工生成 `Makefile` / `config.h`** 绕过。本配方改走标准 autotools 流程 |
| 3 | `configure` 内 `umask 077` → `022` | HMDFS 上临时文件权限异常 |

## 测试

`test_package/test_gperf.sh` **真实执行**：

1. `gperf --version` —— 断言版本号 `3.3`
2. **用真实 `.gperf` 输入生成 C 代码** —— 断言生成物含预期符号
   （直接证明它具备 eudev 所需的「由关键字表生成查找表」能力，而非仅能打印版本号）

上游测试：gperf 自带 `tests/`（含 `5000.gperf` / `ada.gperf` / `c++.gperf` 等 `.gperf`
输入与 `.exp` 期望输出）；本配方构建阶段只出工具本体，未启用 `make check` ——
工具的等价能力已由 test_package 的真实生成验证覆盖。

## 产物

只安装 `bin/gperf`（构建工具，无库/头）。`cpp_info` 的 `libdirs` / `includedirs`
为空；下游（如 eudev）通过 `PATH` 使用它，而非链接。
