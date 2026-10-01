# SKILL 执行流程反馈报告

> 本报告记录 `unfoo/1.0.8` 的真实适配过程；PR 创建前的异步评审与 CI 不记为已通过。

## 背景

- **软件名称/版本**：unfoo/1.0.8，主体为 Bash CLI，无 C/C++ 本体构建。
- **构建系统**：custom（脚本安装）；`tests/Makefile` 只调用测试 runner。
- **上游仓库**：https://github.com/vitaminmoo/unfoo
- **1.0.8 源码**：https://mirror.dogado.de/gentoo/distfiles/3b/unfoo-1.0.8.tar.gz；SHA256 见本包 `conandata.yml`。GitHub 只有 `v1.0.7` 标签，须明确镜像来源。
- **适配路径**：基础适配 + 知识草稿；补丁 0；Conan 构建依赖 0；系统需 Bash、使用相关格式时需对应外部解包工具。
- **本地状态**：`conan-verify` PASS，`finish` 的 W3 `setup.sh` 与 `build_and_test.sh` 均 RC=0，`test_package` OHOS aarch64 消费者 QEMU 实跑 1/1；PR/远程 CI 未开始，不声明远端成功。

## 情况

### 执行概要

| 阶段 | 结果与证据 |
|---|---|
| init-build | 归档下载解压成功；将 Shell 脚本误识别为 autotools，提示旧模板缺失及 `TMPDIR` 未设置。 |
| 上游测试 | `make test` stdout 汇总 7 tests、12 failures、0 skipped；4/7 测试 case 通过；ACE/RAR 解包器缺失。 |
| 配方 | `conan-init` 生成虚构的 Autotools 库配方，改为无编译的 `application`。 |
| conan-verify | 首轮 G1 缺 3 个无构建族钩子而失败；补无操作导出/补丁钩子后 G1/G2 全过，实测消费者 Clang 交叉编译 + QEMU 运行。 |
| finish/W3 | 先 commit 本包再跑 `finish built`，避免 JC 扫全仓；W3 setup/build_and_test RC=0，L0/KC/JC PASS，`.ci-result.json` 由 finish 写入。旧 G0 对无 configure 脚本报 127，全局 W5 既有字段缺失与 summary 异常令 finish 总 RC=1；不误写 W3 红。 |
| W4/PR/CI | 尚未创建 PR；rule12 已由入仓消费者代码与本地执行日志证明 1/1，正式审计/远端 CI 以之后结果为准。 |

### 失败与问题

- `conan-verify` `G1 FAIL`: 无构建脚本仍被要求声明 `build()`、`export_sources()`、`apply_conandata_patches()`，见 `scripts/ohc/conan_verify.py:485-494`；同根因已有 header-only 草稿，未重复提草稿。
- 上游 `tests/runner` 每套件经 `tee` 管道且汇总不传播失败：`make test` 返回 0 时仍报告 12 次断言失败；缺少的是可选 `unace`/`unrar`，绝不报上游 7/7。
- 旧版本语言门禁会把赛事允许的 Shell 错判为 `env_unsupported`：此次按赛事新口径保留脚本配方，不伪称脚本是 aarch64 ELF。

### 知识图谱与验证

- 命中 E411 与本次 G1 不同根因；既有 `DRAFT-pocketfft-release_for_eigen-headeronly-g1-three-declarations` 覆盖 G1 三项要求。
- 新增 `knowledge/drafts/E876-draft-1245.{kv,md}`：shunit2/tee 掩盖失败的准确错误模式；draft-review 邻近正式条目 E535 分数 0.28、未见同签名（根因字段需单行以便预审正确识别）。仅草稿，待主编定正式编号。
- 上游测试 4/7 (57.1%)；鸿蒙消费者 `test_package/consumer.c` 1/1 QEMU 运行通过，输出 `unfoo archive -> OHOS aarch64 consumer`，失败 0、跳过 0。`conan-verify` 的 L2/L4/L5 内部 SKIP 不计入测试通过数。

### AI 检视与 CI

- 建 PR 前：AI 变更摘要与意见均未产生，意见数量 0（非“已通过”），后续用户手动请求复查。
- 本地 `conan-verify` G2 PASS、W3 `setup.sh`/`build_and_test.sh` RC=0；远程 CI 尚未触发，不能标记 PASSED。`finish` 的 G0 因 `./configure` 不存在非阻断失败，W5 全局存量条目 E219/E253/E305 缺字段，summary 异常需由主编另行修框架；本 PR 不碰框架文件。

### 效率分析

- HANDOFF：`feedback` 占位 HANDOFF 1 次；`conan-verify` G1 初检失败 1 次，针对三项结构缺失只修 1 轮；其余无盲重试。
- 瓶颈：无构建脚本的 `init-build` 检测/配方模板与结构闸不匹配，以及上游测试 runner 将失败吞为 `make test` 成功。
- 耗时步骤：人工清点官方测试的可选格式依赖，并编写 Conan 消费脚本→C 源解压→OHOS 编译→QEMU 实跑路径；未提供人工虚构耗时数字。

## 建议

### SKILL 设计改进

在 `scripts/ohc/lang_detect.py` 的 Shell 分支与 `scripts/ohc/conan_verify.py:485-494` 的 G1 检查前增加赛事能力开关：允许 `#!/bin/bash` + 无源码项目走脚本工具类型，而不是写 `env_unsupported`；脚本工具不应因没有 C 编译、补丁而被结构闸拒绝。

### 模板改进

`templates/conanfile-headeronly.py.tmpl` 的“脚本工具”变体应提供与 G1 一致的完整可运行 `source()/export_sources()/build()/package()`，删除头文件复制与库 `package_type`；`templates/积分赛事PR模板.md` 的鸿蒙特有测试行使用待填标记而非自动生成 0，并要求说明“工具产物进入消费者构建+运行”的证据。

### 自动化补全

`conan-init` 对只有 `tests/Makefile` 的源码优先检测根目录是否有 `configure`/Makefile 构建目标，避免把脚本强套 Autotools 配方；自动清点 shunit2 的 `Ran`/`FAILED` 与最终汇总，当 `make test` 退出 0 但发现 failures>0 时报告矛盾且不得写 100%；反馈模板的“成功、finish 完成、测试 0/0”应只在状态文件确有证据时填入（本次人工纠正）。

### 知识图谱覆盖

增加“shunit2 suite 经 `tee` 管道吞掉失败返回码且 `make test` 回 0”的新草稿 E876，供主编审查后纳入正式图谱；G1 三缺项已经有 pocketfft 草稿，推荐合并/引用而非复制。

## 作者

- **姓名**：nyaco3
- **邮箱**：aqjCItYW1QmEJQuF.gcw_XDpqZ8sO@noreply.gitcode.com
- **草稿作者 ID**：1245
- **报告 ID**：e91ac0a9
- **报告生成日**：2026-09-29
- **PR 编号**：创建前未知；远程结果以 PR 审计和 CI 评论为准。
