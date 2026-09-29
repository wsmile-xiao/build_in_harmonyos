# libmowgli-2 2.1.3 适配笔记

## 编译环境
- 构建系统: autotools（顶层 Makefile 含 buildsys.mk，须 in-source 构建）
- 编译日期: 2026-09-27
- 编译器: clang/clang++（ohos-aarch64 profile）
- 状态: built

## 编译步骤

1. `init-build` 下载官方 tarball（codeload.github.com/atheme/libmowgli-2/tar.gz/refs/tags/v2.1.3，SHA-256=b7faab2fb9f46366a52b51443054a2ed4ecdd04774c65754bf807c5e9bdda477，与 GitHub API 标签 v2.1.3 核验一致）。
2. `conan-init` 生成 conanfile.py + conandata.yml + test_package/。
3. `conan-verify` 8 道门禁：G0-G4 + L2/L4/L5 全部通过，生成补丁 2 个。
4. `finish built`：W2 结构检查、R36 依赖检查（无外部依赖）、W3 本地 conan create 均通过，写入 .ci-result.json（exit_code=0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 创建临时目录失败 | HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX` 权限语义受限 | 补丁 0001：configure 中 umask 077 → 022 |
| 2 | `_SC_LEVEL1_DCACHE_LINESIZE` 未定义 | OHOS 平台缺少该 sysconf 常量 | 补丁 0002：cacheline.c 增加 `#ifdef _SC_LEVEL1_DCACHE_LINESIZE`，否则回退 64 |

## 源码修改

- `patches/0001-configure.patch`：configure 临时目录 umask 077→022（HMDFS 兼容）。
- `patches/0002-src-libmowgli-platform-cacheline.c.patch`：cacheline_size 获取兼容 OHOS（sysconf 常量缺失回退 64）。

## 依赖版本

- 无外部第三方依赖（libmowgli-2 仅依赖 libc/POSIX）。

## 验证结果

- conan create 成功（reports/conan-create.log，SHA-256 记录于 .ci-result.json）。
- test_package 消费者测试：调用 mowgli_string_create/append/append_char、mowgli_strlcpy、mowgli_alloc/free 并断言，4 组断言全部通过（test.c）。
- 上游未提供测试套件：源码包无 test/ 目录，make check 无目标（MANIFEST.yml 已记录清点证据）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 2190 | Conan 配方（Autotools，静态库） |
| conandata.yml | 546 | 源码 URL + SHA-256 + 补丁声明 |
| patches/0001-configure.patch | 853 | configure umask 修复 |
| patches/0002-src-libmowgli-platform-cacheline.c.patch | 752 | cacheline OHOS 兼容 |
| test_package/ | - | 消费者测试（conanfile.py + test.c + CMakeLists.txt + MANIFEST.yml） |
| reports/conan-verify-report.md | 1451 | 门禁验证报告 |
| reports/w3-local-ci.log | 59906 | W3 本地 CI 日志 |

## 注意事项

- 顶层 Makefile 是源码静态文件（include buildsys.mk），必须 in-source 构建（conanfile.py layout 已设 `self.folders.build = "."`）。
- 静态库（`--enable-static --disable-shared`），`--build=aarch64-linux-gnu` 覆盖 2014 版 config.guess 无法识别 HarmonyOS 的问题。
---

**编译结束**: 2026-09-27 21:12
**最终状态**: built
