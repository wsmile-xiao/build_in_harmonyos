# editline 2.1.0 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (aarch64-linux-ohos, OHOS PC)
- 状态: built（W3 本地验证通过，PR 合入后由 CI upload）

## 编译步骤

1. `init-build editline 2.1.0 --url=https://github.com/troglobit/editline/releases/download/2.1.0/editline-2.1.0.tar.gz`
   官方 tarball SHA-256: `189e179253c0932d15ce94f53e8cde7a0c38383f39f11f3b92d40cd18839678f`
2. lang-preflight: task=cpp, detected=c（c↔cpp 兼容族）→ 继续
3. 源码适配（3 个配方补丁，见 patches/）：
   - `0001-aux-config.guess.patch`：config.guess 无 HarmonyOS 识别分支，`uname -s=HarmonyOS`
     无法猜出构建类型 → 增加 HarmonyOS 系统识别分支，输出 aarch64-unknown-linux-ohos
   - `0002-aux-config.sub.patch`：config.sub 需接受 ohos-linux 三元组、ohos* OS 及 linux-ohos 内核/OS 组合
   - `0003-configure.patch`：HMDFS 上 umask 077 创建 0700 临时目录后当前进程不可写
     （UID 映射 20020083 vs 20001006），configure/config.status 创建临时文件报 Permission denied → umask 022
4. `./configure --prefix=$DEFAULT_PREFIX`（CONFIGURE_EXIT=0）
5. `make -j1`（MAKE_EXIT=0）→ 生成 libeditline.la
6. `make install DESTDIR=$TEST_PREFIX`（INSTALL_EXIT=0）→ lib/libeditline.{a,so.1.1.1}、include/editline.h、libeditline.pc
7. `make check`（CHECK_EXIT=0）：7 PASS + 1 SKIP（wrap-tmux.sh，无 tmux，上游自声明 headless 跳过路径）
8. conan-init + conan-verify：G0-G4 + L2/L4/L5 全部 PASS
9. 鸿蒙专项测试 ohos_special_test.c：headless 场景（补全引擎 3 候选/无候选、历史 33 项 round-trip、
   el_bind_key 注册）→ 4/4 PASS，退出码 0
10. 消费者用例 test_package/test.c（rl_initialize/el_hist_size/read_history/write_history round-trip）→ PASS，conan create 内 1/1 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess: cannot guess build type | config.guess 无 HarmonyOS 分支 | patches/0001 (config.guess OHOS 识别) + 0002 (config.sub 组合) |
| 2 | config.sub: Kernel linux not known to work with OS ohos | config.sub 内核/OS 组合校验缺少 linux-ohos | patches/0002 |
| 3 | configure/config.status: temp file Permission denied | HMDFS 上 umask 077 创建的 0700 临时目录不可写（UID 映射差异） | patches/0003 (umask 022) |
| 4 | make check 中 wrap-tmux.sh SKIP | 环境无 tmux（headless/CI），上游脚本显式 `exit 77` | 计入台账分母不计通过，7/8=87.5%；恢复条件=安装 tmux 后重跑 |

## 源码修改

- 无对上游源码的侵入式修改；全部改动通过配方 patches/ 在 conan create 时干净应用（3 个补丁均 dry-run OK）。
- 归档新增：conanfile.py、conandata.yml、test_package/、patches/、test-report.md、ohos_special_test.c、notes.md、manifest.yaml。

## 测试统计（双口径）
- source_declared_total=8，configured_executable_total=8，executed_passed_total=7，失败 0，跳过 1
- 全量通过率 7/8 = 87.5%；当前配置可执行集合 7/7 = 100%
- 详见 test-report.md（逐项映射 + 日志 SHA-256）

## 知识候选台账（knowledge_candidate_ledger）

### 候选 1：config.guess/config.sub 无 HarmonyOS 识别 → cannot guess build type / OS ohos not recognized

- 真实错误：`./aux/config.guess: unable to guess system type` → `configure: error: cannot guess build type; you must specify one`；随后 `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'`
- 根因：GNU config.guess 无 `__OHOS__`/HarmonyOS 检测分支，`uname -s=HarmonyOS` 无法匹配已知系统；config.sub 亦无 `ohos-linux` 三元组、`ohos*` OS 列表及 `linux-ohos` 内核/OS 组合校验
- 修复：patches/0001-aux-config.guess.patch（HarmonyOS 系统识别分支，输出 aarch64-unknown-linux-ohos）+ patches/0002-aux-config.sub.patch（ohos-linux 三元组 + ohos* OS 列表 + linux-ohos 内核组合）
- 验证：configure EXIT=0 生成 config.h/Makefile；conan create 干净构建 G2 PASS；conan-verify 全门禁 PASS
- 适用范围：所有基于 autotools 且依赖 config.guess/config.sub 猜型的 C/C++ 库在 OHOS 平台
- 七轴查重：
  - exact_duplicate: 是（E007 错误特征、根因、补丁位置逐项命中）
  - causal_duplicate: 是（同为 GNU autotools 无 OHOS 分支）
  - trigger_overlap: 是（cannot guess build type / OS ohos not recognized）
  - solution_overlap: 是（patch-autotools-ohos.pl 打 config.guess+config.sub）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：knowledge/graph/index.tsv E007（patch-autotools-script，严重度 2，P001/P003/P011），含 config.guess 两处 + config.sub 三处修改，输出 aarch64-unknown-linux-ohos
- 本轮新增部分：无（本次实测复现 E007 覆盖的同一路径）
- 适用边界/反例：`--build/--host` 绕过会误判交叉编译导致 AC_RUN_IFELSE 全跳过（E007 已记载），不可作为替代方案
- 关系：similar_to=E007；caused_by=GNU autotools 未收录 HarmonyOS；prerequisite_of=无；conflicts_with=无
- 决定：**reuse_existing（E007 完全覆盖，路径 A）**

### 候选 2：HMDFS 上 umask 077 临时目录不可写 → configure/config.status Permission denied

- 真实错误：`./aux/config.guess[1680]: can't create /storage/Users/currentUser/tmp/cgPMAGFK/dummy.c: Permission denied`；`config.status` 阶段 `confXXXXXX` 临时目录同样不可写（SKILL E011 特征逐字命中）
- 根因：HMDFS UID 映射（目录所有者 UID 20001006 vs 进程实际 UID 20020083）+ setgid 位（02700），umask 077 创建的 0700 目录对当前进程不可写
- 修复：patches/0003-configure.patch（configure 内 `umask 077` → `umask 022`，覆盖 mktemp -d 与 mkdir 两处）
- 验证：configure EXIT=0 完整走通；conan create 干净构建 G2 PASS
- 适用范围：HMDFS 平台上所有使用 `umask 077 + mktemp` 的 autotools/脚本类构建
- 七轴查重：
  - exact_duplicate: 是（E011 特征 `umask 077.*mktemp` / `Permission denied` / `drwx--S---` 全部命中）
  - causal_duplicate: 是（HMDFS UID 映射 + setgid）
  - trigger_overlap: 是（mktemp/confXXXXXX 临时目录创建被拒）
  - solution_overlap: 是（umask 077→022）
  - combination_novelty: 否；boundary_novelty: 否；test_migration_novelty: 否
- 既有条目覆盖部分：knowledge/graph/index.tsv E011（edit-umask-in-configure，严重度 3，P004/P006），含方法 2 `sed -i 's/umask 077/umask 022/g' configure`
- 本轮新增部分：无（本次实测复现 E011 同一根因与解法；本库补丁落在 configure 脚本内 mktemp/mkdir 两处，与 E011 建议一致）
- 适用边界/反例：仅 HMDFS 存在 UID 映射差异的平台出现；tmpfs/ext4 无此问题；0700 语义敏感的测试目录须另按 SKILL 临时目录恢复规则处理
- 关系：similar_to=E011, E052, E060, E110；caused_by=HMDFS UID 映射 + setgid；prerequisite_of=无；conflicts_with=无
- 决定：**reuse_existing（E011 完全覆盖，路径 A）**

### 候选 3：wrap-tmux.sh 在无 tmux 环境 SKIP（headless/CI 跳过路径）

- 真实错误/观察：`make check` 中 `SKIP: wrap-tmux.sh (exit status: 77)`；`command -v tmux` 为空
- 根因：环境无 tmux；脚本显式设计 `command -v tmux || exit 77`（上游注释：headless machines and CI）
- 修复/验证：非失败项；按上游设计计入台账分母不计通过（7/8=87.5%），恢复条件=安装 tmux 后重跑
- 适用范围：无终端/无 tmux 的 headless 构建环境
- 七轴查重：exact_duplicate=否（属环境条件记录，非可复用构建知识）；其余轴=否/弱
- 决定：**path_a_no_knowledge**（平台运行条件记录，无跨库知识价值，随本库台账申报）

### 路径初判结论

- 两个构建知识候选均**完整命中既有条目（E007 / E011）**，新增差异为空 → 复用既有知识，**路径 A（reuse_existing）**，不建草稿
- 候选 3 为环境条件记录 → path_a_no_knowledge
- 无 `new_draft` 候选；任务类型虽为"知识库扩展"，但查重结论如实判定无新增可跨库复用知识，按协议复用已有知识并走路径 A
---

**编译结束**: 2026-09-19 01:55
**最终状态**: built
