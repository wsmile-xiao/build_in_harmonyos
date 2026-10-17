# mlogger 1.2.0 适配笔记

## 编译环境
- 构建系统: makefile（单文件 C，无 configure）
- 编译日期: 2026-08-31
- 编译器: clang/clang++
- 状态: built

## 上游身份核实

同名项目众多，必须按"版本号 + 语言 + 版本历史"三重确认，避免选错：

| 候选仓库 | 语言 | 版本 | 判定 |
|----------|------|------|------|
| **nbrownus/mlogger** | **C** | **1.2.0 (tag v1.2.0)** | ✅ 正确上游 |
| oval-group/mlogger | Python | v1.0a (prerelease) | ❌ 无 1.2.0 版本 |
| mortie/mlogger | node.js | 无 release tag | ❌ 无 1.2.0 版本 |
| masuldev/mlogger | Go | 无 release tag | ❌ 无 1.2.0 版本 |
| DeNA/m_logger | Ruby gem | 无 1.2.0 版本 | ❌ 名称不同(m_logger) |

**结论**：唯一发布过 `1.2.0` 版本且语言为 C 的是 `nbrownus/mlogger`，Repology
与 Homebrew 均确认其 stable 版本为 `1.2.0`，上游主页为
`https://github.com/nbrownus/mlogger`，是 BSD-4-Clause-UC 许可的命令行 syslog 工具。

## 编译步骤

1. 下载官方 tag 归档：
   `https://github.com/nbrownus/mlogger/archive/refs/tags/v1.2.0.tar.gz`
2. 解压得 `mlogger-1.2.0/`（顶层 7 文件：mlogger.c / Makefile / README.md /
   RELEASE.md / package.sh / docs/mlogger.1.ronn / debian/）
3. 用 OHOS AArch64 clang 直接编译单文件（沿用上游 Makefile 的编译命令，
   仅把 gcc 换成 Conan conf 提供的 clang）：
   `clang -Wall -Wextra -O3 -o mlogger mlogger.c`
4. 产物为单个 ELF 可执行文件 `mlogger`，安装到 `bin/`。

无 configure、无 make install target，package() 直接 copy 二进制到 `bin/`。

## 上游测试核查

完整证据（任务要求"没有测试则给出完整证据"）：

- `tests/` 目录：不存在
- `test/` 目录：不存在
- examples 是否被测试系统注册：不存在 examples 目录，也无任何测试注册
- Makefile 目标：仅 `all` / `clean` / `docs` / `.PHONY: docs`，
  **无 `test` / `check` / `ctest` 目标**（`grep -niE 'test|check|ctest' Makefile` 无匹配）
- CMake/Meson：不存在（非 CMake/Meson 项目）
- `TESTS` / `check_PROGRAMS`：不存在（非 autotools 项目）
- `make check` / `make test`：Makefile 无此目标，运行会报 `No rule to make target 'check'`
- `ctest`：无 CTest 配置
- CI 配置：无 `.github/` / `.gitlab-ci.yml` / `.travis.yml` 等任何 CI 配置
- debian/rules：标准 debhelper，`override_dh_auto_build` 仅 `dh_auto_build -- docs mlogger`，
  **无 `override_dh_auto_test`**（即 debhelper 默认 `dh_auto_test` 会因无测试而 no-op）

**结论：上游无任何测试套件。test_package 为消费者验证，不替代上游测试
（见任务 #7 的单独报告）。**

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 环境网络策略 | 改用 codeload.github.com 镜像下载成功 |
| 2 | 上游 Makefile 硬编码 `gcc` | 上游仅面向 Linux | 配方中用 Conan conf 的 clang 替代，不改源码 |

零 patch：mlogger.c 仅依赖 POSIX/sys/socket/getopt/err.h/syslog.h 等标准头文件，
在 OHOS AArch64 musl + libc++ 下原生编译通过，**无任何 musl/libc++ 兼容问题，
不需补丁**。

## 源码修改

无补丁（patches: []）。未修改任何上游源文件。

## 依赖版本

- 编译依赖：无（仅需 clang，单文件 C，链接 libc）
- 运行依赖：系统 syslog 守护进程（OHOS 默认环境具备）或 `-s` 输出到 stderr

## 验证结果

```bash
# 编译验证（OHOS AArch64 clang）
clang -Wall -Wextra -O3 -o mlogger mlogger.c   # 成功，无 warning/error
file mlogger                                     # ELF 64-bit LSB executable, ARM aarch64
readelf -d mlogger | grep NEEDED                # 依赖: libc.so / libsys_param.so 等 OHOS 系统库
mlogger --version                                # 输出: mlogger 1.1.2（上游硬编码常量）
mlogger -s -t TESTTAG "hello from test"         # -s 输出到 stderr，可确定性捕获
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mlogger | 单个 ELF64 AArch64 可执行文件 |

## 注意事项

- `--version` 输出 `mlogger 1.1.2` 而非 `1.2.0`：这是上游 `PROGRAM_VERSION` 常量
  硬编码为 `"1.1.2"` 的真实行为（tag 是 1.2.0，源码常量未更新），测试据此断言，
  不修改源码常量。
- mlogger 是 CLI 工具（application），非库；`cpp_info.libs=[]`，`bindirs=["bin"]`，
  需声明 commands.json（R38）。
