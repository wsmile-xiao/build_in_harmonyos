# undms 1.3 — OpenHarmony PC aarch64 适配记录

## 源码及依赖

- 上游 Aminet 镜像：`https://ftp.fau.de/aminet/misc/unix/undms-1.3.c.Z`；原始 `.Z` 流 SHA256：`d5c5396d1003f4d4125b4fe4833043e207b7315e87db3be92c2188ffbe27e8ac`（13186 字节）。归档是**单个 C 文件**，不是 tar，也没有配置脚本、Makefile 或声明的许可证；配方将 license 标为 unknown，未推断 MIT。
- 依赖仅 C 编译器、标准 C 库；目标 armv8/OHOS，Conan 2.29.1，使用仓库 `ci/conan/profiles/ohos-aarch64`。
- 手工探索：`/data/service/hnp/bin/clang -O2 -static undms.c -o undms`；`qemu-aarch64 undms` 打印 `Usage: undms source destination`、退出码 0。
- Conan 配方从上游 URL 直接下载 `.Z` 并核验 SHA256；以知识草稿 E6417 的纯 Python LZW 算法恢复 `undms.c`，再通过 Conan `CMakeToolchain` 驱动生成的最小 CMake 构建静态 CLI `bin/undms`。**不可调用构建机 gzip**：鸿蒙设备 toybox gzip 不支持 LZW。无上游源码补丁；本机临时 tar.gz 仅供 init-build 探索，不入仓、不供配方下载。

## 上游测试清点（R51）

`gzip -dc undms-1.3.c.Z` 解出仅 `undms.c`（1136 行）。`tests/` 目录数 0；Makefile/configure/CMakeLists 均无，`make check` 不存在，ctest/pytest 注册数均 0。上游实测 N=0、通过 N′=0，通过率不适用；本 PR 未修改上游用例。

## 消费者测试（rule12）

新增 **1** 个鸿蒙特有完整消费者流程；`test_package/make_fixture.py` 按上游 CRC16 算法构造 stored 与 RLE 双轨 DMS，包内 **OHOS `bin/undms`** 真实解包，解出 16384 字节转成 `extracted_disk.h`；Conan/CMakeToolchain 编译 `test_package/test.c` 的 aarch64 消费者，再以 `qemu-aarch64` 实行逐字节行为校验（或 aarch64 原生执行）。CI `conan create` 必跑 test_package，绝非文件存在性检查或跳过测试。

本机命令：`CONAN_HOME=/data/harmony-compact/.conan2-ohos python3 scripts/ohc-run.py conan-verify undms 1.3`，G1/G2/G3 全过；`reports/conan-create.log` 中 `RUN: qemu-aarch64 .../test_undms` → `OHOS consumer: stored and RLE tracks decoded; 16384 bytes verified`，退出码 0，消费者 1/1。交付静态 OHOS CLI 和消费者均由 qemu **实跑**；不是把动态链接产物静态重链副本冒充交付产物。上游测试 0/0（不适用）。

## 踩坑及知识

- `init-build` 将 `.c.Z` 当 tar.gz，报 `解压失败: not a gzip file`；E6417 已覆盖 Unix compress/LZW，沿用其解法，不重复造条目。
- 自动生成的 autotools 库配方不适用于单文件 CLI；手工改 application 配方、`commands.json` 及消费者测试；已有 `DRAFT-embedded-log-1.0.1-no-build-system-c-lib-direct-compile` 覆盖误判，不重复沉淀。
- DMS 扩展 RLE 最初将 `0x90,0xff` 后的数据错写成长度在前，程序报 `Extract failed`；对照上游 `undms.c:198-206`，正确为重复字节 `0x5a` 后跟大端长度 `0x20,0x00`；修复后真实输出 16384 字节。新增独立草稿 `knowledge/drafts/E8501-draft-6E52.{kv,md}`，`draft-review` 建议 create、最高相似度 0.23，由主编决定是否 promote。

## 状态

本地 `conan-verify`、W3 `setup.sh` 与 `build_and_test.sh` 均通过：`reports/w3-local-ci.log` 中 `RUN: qemu-aarch64 .../test_undms` 与 `OHOS consumer: stored and RLE tracks decoded; 16384 bytes verified` 两行确认消费者 1/1 实跑，`L1e` 移走 `bin/` 的反向测试通过，JC/KC 通过。第一次 W3 因本机缺少 `zsh`（`setup.sh RC=1` 且空输出）被拦，本机安装 zsh 后恢复；没有修改 CI 文件。`finish` 后段报 `SUMMARY.md` 生成 `'str' object has no attribute 'append'`、旧 `packaging/*.tar.gz` 缺失项（packaging 已废弃），与 W3 结果无关，未伪报 finish 全流程成功。

W4：preflight 实跑唯一命中 PF9——软件级 `README.md`、`commands.json`、`manifest.yaml` 是 R38/ARCHIVE-SPEC 必需文件，与 PF9 的「须含版本目录层」互斥；按 PF9 登记例外处置（PR 正文登记，建 PR 时 `--no-preflight`），独立审计 P0/P1=0。

许可：Aminet 条目 `undms-1.3.c.readme`（作者 David Tritscher）与源码均无许可声明，配方如实标 `unknown`；再分发前须核验上游授权。
---

**编译结束**: 2026-09-28 23:04
**最终状态**: built
