# unfoo 1.0.8 — OHOS PC aarch64 适配笔记

## 源码与类型

- 上游仓库：`https://github.com/vitaminmoo/unfoo`，GitHub 只发布 `v1.0.7`；本次用户提供的 Gentoo distfiles 权威镜像包含单独的 `unfoo-1.0.8/` 目录及新扩展名分支。
- 源码 URL：`https://mirror.dogado.de/gentoo/distfiles/3b/unfoo-1.0.8.tar.gz`；SHA256：`badc62603f1f7293032b36a1a3f1051b715b31895700d116d74cba4cb68af1e5`（下载后 `sha256sum` 核实）。
- 上游主体 `unfoo` 首行 `#!/bin/bash`，构建系统为脚本直接安装，无 C/C++ 源码及构建步骤；`init-build` 对 `tests/Makefile` 错归为 Autotools，`conan-init` 错生成库配方，已改为 Conan `application`，只安装脚本和许可证。
- 根据本次赛事 Shell 脚本可参赛的新口径，不运行旧版会将 Shell 误报为 `env_unsupported` 的语言预检。**没有把脚本本体记作 aarch64 原生可执行程序。**

## 依赖与范围

- W0：`conan download bash/5.3 -r=ohpcd --only-recipe` 成功；Bash 与 tar/gzip/bzip2/xz/lzma/unzip/zipinfo/7z 为使用相应格式时的运行工具，不将未实际消费的 Conan 包强行声明为构建依赖。
- `unace`、`unrar` 本机不存在，ACE/RAR 格式未被验证，不宣称完整格式通过；脚本本身不捆绑这些解包器。
- `conandata.yml` 用版本键和实际 SHA256；`commands.json` 声明软件级 CLI。无补丁、无伪造的静态库或头文件。

## R51 上游测试清点与执行

- `tests/` 目录 1 个，`tests/test_*.sh` 5 个（`test_exit_status.sh` 3 个测试函数，另 4 文件各 1 个），合计 7 个 shunit2 case；ctest/pytest 注册数均 0。
- 执行：在解包的源树运行 `make test > /data/harmony-compact/unfoo-upstream.log 2>&1`；日志汇总 `7 tests, 12 failures, 0 skipped`，其中 4 个 case 通过、3 个 case 各有 4 次断言失败，**通过率 4/7 (57.1%)**。失败的格式仅为 ACE/RAR（缺 unace/unrar），非编译错误。
- 上游 `tests/runner` 用 `( exec ${shell} ./${suite} 2>&1 | tee results/...)`，随后只打印汇总，导致 `make test` 返回 `0` 即使报告 `FAILED (failures=4)`；不能把命令退出码当作 7/7。未修改上游测试，不将缺工具的用例计入通过。

## rule12：鸿蒙特有完整消费者用例（1 项）

- 文件：`test_package/conanfile.py`、`test_package/consumer.c` 和 `test_package/CMakeLists.txt`。
- Conan `unfoo/1.0.8` 包内 `bin/unfoo` 解压由消费者 C 源码生成的 `consumer.tar.gz` → Conan OHOS profile / Clang 15 将**解出的 C 文件**交叉编译并静态链接为 AArch64 ELF → `qemu-aarch64 ./unfoo_ohos_consumer` 实际运行并检查可观测输出 `unfoo archive -> OHOS aarch64 consumer`，返回码 0。静态链接仅用于 x86 runner 的 QEMU 功能验证；不将 Bash 脚本假称为 ELF。
- `conan-verify` G2 `conan create` PASS；日志 `reports/conan-create.log` 显示 `RUN: bash .../bin/unfoo .../consumer.tar.gz`、`C compiler identification is Clang 15.0.4`、`Linking C executable unfoo_ohos_consumer`、`RUN: qemu-aarch64 ./unfoo_ohos_consumer`、正确输出。消费者 1/1 实跑通过，无 skip。

## 门禁说明与知识

- 首次 `conan-verify`：`G1 FAIL`，逐项要求 `build()`、`export_sources()`、`apply_conandata_patches()`，但脚本无编译/补丁。配方保留无编译的钩子满足结构检查；此根因已被 `DRAFT-pocketfft-release_for_eigen-headeronly-g1-three-declarations` 覆盖，不重复建草稿。
- 新知识草稿 `E876-draft-1245`：shunit2 runner 管道 `tee` 吞掉测试失败且汇总不传播错误，导致 `make test` 假通过；主编合并时决定正式编号。
- 软件级 `commands.json` 按 PF8/R38 必须位于 `archives/u/unfoo/`；PF9 对新增软件级文件存在结构性冲突，PR 正文需登记唯一例外，不能静默绕过。
- `finish built` 中 **W3 本地 CI 真实 PASS**（`reports/w3-local-ci.log` 与工具生成的 `.ci-result.json`，`setup.sh`、`build_and_test.sh` 均 RC=0，L0/KC/JC 全通过且消费者执行成功）。`finish` 总返回 1 是非阻断的旧框架项：G0 clean-verify 强行运行不存在的 `./configure`（日志 `./configure: 没有那个文件或目录`）；软件没有 configure；全局知识条目 E219/E253/E305 既有空字段使 W5 汇总警告；summary 报 `'str' object has no attribute 'append'`。不为规避历史问题修改他人知识或框架文件，W3 成功以真实 CI 结果为准。
---

**编译结束**: 2026-09-29 15:05
**最终状态**: built
