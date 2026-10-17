# math-sll 1.24 适配笔记

## 知识候选台账 + 七轴查重 + 路径判断（知识库扩展，Path B）

### 候选 1：上游裸 Makefile 静态库产物无 lib 前缀（math-sll.a），CMakeDeps 按惯例查找 libmath-sll.a 失败

- 真实错误：test_package 阶段 `Library 'math-sll' not found in package. If 'math-sll' is a system library, declare it with 'cpp_info.system_libs'`
- 根因：上游 Makefile 产物名为 `math-sll.a`（无 `lib` 前缀），conan package() 原样复制后，CMakeDeps 按 Linux/OHOS 惯例拼出 `libmath-sll.a` 查找，找不到库文件
- 修复：package() 复制后 `os.rename` 为 `libmath-sll.a`
- 验证：conan-verify G2 修复后 PASS（test_package 9/9 断言通过）；test_ohos T1/T2/T3 ALL PASS
- 适用范围：任何上游裸 Makefile 输出非 `lib<name>.a` 命名归档的静态库
- 四范围查重：
  - knowledge/graph（正式条目）：无（E277 vendored/E355 meson/E524 SYS_PREFIX 注入均无关）
  - knowledge/doc：无
  - knowledge/drafts：DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package 仅症状同名（同一报错串），根因是该库 CMake add_subdirectory 产物落 build 子目录、package() 漏复制；本候选根因是"文件已复制但命名无 lib 前缀"，修复操作不同（os.rename vs 递归复制），非 causal_duplicate
  - knowledge/graph/index.tsv：无相关命中

**七轴查重**：
| 轴 | 结论 |
|---|---|
| exact_duplicate | false（无同名条目） |
| causal_duplicate | false（embedded-cli 草稿根因为 add_subdirectory 子目录布局漏复制，本候选根因为命名无 lib 前缀，机制不同） |
| trigger_overlap | partial（与 DRAFT-embedded-cli 共享 "Library ... not found in package" 报错串与静态库场景，但触发条件不同） |
| solution_overlap | partial（均修改 package()，但本候选为 os.rename 重命名，非递归复制） |
| combination_novelty | true（裸 Makefile 无 lib 前缀归档 + CMakeDeps 命名约定不匹配的组合首次沉淀） |
| boundary_novelty | true（边界为"上游产物已复制但命名不符合 lib<name> 约定"，区别于 embedded-cli"产物未复制"边界） |
| test_migration_novelty | true（消费者断言对迭代倒数 slldiv/sllsqrt 用 1e-6 容差可跨库复用） |

关系字段：`similar_to=DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package`；`caused_by=上游 Makefile 产物命名约定`；`prerequisite_of=无`；`conflicts_with=无`
决定：`new_draft` → 草稿 `knowledge/drafts/DRAFT-math-sll-1.24-raw-makefile-lib-prefix-rename.{kv,md}`

### 候选 2：`tools.build:compiler_executables` 为 dict 整体 conf，不能按 `:c` 键取

- 真实错误：`[conf] 'tools.build:compiler_executables:c' does not exist in configuration list`
- 根因：本环境 conan 2.29.1 中该 conf 是字典（整体取值 + key 索引），模板 `conanfile-makefile.py.tmpl` 的 `:c` 键写法在 G2 直接抛 ConanException
- 修复：`self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后按 `compilers.get("c","clang")` 取
- 验证：conan-verify G2 PASS
- 查重：graph/doc/drafts/index.tsv 均无该 conf 键访问方式条目（E528 涉及该 conf 用于 Autotools 环境闭合，非 dict 访问模式）
- 决定：`path_a_no_knowledge`（单行配方写法要点，价值低、随配方自含，不建草稿；已在 manifest.yaml knowledge_gained 记录）

### 候选 3：basic_layout 下 make 需 `cwd=self.source_folder`（Makefile 在 source 目录而非 build 目录）
- 真实错误：`make: *** No targets specified and no makefile found`
- 修复：`self.run("make ...", cwd=self.source_folder)`
- 查重：E097（custom-config-mk）/DRAFT-8958（clthreads stage-install-shadow）/DRAFT-3d-ascii（raw-makefile 模式）覆盖相近场景，属既有知识复现，无新增差异
- 决定：`reuse_existing`（不建新草稿）

### 候选 4：上游零测试库的双口径台账口径（source_declared_total=0，全量 0/0）
- 枚举证据：Makefile 仅 all/clean/install；无 tests/、无内嵌 main/assert；无 ctest/meson/autotools 注册
- 查重：E308（test_package 后缀）/box2d 空套件草稿覆盖空测试集口径；本候选为"上游从设计上无测试"台账写法，与既有 E308/box2d 空套件草稿 `similar_to`，无新增机制
- 决定：`reuse_existing`（台账写法已在 notes.md/test-report.md 落地，不建草稿）

**路径结论：Path B（知识库扩展）成立 —— 候选 1 已验证、可跨库复用、查重未命中/部分覆盖且存在新增差异，须建立草稿对。**

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（OHOS aarch64 交叉工具链 /data/service/hnp/bin/clang）
- 状态: built

## 编译步骤

```bash
# 探索性编译（本机验证）
cd $BUILD_SRC_DIR
make clean
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib STRIP=true all

# Conan 干净构建（OHOS aarch64 profile）
conan create archives/m/math-sll/1.24 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tools.build:compiler_executables:c` conf 不存在 | 该 conan 版本 conf 是字典整体 `tools.build:compiler_executables` | 改为 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 后按 key 取 c/ar/ranlib |
| 2 | `make: No targets specified and no makefile found` | basic_layout 将构建放在 build 子目录，Makefile 在 source 目录 | build() 中 `self.run(..., cwd=self.source_folder)` |
| 3 | CMakeDeps `Library 'math-sll' not found in package` | 上游产物名 `math-sll.a` 无 lib 前缀，CMakeDeps 按惯例查找 `libmath-sll.a` | package() 复制后 `os.rename` 为 `libmath-sll.a` |
| 4 | test_package 断言 `slldiv(3.0,2.0)==1.5` 失败 | 上游 `_slldiv(X,Y)=sllmul(X, sllinv(Y))` 迭代求倒数有舍入 | 对倒数类近似运算（slldiv/sllsqrt/sin/cos）用 1e-6 容差断言 |
| 5 | /tmp 只读 | 设备 /tmp 只读文件系统 | 测试脚本用 $TMPDIR（/storage/Users/currentUser/tmp） |

## 源码修改

无补丁（patches/ 为空）。未修改任何上游源码。

## 依赖版本

无第三方依赖（纯 C 定点数数学库，仅 libc/libm 基础函数）。

## 验证结果

```bash
# conan-verify 8 道门禁全过（G0-G4 + L2/L4/L5）
# 上游测试枚举：Makefile 仅 all/clean/install，无 make check、无测试文件、
#               无内嵌 main()/assert 自测 → 上游独立测试用例数 = 0
# 鸿蒙专项测试 test_ohos/run_ohos_test.sh：T1 aarch64 归档 / T2 无宿主路径泄漏 /
#                                          T3 消费者编译链接运行 → ALL PASS
# test_package 消费者用例：9 项定点数 API 数值断言 → PASS
```
---

**编译结束**: 2026-09-28 16:52
**最终状态**: built
