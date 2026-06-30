# libcddb 1.3.2 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published
- 补丁: 2 个（精简后，原 4 个）
- 依赖: libiconv/2.6.1

## 补丁精简分析（⭐ 4→2）

### 删除的补丁

| 补丁 | 删除理由 |
|------|----------|
| 0001-tests-settings.sh.patch | ❌ **违反 R6**: settings.sh 是 configure 从 settings.sh.in 自动生成的文件（使用 `@abs_top_builddir@/@abs_srcdir@` 变量），configure 会自动生成正确版本 |
| 0004-include-cddb-version.h.patch | ❌ **违反 R6**: version.h 是 configure 从 version.h.in 自动生成的文件（使用 `@VERSION@ @build@` 变量），config.guess 更新后 configure 自动生成 `CDDB_VERSION "1.3.2 aarch64-unknown-linux-ohos"` |

### 保留的补丁

| 补丁 | 保留理由 |
|------|----------|
| 0001-config.guess.patch（原0002） | ✅ **必要平台适配**: 更新 2008→2023 版，识别 aarch64-unknown-linux-ohos |
| 0002-config.sub.patch（原0003） | ✅ **必要平台适配**: 更新 2008→2023 版，识别 aarch64-unknown-linux-ohos |

### 验证依据

- configure 生成的 version.h: `CDDB_VERSION "1.3.2 aarch64-unknown-linux-ohos"` ✅
- configure 生成的 settings.sh: 正确的绝对路径 ✅
- config.guess 输出: `aarch64-unknown-linux-ohos` ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别平台 | 2008 版不识别 OHOS | 更新到 2023 版 |
| 2 | make check 3/5 测试失败 | 需网络连接CDDB服务器 | 离线环境预期失败 |
| 3 | cddb_log.h header guard 错误 | `#ifndef CDDB_LOH_H` 应为 `CDDB_LOG_H` | 上游 bug，不影响功能 |

## 上游 Bug

- cddb_log.h header guard 拼写错误（`CDDB_LOH_H` vs `CDDB_LOG_H`），编译产生 `-Wheader-guard` 警告，不影响功能

## 交付物

| 文件 | 说明 |
|------|------|
| libcddb-1.3.2-ohos-aarch64.tar.gz | 预编译包 |
| libcddb-1.3.2-ohos-aarch64-debug.tar.gz | debug 包 |

## 注意事项

1. libcddb.so 依赖 libiconv.so.2，打包中包含在 lib/external/
2. libcddb.so RUNPATH: `$ORIGIN:$ORIGIN/external`（打包中正确）
3. 补丁已从 4 个精简为 2 个（删除了 settings.sh 和 version.h 生成文件 patch）

---

**编译结束**: 2026-06-01 14:48
**最终状态**: published
