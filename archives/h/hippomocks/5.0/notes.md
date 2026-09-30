# hippomocks 5.0 适配笔记

## 编译环境
- 构建系统: cmake (HippoMocksTest) + 官方 Makefile；header-only 库无独立编译产物
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `git worktree add -b feat/hippomocks-5.0 ../worktrees/hippomocks-5.0 main`（R01 授权创建，main=48d9cee6）
2. `python3 scripts/ohc-run.py init-build hippomocks 5.0 --url=<官方 codeload v5.0>`（sha256=de327a09…）
3. `python3 scripts/ohc-run.py lang-preflight hippomocks 5.0 --src $BUILD_SRC_DIR` → cpp 匹配
4. `cmake -S . -B build-ohos -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 3.0)` 与 CMake 4.x 不兼容，需该参数）
5. `cmake --build build-ohos -j4` → 修复 hippomocks.h 后 RC=0
6. `./build-ohos/HippoMocksTest/HippoMocksTests` → **75 of 75 tests successful** (rc=0)
7. `ctest --test-dir build-ohos` → 100% passed
8. `python3 scripts/ohc-run.py conan-init hippomocks 5.0` → 重写 header-only 配方
9. `python3 scripts/ohc-run.py refresh-patch --auto hippomocks 5.0` → 生成 0001-HippoMocks-hippomocks.h.patch
10. `python3 scripts/ohc-run.py conan-verify hippomocks 5.0` → G1-G4 + L2/L4/L5 全过
11. `python3 scripts/ohc-run.py finish hippomocks 5.0 built` → W3 本地 CI 模拟通过（L0/L1 pass, 100%）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | hippomocks.h:110 `__clear_cache` conflicting types | clang 将 `__clear_cache` 作为内建函数（签名 `void(void*,void*)`），上游 `char*` 声明重定义冲突 | 声明改为 `void*`（char* 可隐式转换） |
| 2 | 上游测试段错误 (SIGSEGV) at checkFunctionReplacedAndChecked | CFUNC 打桩的 `Replace` 在 SOME_ARM 分支写 32 位 ARM 指令（0xE59FF000 等），aarch64 执行非法指令；且打桩需 `mprotect` 文本页为 RWX，OHOS 内核 W^X 策略拒绝（实测 EINVAL） | aarch64 禁用 `_HIPPOMOCKS__ENABLE_CFUNC_MOCKING_SUPPORT`（上游自身以该宏门控 CFUNC 测试："If it's not supported, then don't test it"）；虚拟函数打桩 MockRepository 不受影响 |
| 3 | CMake 4.x 拒绝 `cmake_minimum_required(VERSION 3.0)` | CMake≥4 移除 <3.5 兼容 | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（配方内不修改上游 CMakeLists，仅构建参数） |
| 4 | conan create 按 zip 解压 codeload tar.gz | conandata URL 以 `v5.0` 结尾，无 `.tar.gz` 后缀，`get()` 默认 zip | conandata.yml 增加 `filename: hippomocks-v5.0.tar.gz` |
| 5 | Conan 2 无 `self.copy` | 模板遗留 Conan 1 API | 用 `conan.tools.files.copy` 并复制到 `include/` |
| 6 | test_package `cmake.test()` 找不到 test 目标 | `BUILD_TESTING` 守卫内 add_test 未启用 | test_package/CMakeLists.txt 顶层 `enable_testing()`；conanfile test() 直接 `self.run` 两个测试二进制（L0d 要求含 self.run） |
| 7 | W3 JC 全仓扫描误报他库杂项文件 | full 模式扫描整仓发现 main 上既有 cloog/kics `.build-closed`/`.staging-verified`（空文件，非本 PR 内容） | 以 PR diff 作用域（pr.diff）模拟 CI 口径；记录基线路径与 SHA-256（e3b0c44… 空文件），隔离复验通过后继续，未提交他库文件 |

## 源码修改

- `patches/0001-HippoMocks-hippomocks.h.patch`：①`_HIPPOMOCKS__ENABLE_CFUNC_MOCKING_SUPPORT` 增加 `&& !defined(__aarch64__)`；②`__clear_cache` 声明 `char*`→`void*`（+注释）。orig sha256(头文件)=480fa9ca2eaec055，work=06cf8afb7be17f3a

## 依赖版本

- 无第三方运行时依赖（header-only）；工具链 clang 15.0.4 / cmake 4.1.2 / conan 2.29.1 / make 4.4.1

## 验证结果

```bash
./build-ohos/HippoMocksTest/HippoMocksTests  # 75 of 75 tests successful (rc=0)
ctest --test-dir build-ohos                  # 100% tests passed
python3 scripts/ohc-run.py conan-verify hippomocks 5.0  # G1-G4/L2/L4/L5 PASS
python3 scripts/ohc-run.py finish hippomocks 5.0 built   # W3 L0/L1 pass
```

## 知识候选台账（knowledge_candidate_ledger）

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 |
|---|---|---|---|---|---|
| C1: aarch64 CFUNC 打桩不可用 | 上游测试在 aarch64 SIGSEGV（首个崩溃 checkFunctionReplacedAndChecked）；文本页 mprotect RWX 实测 EINVAL | 上游 Replace 的 SOME_ARM 分支仅写 32 位 ARM 指令；且打桩需文本页 RWX，OHOS W^X 拒绝 | aarch64 禁用 `_HIPPOMOCKS__ENABLE_CFUNC_MOCKING_SUPPORT`（上游以该宏门控 CFUNC 测试）；虚拟函数打桩不受影响 | 75/75 上游测试全过；conan-verify G1-G4 全过；消费者/鸿蒙专项测试通过 | 所有在 aarch64/OHOS 上使用 hippomocks 的消费者；同类依赖文本页打桩的 C++ mock 框架（参考 E045 W^X 家族） |
| C2: `__clear_cache` clang 内建签名冲突 | clang 编译 hippomocks.h conflicting types | clang 内建 `void(void*,void*)` vs 上游 `char*` 声明 | 声明改 `void*` | 编译通过 | 任何在 clang 下包含 hippomocks.h 的 OHOS/ARM 构建 |

### 七轴查重（对照 knowledge/graph/ 既有条目）

- **exact_duplicate**: false — index.tsv 无 hippomocks/mock-framework 同错误条目（E045 为 ctypes/libffi closure 的 mmap RWX 拒绝，非 C++ mock 打桩）
- **causal_duplicate**: false — E045 根因为 W^X 策略（mmap 分配 RWX 被拒），C1 根因是上游代码仅支持 32 位 ARM 指令 + 文本页 mprotect RWX 被拒；同属 W^X 家族但实体不同（分配 vs 已有文本页打桩）
- **trigger_overlap**: 部分 — E045 match_keywords 含 mprotect/PROT_EXEC/Invalid argument；C1 触发面为编译期 conflicting types + 运行期 SIGSEGV + 打桩 mprotect EINVAL，重叠仅限 mprotect 关键词
- **solution_overlap**: 无 — E045 方案为平台限制记录；C1 方案为宏级禁用 + 保留虚拟函数打桩，无既有条目给出该方案
- **combination_novelty**: 有 — 「aarch64 上 CFUNC 打桩禁用」+「__clear_cache void* 签名修复」+「以 PR diff 作用域处理全仓 JC 误报」组合无既有条目覆盖
- **boundary_novelty**: 有 — 明确给出适用边界：CFUNC 打桩禁用不影响 MockRepository 虚拟函数打桩；上游 CFUNC 测试以宏门控可安全排除；文本页 mprotect EINVAL 为 OHOS 内核硬限制（E045 佐证）
- **test_migration_novelty**: 有 — 75/84 全量口径 + 75/75 可执行集合口径双台账与 9 个未实例化用例的逐项映射（MSVC-only 6 + CFUNC 3），可跨库复用为 mock 类库测试台账模板

### 关系字段

- similar_to: E045（W^X 家族，mprotect/mmap RWX 拒绝；触发面不同）
- caused_by: 上游 hippomocks 5.0 仅实现 32 位 ARM CFUNC 打桩；OHOS 内核 W^X（E045 同因）
- prerequisite_of: 无
- conflicts_with: 无

### 路径决定

- **C1+C2 合并为路径 B（知识库扩展）**：已验证（75/75 + conan-verify 全过）、可跨库复用（mock 框架打桩类）、查重为未命中（C1）/部分覆盖（C2 无既有条目）→ 建立同 stem 的 .md/.kv 草稿 `DRAFT-hippomocks-5.0-cfunc-mock-aarch64-wx.kv/.md`
- reuse_existing: false（无既有条目可复用，E045 仅覆盖 W^X 原则面）
- new_draft: true（DRAFT-hippomocks-5.0-cfunc-mock-aarch64-wx）
- path_a_no_knowledge: false

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方（package_type=header-library，copy 头文件到 include/） |
| conandata.yml | 官方 codeload v5.0 源 + sha256 + filename + patches 声明 |
| test_package/ | 消费者用例 test.cpp + 鸿蒙专项 test_ohos.cpp + MANIFEST.yml 台账 |
| patches/0001-HippoMocks-hippomocks.h.patch | aarch64 CFUNC 禁用 + __clear_cache void* |
| reports/test-report.md | 双口径测试台账（75/84 全量、75/75 可执行） |
| knowledge/drafts/DRAFT-hippomocks-5.0-cfunc-mock-aarch64-wx.kv/.md | 路径 B 草稿 |

## 注意事项

- 全仓 JC full 模式会扫描 main 上其他库既有杂项文件（cloog/kics 空标记），本 PR 以 pr.diff 作用域模拟 CI 口径，未提交任何他库文件
- 上游测试 9 个未实例化用例全部有明确上游互斥条件（_MSC_VER / CFUNC 宏），非跳过或失败

**编译结束**: 2026-09-28 09:53
**最终状态**: built
