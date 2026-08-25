# parallel 20260522 适配笔记

## 编译环境

- 目标平台: OpenHarmony 6.0 arm64
- 软件类型: Perl 命令行工具
- 构建日期: 2026-08-24
- Conan 依赖: perl/5.42.2.1
- 状态: built

## 适配方案

1. 从 GNU 官方源获取 `parallel-20260522.tar.bz2` 并校验 SHA256。
2. 不运行 Autotools 安装流程，直接安装上游 Perl 命令脚本和 man page。
3. 用补丁将 `sql` 的硬编码 Perl shebang 改为 `/usr/bin/env perl`，由 Conan 的 perl 运行环境提供解释器。
4. 不打包依赖 Bash 的 `parset`，也不打包不支持 `--version`/`--help` 的内部辅助命令 `parcat`。
5. 通过 test_package 从 package_folder 执行真实 `parallel` 命令，并用耗时上限证明两个作业并发重叠。
6. 从固定上游标签 `20260522`（提交 `d913adb63fd4d8f28ed82cd9c519d0e017a763a2`）下载 SHA256 锁定的完整 Git 快照；测试前确认 `testsuite` 的 390/390 个文件均存在。PR 内同时保留 365 个可文本审阅的上游文件，二进制及隐藏夹具由完整快照无损承载。

## 测试分类

- 上游测试资源：390/390 个文件完整保留，其中包含 108 个测试脚本和 109 份预期输出。
- 上游测试执行：`tests-to-run/*.sh` 的 108/108 个原始脚本全部实际调用，未执行项为 0；逐脚本与未修改的 `wanted-results` 比对。
- 上游严格结果：13 个脚本输出完全匹配，95 个脚本因 OHOS Conan Worker 缺少上游专用测试环境而阻塞，0 个普通输出差异，严格通过率为 13/108（12.04%）。
- 新增 OHOS 测试：2 项，分别为包许可证完整性测试和打包 CLI 并发消费者集成测试，结果 2/2 通过。
- 资源完整性检查不重复计作测试用例；CLI 的版本与并发断言属于同一消费者工作流，不拆分虚增用例数。

## 上游测试环境限制

95 个环境阻塞项均已真实启动并记录，不计为通过，也未通过修改预期值、删除测试、统一 `skip` 或筛选用例掩盖：

- 上游 `REQUIREMENTS` 依赖 Debian 测试主机上的 `stdout`、`G`、`field`、`pv`、`expect`、`tcsh`、`gawk`、多语言运行时及数据库驱动。
- SSH/虚拟化测试依赖预配置的 CentOS、FreeBSD、OpenIndiana、macOS、Android、Vagrant 和 VirtualBox 主机。
- SQL 测试依赖 PostgreSQL、MySQL、Oracle、SQLite 驱动、凭据及运行中的数据库服务。
- 部分测试需要 `sudo`、内核模块、服务控制、主机安装、无限制可写 `/tmp` 或多 GiB 内存/磁盘。
- 100s/300s、超大输出和交互测试受 Worker 非交互、资源和时限约束；执行器仍调用原始脚本并记录超时或依赖失败。

逐项结果保存在 Conan 构建目录的 `upstream_test_results/summary.tsv`，每一行记录脚本、状态、退出码、耗时和原因。

## 验证结果

```text
PASS: retained complete upstream testsuite (390/390 files)
RUN: all upstream test scripts (108/108 scripts, 109 wanted-results)
PASS: Conan Perl runtime modules loaded
UPSTREAM_ALL_SUMMARY executed=108 passed=13 failed=0 blocked_env=95 missing_expected=0
```

消费者测试使用两个 worker 执行两个各耗时 3 秒的作业，断言总耗时低于 5.5 秒并校验输出为 `1 2`，从而证明作业确实重叠执行。上游 108 项与新增 OHOS 2 项共实际执行 110 项。

## 打包产物

- `bin/parallel`
- `bin/sem`
- `bin/sql`
- `share/man/man1/*.1`
- `share/doc/parallel/README`
- `licenses/GPL-3.0-or-later.txt`
---

**编译结束**: 2026-08-22 18:00
**最终状态**: built
