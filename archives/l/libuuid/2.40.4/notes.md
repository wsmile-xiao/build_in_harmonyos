# libuuid 2.40.4 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (15.0.4)
- 目标平台: HarmonyOS PC (aarch64-linux-ohos)
- 状态: built

## 编译步骤

1. 下载 util-linux 2.40.4 官方源码 tarball（kernel.org 镜像，SHA-256 已核验）
2. 配置：`./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --disable-all-programs --enable-libuuid --without-python --disable-makeinstall-chown --disable-makeinstall-setuid --enable-static --disable-shared`
3. 编译：`make -j1`
4. 构建并运行上游测试：`make test_uuid_parser`（14 断言全部通过）
5. 手工编译运行 test_uuid_namespace helper（7 断言全部通过）
6. test_package 消费者验证：`conan create` 内 CMake 构建 + 运行 test_uuid（公开 API 全通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 平台检测不支持 OHOS | 显式传递 --build 和 --host 三元组 |
| 2 | config.status 无法创建临时文件 | HMDFS 上 `umask 077 && mkdir` 创建的 0700 目录仅 owner 可写，而构建进程 uid 与文件 owner 不同 | 补丁 0001 将 ac_tmp 改到 TMPDIR，且**不用 umask 077** 创建（0700 目录在 HMDFS 上不可写） |
| 3 | 上游 make check 全量测试的部分脚本依赖命令行工具 | uuidgen/uuidd/uuidparse 工具在 --disable-all-programs 下不构建 | 只影响 ts 包装脚本（oids/uuidgen/uuidparse/uuidd），非独立用例；libuuid 库自身测试入口全部运行通过 |
| 4 | /tmp 只读 | HMDFS 平台限制 | 编译与运行使用 $HOME 下可写目录 |

## 源码修改

补丁 0001-configure-use-tmpdir-for-config-status.patch：修改 configure 中 ac_tmp 赋值，
使用 `${TMPDIR:-$tmp}/config-status-tmp` 替代当前目录，且创建时不带 umask 077
（HMDFS 上 0700 目录对构建进程不可写，config.status 会 Permission denied）。

## 测试台账（双口径）

- 上游独立用例: test_uuid_parser（14 断言）+ test_uuid_namespace（7 断言）= 2
- 实际运行通过: 2（2/2 = 100%）
- 鸿蒙专项测试: test_uuid_ohos 17 项断言全部通过
- 消费者验证: test_package test_uuid 公开 API 调用全部通过

详见 reports/upstream-test-ledger.md、reports/upstream-tests-run.log、
reports/ohos-test-run.log、reports/conan-create.log。

## 依赖版本

无外部依赖。

---
**编译结束**: 2026-09-16
**最终状态**: built
---

**编译结束**: 2026-09-16 03:41
**最终状态**: built
