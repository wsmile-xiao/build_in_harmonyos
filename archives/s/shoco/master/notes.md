# shoco master 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure / install 目标）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: published
- Conan: 2.29.1（OHOS 适配版），profile: ci/conan/profiles/ohos-aarch64

## 编译步骤

shoco 是零依赖 C99 库，无 configure 脚本，直接编译：

```bash
# 库（静态）与 CLI
clang -std=c99 -O3 -Wall -fPIC -c shoco.c -o shoco.o
ar rcs libshoco.a shoco.o
clang -std=c99 -O3 -Wall -fPIC shoco.o shoco-bin.c -o shoco
# 上游测试
clang -std=c99 -O3 -Wall shoco.o tests.c -o tests && ./tests
clang -std=c99 -O3 -Wall shoco.o test_input.c -o test_input && printf '...' | ./test_input
```

Conan 道路（归档配方自包含）：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify shoco master   # G0-G4+L2/L4/L5 全过
python3 $SKILL_ROOT/scripts/ohc-run.py finish shoco master published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接报 `undefined symbol: alloca`（shoco-bin.c） | OHOS musl 不提供 stdlib.h 隐式 alloca 声明（glibc 有） | 补丁 `0001-shoco-bin-alloca-h.patch`：shoco-bin.c 显式 `#include <alloca.h>` |
| 2 | conan source() 报 `BadZipFile: File is not a zip file` | codeload URL 末段 `refs/heads/master` 无 .tar.gz 扩展名，conan 误判为 zip | conandata.yml 显式声明 `filename: "shoco-master.tar.gz"` |
| 3 | conan create 配方生成后 package() 报 `attribute 'copy'` | Conan 2 移除 `self.copy` | 改用 `conan.tools.files.copy(self, ...)` + `self.package_folder` |
| 4 | conan 配方的 patches dict 格式未应用 | apply_conandata_patches 对 dict 按 version 键查找（"master"）而非文件名 | conandata.yml patches 改为 list 格式（patch_file/patch_description/patch_type） |
| 5 | W3 JC 命中 `archives/c/cloog/0.21.1/.build-closed`、`.staging-verified` | 其他库提交前已存在的基线跟踪文件（空文件，blob e69de29b），full 模式 git ls-files 全仓扫描 | 按基线隔离规则：记录路径 + 隔离前 SHA-256（e3b0c442…）→ 临时移出索引与工作树 → 复跑 W3（通过，.ci-result.json exit_code=0，log_sha256=e8b6fec8…，integrity_hash=f6879185…）→ 原样恢复并核对恢复后 SHA-256（e3b0c442… 一致）→ git 状态干净、不进入当前库 diff/staged/PR |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| patches/0001-shoco-bin-alloca-h.patch | shoco-bin.c 增加 `#include <alloca.h>`（OHOS musl 需要显式声明） |

## 依赖版本

无第三方依赖（零依赖库）。工具链：clang 15.0.4 / llvm-ar / make 4.4.1 / conan 2.29.1。

## 验证结果

- 上游测试：tests.c（31 assert，`All tests passed.` RC=0）+ test_input.c（3 assert，RC=0），统计 2/2 = 100%
- 鸿蒙专项测试：ohos_special_test.c（UTF-8 中文/混合串/空串/截断输入），`all checks passed` RC=0
- 消费者用例：consumer_example.c（仅用公开头文件 + libshoco.a + 公开 API），`all public-API roundtrips passed` RC=0
- test_package：test.c 压缩/解压回环断言，conan create 内自动运行通过
- 全部验证命令、cwd、退出码与日志 sha256 见 `reports/test-report.md` 与 `.ci-result.json`

## R38 说明

构建产物 `shoco` 为可执行 CLI 工具（压缩/解压文件），软件级 `archives/s/shoco/commands.json` 已声明。
---

**编译结束**: 2026-09-17 21:46
**最终状态**: published

## 知识候选台账 + 七轴查重（knowledge-candidate-ledger）

### 候选1：OHOS musl 下 alloca() 需显式包含 <alloca.h>（shoco-bin.c）
- 真实错误：`clang -std=c99` 编译 shoco-bin.c 报 `call to undeclared function 'alloca'`（隐式声明警告）→ `ld.lld: error: undefined symbol: alloca`
- 根因：glibc 的 <stdlib.h> 在 __GNUC__ 下隐式声明 alloca；OHOS musl 的 <stdlib.h> 不提供，源码未包含 <alloca.h>
- 修复：patch 0001-shoco-bin-alloca-h.patch 增加 `#include <alloca.h>`（纯 POSIX 移植修复，无平台宏，符合 R8）
- 验证：conan-verify G2 PASS；W3 本地 CI PASS
- 适用范围：所有在 OHOS/其他 musl 系平台使用 alloca() 的 C/C++ 源码（上游 glibc 环境下可编译的代码）
- 查重（四范围：正式知识 E-entry / doc / 草稿 / 图谱）：
  - exact_duplicate=false：knowledge/graph/*.kv 无 alloca 专属条目（E004 musl BIND_NOW、E115 fallocate 常量缺失、E063 -Werror 隐式声明均不同根因）
  - causal_duplicate=false：无同因条目（musl-glibc 对比文档 §1.10 仅记录可用性表，无错误模式+修复）
  - trigger_overlap=partial：与 E115/E063 同属"隐式声明/编译警告"类别，但触发点（alloca 链接失败）与修复（补头文件）不同
  - solution_overlap=low：E115 用 #ifdef __OHOS__ 补常量，本修复是跨平台 #include <alloca.h>
  - combination_novelty=true：alloca + musl + clang/lld 链接失败组合未收录
  - boundary_novelty=true：glibc 隐式声明 vs musl 不声明的 libc 边界差异
  - test_migration_novelty=n/a
- 关系：similar_to=E063（隐式声明族）；prerequisite_of=无；conflicts_with=无

### 候选2：conandata.yml patches 必须用 list 格式（dict 按 version 键查找陷阱）
- 真实错误：conan create 配方构建时补丁静默未应用（先写 dict 格式 `patches: {"xxx.patch": {...}}`，apply_conandata_patches 把 dict 按 version 键查找，version="master" 无匹配 → "No patches defined for version master" 静默返回，链接继续报 undefined symbol）
- 根因：Conan 2 apply_conandata_patches 对 dict 类型按 `conanfile.version` 键查找条目；list 类型才是无条件全量应用
- 修复：conandata.yml patches 改 list 格式（patch_file/patch_description/patch_type）后补丁生效
- 验证：conan-verify G2 PASS
- 适用范围：所有 Conan 2 配方声明 patches 的场景
- 查重：exact_duplicate=false（E515/E526 覆盖 strip 语义、E282 覆盖 base_path，均非 dict-version-key 查找）；causal_duplicate=false；trigger_overlap=partial（同属"补丁未正确应用"族，但触发机制不同）；solution_overlap=low；combination_novelty=true；boundary_novelty=true（dict 按 version 键 vs list 无条件语义差异）；test_migration_novelty=n/a

### 候选3：codeload URL 无扩展名 → BadZipFile（filename 字段）【复用既有知识】
- 查重：exact_duplicate=true —— E483（explicit-filename-in-get）、E276、E392（raw-makefile-conan-recipe-pattern 陷阱1）已完整覆盖同一根因与修复
- 决定：复用既有条目，不建新草稿

### 候选4：Raw Makefile 配方三要素（compiler_executables dict / make cwd / get filename）【复用既有知识】
- 查重：exact_duplicate=true —— E392 raw-makefile-conan-recipe-pattern 已覆盖
- 补充观察：Conan 2 移除 self.copy（AttributeError: has no attribute 'copy'）→ 用 conan.tools.files.copy；DRAFT-conan-delivery-chain-silent-traps 与 DRAFT-8958 已覆盖 copy() 用法，solution_overlap=high，不另建草稿

### 路径判定
- 候选1（alloca/musl）与候选2（patches list 格式）：已验证、可跨库复用、查重未命中或部分覆盖且存在新增差异 → **路径 B 成立（知识库扩展）**，建立 .md/.kv 草稿
- 候选3/候选4：完整重复，复用既有知识，不建草稿
- 决定：new_draft（知识库扩展 PR 前缀）
