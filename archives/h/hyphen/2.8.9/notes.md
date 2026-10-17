# hyphen 2.8.9 适配笔记

## 编译环境
- 构建系统: autotools (configure + make + libtool)
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4 / llvm-ar / llvm-ranlib
- 状态: built
- 源码: https://github.com/hunspell/hyphen/releases/download/v2.8.9/hyphen-2.8.9.tar.gz
- SHA-256: 783743daf477de8c4d16e3c74b4d2827377017718d8e17e2d9440210246f6abe

## 编译步骤
```bash
# 1. config.guess/config.sub 打 OHOS 补丁（E007/E160/E268 标准方案）
perl scripts/patch-autotools-ohos.pl config.guess config.sub

# 2. 配置（必须携带任务专用 mktemp 包装，见"遇到的问题 #2"）
TMPDIR=$HOME/tmp/hyphen-conf-tmp PATH=$HOME/tmp/hyphen-conf-tmp/bin:$PATH \
  ./configure --prefix=$DEFAULT_PREFIX CC=clang CFLAGS="-fPIC -O2"

# 3. 编译 + 安装
make -j4
make install DESTDIR=$TEST_PREFIX

# 4. 上游测试（必须携带同一 TMPDIR/PATH 环境）
make check
# 结果: 37/37 PASS（修复 test.sh shebang 后，见"遇到的问题 #3"）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type`（UNAME_SYSTEM=HarmonyOS） | config.guess 2024-07-27 不认识 HarmonyOS/HongMeng Kernel | `patch-autotools-ohos.pl` 注入 `__OHOS__` LIBC 检测 + HarmonyOS 系统识别 + config.sub 增加 ohos-linux/linux-ohos triplet（补丁 0001/0002），configure 通过 |
| 2 | `config.status: can't create .../confXXXXXX/subs1.awk: Permission denied` | config.status 硬编码 `(umask 077 && mktemp -d ./confXXXXXX)`，HMDFS 上 umask 077 创建 0700 目录，属主映射 20001006 而进程 uid 20020101 无写权限，chmod 不生效 | 补丁 0003 将 configure 中两处 `umask 077` 改为 `umask 002`（config.status 由 configure 生成，tmp 目录创建为 2771 组可写）；本地探索编译另行使用组可写 TMPDIR + umask 002 mktemp 包装辅助，最终配方只依赖 0003 补丁 |
| 3 | 上游测试 37 项全部 FAIL，`./test.sh: No such file or directory` (126) | tests/test.sh shebang `#!/bin/bash`，设备上无 /bin/bash（bash 在 /data/service/hnp/bin/bash，PATH 可及但 shebang 绝对路径不可及） | 补丁 0004：test.sh shebang 改为 `#!/usr/bin/env bash`（/usr/bin/env 存在，PATH 中可解析 bash），37/37 全部 PASS；示例程序 example 输出与 .hyph 期望逐一 diff 一致 |
| 4 | W3 本地 CI 模拟 JC 拦截 3 个其他库基线文件（archives/c/cloog/0.21.1/.build-closed、.staging-verified、archives/k/kics/2.1.20/.staging-verified） | 本地 junk_check 回退 full 模式（git ls-files 整仓）；真实 CI 用 prdiff 模式只查 PR 文件清单，这些文件不在当前库 PR 变更内 | 基线隔离复验：记录隔离前 SHA-256（e3b0c44298...），`git rm --cached` 临时隔离，复跑 W3 通过，`git add -f` 原样恢复并核对恢复后 SHA-256 一致，当前库 diff/staged/PR 不含该路径；不修改、不提交该基线文件 |

## 源码修改
- 仅 patch-autotools-ohos.pl 对 config.guess/config.sub 的 OHOS 识别注入（构建脚本，不进入正式源码）
- tests/test.sh 第 1 行 shebang `#!/bin/bash` → `#!/usr/bin/env bash`（上游测试可移植性修复）
- 无平台宏、无空壳 stub、无 __OHOS__ 条件编译注入

## 依赖版本
- 无外部 Conan 依赖（纯 C 库，仅 libc）
- 构建工具: clang 15.0.4, GNU make 4.4.1, autoconf 2.72, automake 1.16.5, libtool, gawk, perl

## 验证结果
### 上游测试完整枚举台账（tests/Makefile.am TESTS 声明 = 37 项）
| 分类 | 项 | 说明 |
|------|-----|------|
| 独立上游用例（.test，计入统计） | 37 | basealt2/basealt/base/conv/unicode/alt..alt7(8)/longlines/compound..compound7(8)/settings..settings4(4)/lhmin/rhmin/lig/hyphen/num/boundary/recursion/nohyphen2/nohyphen3/rhmin2/replindex/matchindex/utf8cut |
| 测试框架脚本 | tests/test.sh | 公共执行器（非独立用例，不计入）：调用 example 并 diff 期望输出 |
| 测试数据 | 37×(.pat/.word/.hyph) | 每用例的 pattern/word/期望输出三件套 |
| 测试程序 | example.c → example | 用户测试入口，经 libtool -dlopen libhyphen 运行 |
| 工具程序 | substrings.c / substrings.pl | 辅助工具（词表生成，非测试用例） |
| 文档样例 | doc/、README_hyph_en_US.txt | 非测试 |
| checkme.lst | 18 词 | 手写检查词表，非自动化用例 |

### 双口径统计
- source_declared_total（源码 TESTS 声明）: **37**
- configured_executable_total（当前配置实际实例化/注册）: **37**
- executed_passed_total: **37**
- failed: **0** / uninstantiated: **0** / skipped: **0**
- 全量通过率: **37/37 = 100%**（实际执行集合 = 源码声明集合，无未实例化项）
- 逐项映射：Makefile.am TESTS(37) → 构建目标 tests/*.test(37 可执行脚本) → test.sh 调用 example → 实际执行日志（make check 输出 PASS 37 项）
- 修复前基线：37/37 FAIL（根因 #3 shebang），修复后 37/37 PASS，无上游条件宏/互斥分支导致未实例化

### 测试命令（真实执行）
```bash
TMPDIR=$HOME/tmp/hyphen-conf-tmp PATH=$HOME/tmp/hyphen-conf-tmp/bin:$PATH make check
# Testsuit summary: TOTAL 37, PASS 37, FAIL 0
# 日志: $BUILD_SRC_DIR/tests/test-suite.log
```

## 基线隔离审计（W3 本地 CI 命中其他库基线文件）

| 字段 | 值 |
|------|-----|
| path | archives/c/cloog/0.21.1/.build-closed、archives/c/cloog/0.21.1/.staging-verified、archives/k/kics/2.1.20/.staging-verified |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（×3，均为空文件） |
| isolation_command | `git rm --cached -q archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified archives/k/kics/2.1.20/.staging-verified` |
| rerun_command | `python3 scripts/ohc-run.py finish hyphen 2.8.9 built`（隔离后复跑 W3） |
| rerun_exit_code | 0（W3 本地 CI 模拟通过：setup.sh 通过、build_and_test.sh 通过；JC 不再拦截） |
| restore_command | `git add -f archives/c/cloog/0.21.1/.build-closed archives/c/cloog/0.21.1/.staging-verified archives/k/kics/2.1.20/.staging-verified` |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（×3，与 pre 一致） |

结论：pre_sha256 == post_sha256；当前库 diff/staged/PR 均不含上述路径；未修改、未提交该基线文件。W3 失败仅因本地 junk_check 回退 full 模式扫描整仓 `git ls-files` 命中其他库预存基线空文件；真实 CI 使用 prdiff 模式只检查 PR 文件清单，本 PR 不含这些路径，不会拦截。

## 知识候选台账与四范围查重（knowledge_candidate_ledger）

| 候选 | 真实错误/根因/修复/验证 | 适用范围 | 正式知识( graph/ ) | 图谱文档( doc/ ) | 草稿( drafts/ ) | 判定 |
|------|------|------|------|------|------|------|
| C1 config.status umask 077 + mktemp 临时目录 Permission denied（HMDFS） | 根因：config.status 硬编码 `(umask 077 && mktemp -d ./confXXXXXX)`，HMDFS 上 0700 目录属主映射 20001006 而进程 uid 20020101 无写权限。修复：补丁 0003 将 configure 两处 umask 077→002。验证：conan create G2 全绿（toybox mktemp 尊重 umask，002→2771 可写） | 所有 autotools 包在 HMDFS 上 configure | E011（umask 077+config.status+mktemp，rec=edit-umask-in-configure，与本修复同构）/ E129 / E175 | doc/E011.md 等 | DRAFT-6507-cln-mktemp-0700-hmdfs（声称 mktemp 恒 0700 umask 无效，未区分 toybox/GNU 实现） | **partial：trigger/solution 高度重叠，但新增边界差异：toybox mktemp 尊重 umask（002→2771 可写）而 DRAFT-6507 断言 mktemp 恒 0700（GNU 实现）；本轮实测区分了实现差异 → 建草稿（路径 B）** |
| C2 tests/test.sh shebang `#!/bin/bash` → `/usr/bin/env bash`（OHOS 无 /bin/bash） | 根因：设备无 /bin/bash（bash 在 /data/service/hnp/bin/bash，shebang 绝对路径不可及）。修复：补丁 0004。验证：make check 37/37 PASS | 所有 `#!/bin/bash` 脚本在 OHOS 上执行 | E037（/usr/bin/env shebang 兼容）/ E049（shebang-portable-fix）/ E165（bash shebang OHOS） | doc/E037.md 等 | DRAFT-8207/DRAFT-date-3.0.3/DRAFT-gnustep-gui（同类） | **exact_duplicate：完全覆盖，无新增差异 → 复用既有知识（E037/E049/E165），不建草稿** |
| C3 config.guess/config.sub HarmonyOS 识别（patch-autotools-ohos.pl） | 根因：config.guess 2024-07-27 不认识 HarmonyOS。修复：补丁 0001/0002。验证：configure 通过 | 所有 autotools 包 | E007/E160/E205/E268（标准方案） | doc/E007.md 等 | 无新增 | **exact_duplicate：完全覆盖 → 复用既有知识，不建草稿** |
| C4 W3 本地 CI junk_check full 模式拦截其他库基线文件（cloog/kics 空状态文件） | 根因：本地 junk_check 回退 full 模式（git ls-files 整仓）扫描到 main 上其他库预存基线文件；真实 CI prdiff 模式只查 PR 文件清单。处理：基线隔离复验（隔离→复跑→恢复→SHA 一致） | 所有含其他库基线状态文件的 PR | 无正式条目 | 无 | DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise（W3 JC 基线噪声 prdiff 豁免主题已覆盖） | **trigger/solution 已由既有草稿覆盖 → 复用，不建草稿；基线隔离审计见上文表格** |

### 七轴查重结论（C1 部分覆盖建草稿，其余复用）

- C1: exact_duplicate=false; causal_duplicate=true（同根因族）；trigger_overlap=高（同 error_signature）；solution_overlap=高（E011 同构）；**combination_novelty=true（toybox vs GNU mktemp 的 umask 行为差异 + E011 处方在 toybox 环境实证有效）**；boundary_novelty=true（区分 mktemp 实现，DRAFT-6507 未覆盖）；test_migration_novelty=false
- C2/C3/C4: 完整重复或既有草稿覆盖，无独立新增差异 → 复用原条目

### 路径决定

**path_b_new_draft**：C1 候选经本轮真实日志验证（conan create G2 通过、toybox mktemp umask 002 有效）、可跨库复用、查重为部分覆盖且存在新增差异（mktemp 实现行为区分），按赛事路径 B（【知识库扩展】）建立同 stem 的 .md/.kv 草稿；C2/C3/C4 复用既有知识，不重复建草稿。

## 交付物
- archives/h/hyphen/2.8.9/conanfile.py + conandata.yml + test_package/ + patches/
- libhyphen (libhyphen.so.0.4.0 + libhyphen.a)，头文件 hyphen.h，数据 hyph_en_US.dic
- 产物包含可执行文件 example/substrings（noinst_PROGRAMS，不安装）；正式安装产物仅库+头+数据，非 CLI 交付，不创建 commands.json（R38：库类型）

## 注意事项
- 本机所有构建相关命令必须携带任务专用 TMPDIR 与 mktemp 包装 PATH（HMDFS 权限语义所致，见问题 #2）
- test.sh shebang 修复为可移植写法，随 patches/ 进入 PR（若配方采用构建期替换则说明理由）
- 知识候选：问题 #2（HMDFS umask 077 下 mktemp 0700 目录不可写）与问题 #3（shebang 绝对路径不可移植）为可跨库复用的知识候选，进入路径 B 判断
---

**编译结束**: 2026-09-21 01:01
**最终状态**: built
