# virt-what 1.27 HarmonyOS 移植记录

## 概况

- 上游：virt-what 1.27，GPL-2.0-or-later，纯 shell + 两个 C 辅助程序。
- 归档：`archives/v/virt-what/1.27`，符合仓库 W2 标准目录。
- 目标：HarmonyOS PC aarch64（OHOS 6.0）。
- 上游正式源码：`https://people.redhat.com/~rjones/virt-what/files/virt-what-1.27.tar.gz`
- SHA256：`d4d9bd9d4ae59095597443fac663495315c7eb4330b872aa5f062df38ac69bf1`
- Conan 依赖：0；源码使用系统 shell、clang、make、libc，`dmidecode` 和 `timeout`
  为可选运行时探测工具，不构成构建依赖。
- 状态：Conan 包、消费者测试及仓库官方 aarch64 CI 均已在 HarmonyOS 真机通过。

## W0 依赖预检

已在最终配方上于 HarmonyOS 真机执行仓库 `ci/scripts/preflight_check.sh virt-what/1.27`，
脚本给出 `[OK] 预检通过（无依赖需要检查）`。本包不声明第三方 `requires` 或
`tool_requires`。

## W1 上游清点

- 构建系统：Autotools，源码归档内含 `configure`、`Makefile.in`、`config.guess`、
  `config.sub`；不需要 Autoconf/Automake 重新生成文件。
- 产物：`virt-what` shell 工具、`virt-what-cvm` 和 `virt-what-cpuid-helper` C 工具；
  安装时统一放入 Conan `bin/`。
- 外部依赖：无第三方依赖。目标机已核实 `clang`、`make`、`bash`、`python3`、
  `pod2man` 可用；`dmidecode` 缺失可由上游逻辑容忍。
- HarmonyOS 预检：真机 `uname -s` 为 `HarmonyOS`，`uname -m` 为 `aarch64`，
  clang/make/Conan 2.29.1 可用。上游 `config.sub` 原样拒绝
  `aarch64-linux-ohos`（`system 'ohos' not recognized`）。真机 `id -u` 报
  `bad uid 20020084`，而上游脚本即使在 fixture 模式也无条件调用 `id -u`。
- Autoconf `configure` 在 config.status 生成器中含两处 `umask 077`；HMDFS
  强制 setgid 后，这会产生 owner 不可写目录。改为仓库已有设备实证的 `umask 022`。
- GNU config 脚本版本为 2018-08-29 旧式格式。仓库通用 `patch-autotools-ohos.pl`
  在真机实测仅写入现代 `GUESS=` 风格分支，仍以 `unable to guess system type`
  失败，且旧版 `config.sub` 的脚本锚点不匹配；因此按旧式语法适配并实际验证
  config.guess 与 config.sub 的 4 段和 3 段输入都规范成
  `aarch64-unknown-linux-ohos`。

## 上游测试清点（R51）

- 源码 `tests/` 目录数：45。
- 每目录含 1 个 `test.sh`；Automake 为每项登记 `TESTS = test.sh`，共 45 项。
- 注册入口：`configure.ac` 中的 `tests` 列表与 45 个
  `tests/<case>/Makefile.am`。
- 测试命令：`make check -j1`，已纳入 Conan `build()`；HarmonyOS 真机全量实跑 45/45 通过。
- 每个 fixture 覆盖一类虚拟机/容器检测，通过隔离 proc/sys、dmidecode、uname 与
  CPUID helper 输入，断言输出 facts。

## 适配改动及验证状态

目标源码改动：`--test-root` fixture 不查询 uid；真实 HarmonyOS 运行也跳过失效的
`id -u` 检查并以 best-effort 模式执行检测，其他系统保留上游 root 限制；旧式
`config.guess` 使用 `echo` + `exit` 识别 aarch64 HarmonyOS，
`config.sub` 在两处系统白名单中接受 `linux-ohos`；Autoconf configure 对
HMDFS 的 `pwd` 加 `$PWD` 回退，config.status 临时目录将两处 `umask 077` 调整为
`022`。所有源码改动由仓库 `scripts/ohc/refresh_patch.py --auto` 在真机上按编辑跟踪记录生成补丁。

测试执行时发现：上游各 fixture 从当前目录相对读取伪造的 `proc/` 与 `sbin/`；
Automake out-of-source 运行会丢失这些目录。Conan `basic_layout` 已把源码放入该包的
可写 source/build 根目录，因此配方直接在此目录 in-source configure 和 `make check`，
保持所有上游 fixture 相对路径；不能再把副本嵌套到其 `build-release/` 子目录。

| 检查 | 结果 |
|---|---|
| 官方 tarball SHA256 | 通过，本机复核 |
| W0 依赖预检（最终配方） | 通过，无依赖 |
| HarmonyOS 原版 fixture 基线 | 失败（预期）：`id: command not found` / `failed to get current user id` |
| triplet 核验 | 通过：config.guess 及 config.sub 的 3/4 段输入均输出 `aarch64-unknown-linux-ohos` |
| Conan `make check -j1`（45 项） | 通过：45 PASS / 0 SKIP / 0 FAIL / 0 ERROR |
| HarmonyOS aarch64 `conan create` | 通过；包由 HarmonyOS clang 15 原生构建 |
| `test_package` 普通消费者测试 | 通过：5 项断言 |
| HarmonyOS 专项消费者测试 | 通过：4 项断言（HarmonyOS、aarch64、真实检测退出码、facts 格式） |
| 完整仓库 `ci/conan/build_and_test.sh` | 通过：G0/G0e、KC、包级 PR-diff JC、L0/L1/L2/L4/L5 全通过；上游 45 PASS / 0 SKIP / 0 FAIL / 0 ERROR；Conan 消费者与 HarmonyOS 专项测试共 9 项断言通过 |

## 最终结果

版本级 `manifest.yaml` 已更新为 `status: built`。首次运行因 bundle 未配置 `origin/main`，
官方脚本回退到整仓扫描并命中 5 个与本包无关的既有隐藏状态标记；随后按 CI 支持的
PR-diff 模式提供本次包变更的真实暂存补丁清单，所有门禁及完整构建测试通过。
---

**编译结束**: 2026-09-30 23:07
**最终状态**: built
