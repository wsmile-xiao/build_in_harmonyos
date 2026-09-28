# SKILL 执行流程反馈报告

## 背景

- 软件/版本：pilercr 1.06；2026-09-26；手写 Makefile。
- 官方上游：https://www.drive5.com/pilercr/pilercr1.06.tar.gz
- 适配路径：路径 B（可配置目标 strip 的一行补丁 + OHOS PC 功能消费者用例）。
- 外部依赖：无。补丁：1。`conan-verify`：PASS；本地 W3：见下方流程记录。

## 情况

### 执行概要

| 阶段 | 状态 | 证据 |
|---|---|---|
| init-build | 完成 | 官方源下载，语言预检 cpp |
| 探索编译 | 完成 | NDK clang++ aarch64 静态链接，目标 llvm-strip |
| conan-verify | PASS | G2 真正运行本包 CLI + 编译运行消费者，1/1 |
| finish W3 | PASS | `build_and_test.sh` 与 `conan create` 均通过；消费者本地 qemu 实跑 |
| W4 / PR / CI | W4、rule12 已过；CI 红待复验 | PR #13010 首轮 CI 的 NDK 缺 llvm-strip；本次一并修复 |

### 失败与问题

首次 Conan 骨架与上游目录不符：`get(strip_root=True)` 在 tar 条目带 `./pilercr1.06/` 时未搬平真实根目录，补丁找不到 Makefile；其次 `-std=c++17` 对上游 register 报错，依 `E293` 加 `-Wno-register`；第三，profile clang++ 是软链，`dirname(cxx)` 找不到 `llvm-strip` 意外回退宿主 strip。本地改 `realpath(cxx)` 后通过，但 PR #13010 CI NDK 不含 llvm-strip，`build()` 报 `OHOS target llvm-strip missing`。最终为 OHOS 显式 `STRIP=:` 跳过非必要剥离，沉淀草稿 `E6402`。

### 知识图谱使用情况

- 查重：`E293` 覆盖 register；`DRAFT-yosys-0.66-makefile-install-host-strip-cross-elf` 覆盖宿主 strip 通用故障；`E456` 为 Qt host generator，不适合本例。`E6402-draft-9142` 新增 CI SDK 缺可选目标 strip 时安全跳过剥离的处置，`draft-review` 建议 create（首轮相似最高 E191 0.14）。
- 上游测试 0（Makefile 没有 check 目标）；新增 OHOS PC 消费者 1/1、qemu 本地实跑，未跳过。

### 检视和 CI

PR #13010 已创建，W4 和 rule12 本地通过；首轮远程 CI L1 失败原文为 `OHOS target llvm-strip missing: .../llvm/bin/llvm-strip`，L2/L4/L5 未执行。本地 Conan G2 和 W3 曾经通过，但本地 NDK 含该工具，不代表 CI 可迁移；修复后需重跑 W3 并重新触发 CI、核对实际构建 SHA。finish 总退出码 1 另源于已废弃 packaging/ 的旧式预检和存量图谱字段，不是 W3 编译失败。

### 效率分析

- HANDOFF 0 次；Conan 首轮验证失败 3 次，随后 G2 PASS，分别为解包层级、C++17 register、软链定位 strip 三种不同原因，未触及同类 5 轮止损。
- 瓶颈：本机与 CI OHOS NDK 工具内容不一致（CI 无 llvm-strip）、旧 Makefile 和源码归档前缀；`gitcode_pr.py diagnose` 将 CI 日志中的 `timeout 14400 secs` 误归类为网络，实际根因是缺少可选构建工具。补丁生成器在单个 `comp.cpp` 补丁 dry-run 失败，最终不需该补丁，直接使用 `E293` 推荐编译标志。

## 建议

### SKILL 设计改进

在 `scripts/ohc/conan_verify.py` 的 G2 报错根因建议前，保留原始 `conan-create.log` 关键行供模型优先读取：这次三种错误均被泛匹配为 `E540`，与实际网络/工具缺失无关；先展示 `strip`、`register` 等精确行可少走弯路。

### 模板改进

`conan-init` 对顶层仅 Makefile、无 configure 的项目仍套 `templates/conanfile-autotools.py.tmpl`（默认 `autotools.configure()` / `autotools.install()`），并把 `test_package` 设为链接不存在的 `pilercr` 库。应按是否存在 `./configure` 和 install 目标切换到纯 Makefile + CLI 消费者模板。

### 自动化补全

生成的 `notes.md` 中 `{cmake|autotools|...}`、`conandata.yml` 中 `REPLACE_WITH_ACTUAL_SHA256` 等无强制校验。建议在 `conan-init` 提示立即核对实测 sha256、上游 Makefile 目标清点；`feedback` 骨架自动获取的 `{BUILD_SYSTEM}`、上游地址 `(未知)`、补丁数 0、用例数 0 均须用 manifest/source 和当前 test_package 重新采集。本报告已手动填实。`refresh-patch --auto` 对修改后的 `comp.cpp` 单文件 dry-run 失败时只给警告，应输出对应的 patch_ng 错误行。

### 知识图谱覆盖

建议主编审核 `knowledge/drafts/E6402-draft-9142.kv`：本地与 CI NDK 工具集合不一致时，不要因缺失非必要 llvm-strip 而阻止已可链接的 CLI；把剥离改为可配置并在 OHOS 上 `STRIP=:`。已核查它区别于已有宿主 strip 草稿。本报告只提交草稿，不 promote。

## 作者

- nyaco3 <aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com>
- 反馈 ID：5be05fd1；日期：2026-09-26
- PR：#13010，首轮 CI 红仅因目标 SDK 无可选 llvm-strip；修复后的 CI 结果待复查。
