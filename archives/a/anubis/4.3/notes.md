# anubis 4.3 适配笔记

## W0/W0b/W1 与来源

- 官方源：`https://ftp.gnu.org/gnu/anubis/anubis-4.3.tar.gz`
- SHA256：`ff0af3337c462218e5ee244c7ef90188af9efdf095bc05b6333401cf9882af2c`
- W0：`preflight_check.sh anubis/4.3` 在生成配方前通过；生成配方声明无第三方依赖。
- W0b：`upstream/main` 没有 `archives/a/anubis` 历史归档或 `notes.md`。
- W1：worktree 从 `upstream/main` `a675263b91fd9cef49cbce7aafb54062ae10df2c` 创建，分支为 `feat/anubis-4.3`。

## 构建与配方

- 构建系统：Autotools；包类型：application；上游 sbin 产物在 `package()` 中归一到 Conan `bin/anubis`。
- configure 使用 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，实际编译器来自 OHOS Conan profile。
- 显式关闭 GPGME、GnuTLS、Guile、GSASL、MySQL、PostgreSQL、PCRE、PAM、SOCKS 和 TCP-wrapper 可选集成；核心包无 Conan 依赖。
- `MAKEINFO=/bin/true` 只避免设备缺少 makeinfo 时刷新上游已提供的 `anubis.info`，不跳过 `make check`。

## 问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `config.status` 无法创建 `confXXXXXX/subs1.awk` | HMDFS 对 `umask 077` 创建的目录不可写 | 通过 `refresh-patch --auto` 生成 `0001-configure.patch`，将两个临时目录创建点改为 `umask 022` |
| 2 | `tests/mta.c` 中 `u_char` 未定义 | OHOS libc 不提供该旧 typedef | 生成 `0002-tests-mta.c.patch`，仅将两个字符分类转换改为 `unsigned char` |
| 3 | `make check` 文档阶段找不到 `makeinfo` | 设备没有 Texinfo 工具，且版本文件更新时间触发文档刷新 | make 命令显式传 `MAKEINFO=/bin/true`，继续执行完整测试目标 |
| 4 | 旧式 Autotest 没有 `# TOTAL` 汇总块 | Anubis 4.3 输出“tests were successful/skipped”格式 | recipe 同时解析两种汇总格式，并校验注册数为 27 |
| 5 | consumer test 的 `popen/pclose` 在严格 C99 下未声明 | OHOS libc 的 POSIX 声明需要 feature macro | test_package/test.c 增加 `_GNU_SOURCE` |

## 补丁与上游测试修改

- `0001-configure.patch`：构建可移植性修复，作用于上游生成的 `configure`。
- `0002-tests-mta.c.patch`：上游测试辅助程序的 OHOS 兼容修复；未删除测试、未改变测试语义。

## 四维测试账本

| 维度 | 数量 | 证据 |
|---|---:|---|
| 上游静态声明 `N_static` | 27 | `tests/*.at` 中 `AT_SETUP` 逐项统计 |
| 构建系统注册 `N_registered` | 27 | `make -j1 MAKEINFO=/bin/true check` 输出 1-27 |
| 实际执行 `N_executed` | 20 | Autotest 汇总 |
| 通过/失败/跳过 | 20 / 0 / 7 | GPG 3、TLS 1、Guile 2、anubisusr 1 为 feature-gated skip |
| 新增消费者程序 `N_consumer` | 1 | `test_package/test.c` |
| 消费者断言 `N_assertion` | 2 | `--version` 与 `--show-config-options`，2/2 通过 |

## 路径判断

- 走路径 A，不走路径 B：本轮新增内容是 anubis 4.3 的归档适配与两处版本/平台修复；已检索 `适配经验汇总.md`，未命中 anubis/u_char/旧式 Autotest 汇总的既有条目，当前证据尚不足以形成独立跨仓库知识主题，也未创建知识扩展 Issue。
- 不走路径 C：不存在私有系统接口、闭源二进制、汇编或超大依赖链资质。

## 验证结果

- 最终 Conan 验证：G1/G2/G3/G4/L2/L4/L5 通过。
- 上游测试：27/27 注册，20/20 执行项通过，7 项因显式关闭的可选能力跳过，0 失败。
- 消费者测试：1/1 程序通过，2/2 断言通过。
- finish 的通用 G0 clean-verify 曾因 HNP bash 在临时 HMDFS 目录 `getcwd` 失败并传入空 host 而失败；recipe 级 Conan W3 已使用 `/bin/sh`、正确 host tuple、两份补丁并通过。该 G0 非阻塞结果保留在设备日志中。

## 交付物

- `conanfile.py`、`conandata.yml`、`patches/0001-configure.patch`、`patches/0002-tests-mta.c.patch`
- `test_package/conanfile.py`、`test_package/test.c`、`test_package/MANIFEST.yml`
- 软件级 `manifest.yaml`、`README.md`、`commands.json`
---

**编译结束**: 2026-09-13 13:15
**最终状态**: built
