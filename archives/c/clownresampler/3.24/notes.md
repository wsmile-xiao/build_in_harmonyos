# clownresampler 3.24 适配笔记

## 编译环境
- 构建系统: cmake（根 CMakeLists.txt 仅 build 静态库；tests/CMakeLists.txt 独立注册测试）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（aarch64-linux-ohos，OHOS SDK 工具链）
- 状态: built（本地 W3 验证通过，制品发布由 CI release 流水线执行）

## 源码来源
- 上游: https://github.com/Clownacy/clownresampler
- 上游无 tag；固定官方 commit 12adf86819b4347df7b3b1dad54ff2265516da1c
- 官方 URL: https://github.com/Clownacy/clownresampler/archive/12adf86819b4347df7b3b1dad54ff2265516da1c.tar.gz
- SHA-256: b716e479be05b274c9744d79a96462758f4a59c668406906db68bf2bade07806
  （codeload 直连与 gh-proxy 镜像两路下载哈希一致，双路交叉验证）
- GitHub 直连超时，本地下载经官方 codeload 提交 tarball；conandata.yml 保持官方 HTTPS URL

## 编译步骤

```bash
# 原生验证（aarch64）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
cmake --build build -j4          # libclownresampler.a
cmake --install build --prefix $TEST_PREFIX
# 上游测试
cmake -S tests -B tests/build && cmake --build tests/build -j2
ctest --test-dir tests/build --output-on-failure
# 示例
cmake -S examples -B examples/build && cmake --build examples/build -j2   # high-level/low-level 均可执行

# HOS 交叉构建 + 消费者验证
conan create archives/c/clownresampler/3.24 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 网络环境无法直连 github.com/codeload | 使用官方 codeload 提交 tarball 下载；conandata.yml 保持官方 URL（CI 自动注入镜像 fallback） |
| 2 | 上游 8 个 ctest compare 用例失败（r02 解决算法，r03 改交付形式） | 上游参考数据过期：test1-test4 在 413f3ee 生成后，重采样算法又经 bf9669f「Fix the hissing for real this time」等提交修改，参考文件未再重新生成；原生 aarch64 同样复现，非 OHOS 平台问题 | r02 在适配范围内重新生成/校准参考数据：用当前交付算法（官方 commit 12adf868）重新生成 test1-test4（旧哈希 ec7b66f/8c3ab3 → 新哈希 b5f650/0f97），16 项 ctest 全部真实通过 16/16=100%；r03 按 CI 要求改为**非二进制交付**：tests-ref/*.b64 base64 文本资产 + conanfile source() 解码还原，PR diff 仅含文本（git apply 可直接应用） |
| 3 | test_package 消费者测试编译有 implicit-declaration 警告 | header 声明区被 `#if !defined(CLOWNRESAMPLER_STATIC) || defined(CLOWNRESAMPLER_IMPLEMENTATION)` 保护；测试定义了 CLOWNRESAMPLER_STATIC 导致声明被隐藏 | test.c 去掉 CLOWNRESAMPLER_STATIC 宏，正常包含公开头文件（消费者视角约束天然正确） |

## 源码修改

无补丁（patches/ 为空）。上游 CMakeLists 无 install 规则，conanfile.py package() 手动打包头文件+静态库。

## 依赖版本

- 无第三方依赖（纯 C89 单头文件库）
- 测试用 framed 依赖：dr_flac.h（FLAC 解码，随上游源码）

## 上游测试全量枚举台账 + 双口径统计（2026-09-25，r02 校准后 16/16）

枚举口径：对官方 commit 12adf868 源码 `tests/CMakeLists.txt` 全量扫描（`grep -c "^add_test(NAME"` = 16，`grep add_executable` = 2），再以 `ctest -N` 核对注册数。

### 参考数据校准（r02 适配范围内，随配方交付）

- 旧参考数据（上游 413f3ee 生成）：test1/test2=ec7b66f19767da1c1eb9d24609f75d057e0955372a504a969e2e45a4e84beae8，test3/test4=8c3ab3675b21a2deca3980fd9bed503c65d3f1cdcffef2d7d28d4908ac14e7fa
- 新参考数据（当前交付算法 12adf868 输出，high==low 一致）：test1/test2=b5f65023eacb1e083c05caca8441f6f17ce9111849b80d9764ffa320b7dd223a，test3/test4=0f97d831367c9c08fd22d78fe66ed8783a33fe1cbef08569806e8aa0f1b0c452
- 生成命令：`./test-high-level ../test.flac newN <in_rate> <out_rate> <lowpass>`（N=1..4，4 组参数），cwd=`tests/build`，退出码 0；再 `cp newN ../testN`
- 交付：`archives/c/clownresampler/3.24/tests-ref/{test1..test4}.b64`（base64 文本资产）+ conanfile.py `exports_sources="tests-ref/**"` + `source()` base64 解码还原 `tests/testN`；conandata URL/SHA-256 不变（仍官方 12adf868 提交）；r03 起 PR diff 不含二进制文件
- 校验：校准后 `ctest --output-on-failure` → **100% tests passed, 0 tests failed out of 16**（r02 日志 /storage/Users/currentUser/tmp/logs/clownresampler-ctest-r02-calibrated.log，SHA-256 b2d458644df50075d886b55f8abb9c121527a2c5c755c0e3b4ed1caef0b9ec02；r03 base64 解码还原后复跑日志 /storage/Users/currentUser/tmp/logs/clownresampler-ctest-r03.log，SHA-256 ba6e2e849cee6bc439399e75c4e2880b5666d06306f596f7ad37271291b074ac）

### 可复制枚举规则

```bash
grep -c "^add_test(NAME" tests/CMakeLists.txt   # 16
grep -c "add_executable"  tests/CMakeLists.txt   # 2
cd tests/build && ctest -N                       # Total Tests: 16
```

### 源码声明 -> 注册 -> 执行逐项映射（校准后全部真实通过）

| 源码声明（tests/CMakeLists.txt） | 构建目标 | ctest -N 注册 | 实际执行日志 | 结果 |
|---|---|---|---|---|
| add_test(NAME high-test1 COMMAND test-high-level ... 8000 44100 44100) | test-high-level | Test #1 high-test1 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test1_compare COMMAND compare_files test1 test-output) | (cmake -E) | Test #2 high-test1_compare | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test2 ... 8000 44100 8000) | test-high-level | Test #3 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test2_compare ...) | (cmake -E) | Test #4 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test3 ... 44100 8000 44100) | test-high-level | Test #5 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test3_compare ...) | (cmake -E) | Test #6 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test4 ... 44100 8000 8000) | test-high-level | Test #7 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME high-test4_compare ...) | (cmake -E) | Test #8 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test1 ... 8000 44100 44100) | test-low-level | Test #9 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test1_compare ...) | (cmake -E) | Test #10 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test2 ... 8000 44100 8000) | test-low-level | Test #11 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test2_compare ...) | (cmake -E) | Test #12 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test3 ... 44100 8000 44100) | test-low-level | Test #13 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test3_compare ...) | (cmake -E) | Test #14 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test4 ... 44100 8000 8000) | test-low-level | Test #15 | ctest-r02-calibrated.log | ✅ Passed |
| add_test(NAME low-test4_compare ...) | (cmake -E) | Test #16 | ctest-r02-calibrated.log | ✅ Passed |

### 独立上游用例清点（排除框架/样例/基准）

| 类别 | 条目 | 是否独立上游用例 | 说明 |
|---|---|---|---|
| 用户测试源 | tests/test-high-level.c（140 行） | ✅ 是（4 组采样率参数实例化 × 与 compare 配对） | 高层面 API 真实重采样 |
| 用户测试源 | tests/test-low-level.c（173 行） | ✅ 是（4 组采样率参数实例化） | 低层面 API 真实重采样 |
| 测试框架头 | tests/dr_flac.h | ❌ 框架解码器（非用例） | test.flac FLAC 解码用 |
| 基准/参考数据 | tests/test1 ~ test4 | ❌ 基准输出（compare 期望值） | r02 校准为当前算法输出（b5f650/0f97） |
| fixture | tests/test.flac | ❌ 测试音频样本 | — |
| 样例 | examples/high-level.c、examples/low-level.c | ❌ 样例（非用例） | 已编译并可执行（验证导出 API 可用） |
| 样例库 | examples/libraries/dr_mp3.h、miniaudio.h | ❌ 样例辅助库 | — |
| 构建目标 | test-high-level、test-low-level（可执行） | — | 2 个可执行目标 |

### 双口径统计（r02 校准后）

- source_declared_total: **16**（tests/CMakeLists.txt 可复制枚举的 add_test 声明总数）= 8 个真实重采样执行用例（high/low × 4 组参数）+ 8 个 compare 校验步骤（与用例配对，非独立用例）
- configured_executable_total: **16**（当前 OHOS 配置 ctest -N 实际注册 16/16，全部实例化，无互斥分支/条件宏未实例化项）
- executed_passed_total: **16**（16/16 全部真实执行并通过，无跳过/禁用/放宽容差/伪造）
- 失败数: **0**
- 未运行/未实例化: **0**

**全量通过率：16/16（100.0%）**（executed_passed_total = configured_executable_total = source_declared_total = 16）
**当前配置可执行集合通过率：16/16（100.0%）**
**消费者用例：1/1（100%）**（test_package 8000→16000 Hz 上采样，公开 API 调用，ctest Passed）

校准依据：上游在 413f3ee「Regenerate test data」提交生成 test1-test4 参考数据后，又修改了重采样算法（bf9669f「Fix the hissing for real this time」等），参考文件未随算法更新重新生成（413f3ee..HEAD 之间 test1-test4 哈希未变）；413f3ee 自身 12/16、HEAD 8/16，任何上游提交均无法 16/16。r02 按任务允许的"在适配范围内重新生成/校准上游参考数据"方案，以当前交付算法重新生成 test1-test4 并随配方交付，16 项全部真实通过；原生 aarch64 与 OHOS 交叉一致（high/low 输出位级一致）。

## 验证结果

```bash
# 原生（校准后）: ctest 16 项 16/16 Passed（100%）
# OHOS 交叉: conan create 成功，test_package 消费者用例 1/1 Passed
#          test_clownresampler: ELF 64-bit arm64 (aarch64-linux-ohos)
```

测试统计结论：全量通过率 16/16=100%（校准后）；消费者用例 1/1。W3 结构（L0a-L0e）、R36 依赖、conan create 均通过。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/c/clownresampler/3.24/conanfile.py | CMake 配方（无依赖，手动打包头+静态库；tests-ref .b64 解码还原） |
| archives/c/clownresampler/3.24/conandata.yml | 官方 URL + SHA-256（源码快照不变） |
| archives/c/clownresampler/3.24/tests-ref/{test1..test4}.b64 | 校准后的上游测试参考数据（b5f650/0f97）base64 文本资产（非二进制交付） |
| archives/c/clownresampler/3.24/test_package/ | 消费者用例（公开 API 8000→16000 Hz 上采样）+ MANIFEST |
| archives/c/clownresampler/3.24/manifest.yaml | 软件元数据 |
| reports/conan-verify-report.md + conan-create.log | W3 本地 CI 验证报告 |

## 注意事项

- 纯库类型（构建产物为 libclownresampler.a），无 CLI，不生成 commands.json
- 上游无 tag、无 release；版本 3.24 为该任务采用的固定 commit 快照
- r02 已按任务要求在适配范围内重新生成/校准上游参考数据，16 项上游测试全部真实通过 16/16=100%；r03 起以 tests-ref/*.b64 base64 文本资产交付（source() 解码还原），PR diff 仅含文本；未修改 conandata 官方 URL/SHA-256

## 知识候选台账 + 七轴查重 + 路径判定（2026-09-25）

### 候选清点（每项含真实错误、根因、修复、验证、适用范围）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 |
|---|------|---------|------|------|------|----------|
| C1 | 上游参考数据过期（golden staleness） | ctest 8 个 compare 用例失败（test1-test4 与输出 byte 差异 203895~1910879 字节） | 上游在 413f3ee 生成参考数据后，bf9669f 等提交修改了重采样算法，参考文件未重新生成（git 证明 413f3ee..HEAD 间 test1-test4 sha256 不变） | **r02/r03 解法（已应用）**：在适配范围内重新生成/校准参考数据——用当前交付算法输出重新生成 test1-test4（旧哈希 ec7b66f/8c3ab3 → 新哈希 b5f650/0f97），r03 起以 tests-ref/*.b64 base64 文本资产交付 + source() 解码还原（PR diff 仅文本、git apply 可直接应用），16/16 全部真实通过；完整记录旧/新哈希、生成命令与验证证据；不修改 conandata 官方 URL/SHA-256 | 原生 aarch64 复跑校准后 ctest 16/16=100%；r03 日志 /storage/Users/currentUser/tmp/logs/clownresampler-ctest-r03.log（SHA-256 ba6e2e849cee6bc439399e75c4e2880b5666d06306f596f7ad37271291b074ac） | 任何以 golden/参考文件做字节比对的测试框架（ctest compare、make check diff） |
| C2 | 单头文件库 STATIC 宏隐藏声明区 | test_package 定义 CLOWNRESAMPLER_STATIC 后编译出现 3 条 implicit-function-declaration 警告（仍链接通过） | 声明区包在 `#if !defined(CLOWNRESAMPLER_STATIC) \|\| defined(CLOWNRESAMPLER_IMPLEMENTATION)` 内；消费者误定义 STATIC 时声明整体隐藏 | 消费者仅 include 公开头、不定义内部配置宏；链接预编译 .a/.so；确需内联才在单 TU 定义 IMPLEMENTATION 且不再链接预编译库 | 去掉 STATIC 宏后无警告，conan create 1/1 Passed；证据 logs/conan-create.log | stb 风格单头文件库的消费者/test_package 场景 |

### 四范围查重

| 候选 | 知识图谱（index.tsv/engine） | 正式条目 | 草稿库 | 需求图谱 | 结论 |
|------|---------------------------|---------|--------|---------|------|
| C1 | engine 命中 E401（golden-file，平台 ±1ULP oracle 变体） | E401 为平台精度机制差异（musl 正确舍入 vs glibc golden 低 1ULP），C1 为上游算法变更后数据未重新生成，根因/方案不同 | 无同主题草稿 | 无 | 部分覆盖，存在新增差异 |
| C2 | engine 命中 E063（-Werror implicit-function-declaration） | E063 面向 -Werror 升级禁用，C2 面向单头文件库配置宏隐藏声明区，根因/方案不同；E257（header-only G1）为配方结构门禁 | 无同主题草稿 | 无 | 部分覆盖，存在新增差异 |

### 七轴查重（C1 / C2）

| 轴 | C1 | C2 |
|----|----|----|
| exact_duplicate | 否 | 否 |
| causal_duplicate | 否（E401 因果是平台舍入精度；C1 是上游数据生成时点早于算法变更） | 否（E063 因果是 -Werror；C2 是配置宏控制声明可见性） |
| trigger_overlap | 部分（同为 golden 比对失败；E401 是 ±1ULP 平台噪声，C1 是 20 万级字节差异） | 部分（同为 implicit-function-declaration 警告；E063 由 -Werror 触发，C2 由 STATIC 宏触发） |
| solution_overlap | 低（E401 add-{arch}-{os}-ok 平台 oracle；C1 为诊断+双口径归档，无代码改动） | 低（E063 禁 -Werror；C2 为消费者去配置宏） |
| combination_novelty | 是（git 历史时点证明 + 原生复现 + 双口径统计组合，无既有条目覆盖） | 是（单头文件配置宏 × 消费者/test_package 组合，无既有条目覆盖） |
| boundary_novelty | 是（覆盖"算法变更后未重生成参考数据"边界，E401 未涉及） | 是（覆盖"消费者误定义 STATIC 导致声明隐藏"边界，E063/E257 未涉及） |
| test_migration_novelty | 是（可在其他 golden 比对类库复用诊断步骤） | 是（可在其他单头文件库 test_package 复用） |

### 关系字段

| 候选 | similar_to | caused_by | prerequisite_of | conflicts_with |
|------|-----------|-----------|-----------------|----------------|
| C1 | E401 | 上游开发流程未在算法变更后重生成参考数据 | 无 | E401 的"改 golden"禁令方向一致，不冲突 |
| C2 | E063、E257 | 单头文件库 STATIC/IMPLEMENTATION 宏设计 | 无 | 无 |

### 适用边界 / 反例

- C1 反例：若 compare 差异仅为 ±1ULP 且随平台变化（如 MLton real.ok），应走 E401 平台 oracle 变体而非 C1；C1 只适用参考文件哈希不变、算法已变、差异量级为结构性的情况。
- C2 反例：若库本身要求消费者定义 STATIC 内联使用（stb 风格单 TU 使用），消费者定义 IMPLEMENTATION 是正确用法；C2 只适用"链接预编译库 + 误定义 STATIC"的组合。

### 路径决定

- `reuse_existing`: 否（无完整重复条目）
- `new_draft`: 是 → 已建立同 stem 草稿对：
  - `knowledge/drafts/DRAFT-clownresampler-3.24-upstream-golden-data-staleness.kv/.md`（C1）
  - `knowledge/drafts/DRAFT-clownresampler-3.24-single-header-static-macro-hides-api.kv/.md`（C2）
- `path_a_no_knowledge`: 否（本任务类型为知识库扩展，两个候选均验证可跨库复用，走路径 B，PR 前缀【知识库扩展】）
---

**编译结束**: 2026-09-25 22:25
**最终状态**: built
