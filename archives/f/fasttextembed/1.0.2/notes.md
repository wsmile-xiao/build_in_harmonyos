# fasttextembed 1.0.2 — 适配笔记

## 库概览

- 上游：https://github.com/cemsina/fasttextembed（官方 tag `v1.0.2`，MIT）
- 类型：纯 C 库（libfte.a / libfte.so）+ CLI（fte_cli），零第三方依赖（仅 libm）
- 功能：BAAI/bge-small-en-v1.5 文本向量化推理引擎（384 维）
- 构建系统：CMake（C11），无 install() 规则 → 配方手动打包
- 模型：66MB `.fte` 权重由 Git-LFS 托管，官方源码 tarball 仅含 LFS 指针（model.fte 133B），
  实际权重需 `media.githubusercontent.com` 拉取（本环境多次尝试均超时，仅下载 1.2MB~3.7MB/66MB）

## 适配要点

1. **native 标志关闭（补丁 0001）**：上游 CMake 自动 `check_c_compiler_flag("-mcpu=native" / "-march=native")`，
   按构建主机 CPU 编译，跨平台交叉编译不可复现。补丁新增 `FTE_DISABLE_NATIVE_CPU` option，
   配方置 ON，保证 OHOS 交叉构建可复现。arm64 的 NEON 路径由 `__aarch64__` 自动选择，无性能回退。
2. **打包**：include/fte/fte.h + libfte.a（shared 时 libfte.so）+ fte_cli（commands.json 已声明）。
3. **LFS 模型不可得**：test_e2e 与 test_kernels 的 loader 子检查需要真实模型；缺少时按上游设计
   SKIP（exit 0）。恢复条件：从 Git-LFS media 端点下载 66MB model.fte 后重跑。

## 上游测试台账（双口径）

### 判定：独立上游用例 = 用户测试源中由 CMake add_test 注册的独立测试程序

| # | 入口（源） | 独立用例? | 分类理由 | 构建目标 | ctest 注册 | 实际运行 | 结果 | cmd/cwd/rc |
|---|-----------|----------|---------|---------|-----------|---------|------|-----------|
| 1 | tests/test_kernels.c | ✅ 是 | 用户测试源的独立 test 程序（6 个子检查：arena/layernorm/fastgelu/softmax/matmul/loader） | test_kernels | Test #1 | ✅ | PASS（rc=0，输出 "OK"；其中 loader 子检查因无 LFS 模型 SKIP） | `$B/test_kernels`，cwd=src，rc=0 |
| 2 | tests/test_tokenizer.c | ✅ 是 | 用户测试源的独立 test 程序（basic + golden 对拍 4 行） | test_tokenizer | Test #2 | ✅ | PASS（rc=0，"checked 4 golden token rows / OK"） | `$B/test_tokenizer`，cwd=src，rc=0 |
| 3 | tests/test_e2e.c | ✅ 是 | 用户测试源的独立 e2e test（需 66MB LFS 模型 model.fte） | test_e2e | Test #3 | ✅ | **PASS（r02 已获取 LFS 模型并真实对拍：doc0-3 cos≈0.9999997，rc=0，"OK"）** | `$B/test_e2e`，cwd=src，rc=0 |

### 非独立用例（台账明确列出，不计入独立用例）

| 类别 | 条目 | 不计入原因 |
|------|------|-----------|
| 基准/工具脚本 | tools/bench.py、tools/bench_all.py、tools/plot_results.py、tools/convert.py | 基准/工具，非测试用例 |
| 样例数据 | corpus.txt、vocab.tsv、model.fte（Git-LFS 托管，r02 已获取真实 66MB）、assets/benchmark.png | 数据/资源，非测试程序 |
| 测试 fixture | tests/data/golden_docs.txt、golden_meta.txt（4×384）、golden_tokens.txt（4 行）、golden_tokens.json、golden_vecs.f32 | 测试对拍数据 |
| 绑定层测试 | bindings/go/embed_test.go、bindings/js/test.js、bindings/rust/examples/embed.rs | 语言绑定侧测试，不属于 C 核心 CMake 构建目标 |

### 映射链（宏/注册 → 构建目标 → CTest → 执行日志）

```
CMakeLists.txt add_test（test_kernels/test_tokenizer/test_e2e，WORKING_DIRECTORY=CMAKE_SOURCE_DIR）
  → ctest -N：3 项注册（Test #1/#2/#3）
  → r02 实际执行（真实 66MB LFS 模型已获取）：
      $ {{BUILD}}/Release/test_kernels  → "OK"（rc=0）
      $ {{BUILD}}/Release/test_tokenizer → "checked 4 golden token rows / OK"（rc=0）
      $ {{BUILD}}/Release/test_e2e      → "doc 0 cos=0.9999996 … doc 3 cos=0.9999997 / OK"（rc=0）
```

### 统计口径（最终回报以此为准，r02 更新）

- `source_declared_total` = **3**（tests/ 下 3 个独立测试源文件，每个独立 add_test 注册）
- `configured_executable_total` = **3**（OHOS CTest 实际实例化 3 个可执行用例）
- `executed_passed_total` = **3**（test_kernels、test_tokenizer、test_e2e 全部实跑通过）
- 失败 = 0；未运行/不可运行/SKIP = **0**
- **全量通过率 = 3/3 = 100%**（r02 达成赛事 100% 验收要求）
- 实际执行集合通过率 = 3/3 = 100%
- 附加说明：`conan create` 构建期 `cmake.test()` 亦运行上述 3 项（r02 日志 test_e2e 耗时 0.91s，真实加载模型非 SKIP），test_package 消费者测试 1/1 通过。

## 验证产物

- conan create（ohos-aarch64 profile）：✅ 通过（含 CTest + test_package）
- 包内产物：include/fte/fte.h、lib/libfte.a、bin/fte_cli、share/fasttextembed/vocab.tsv

## 知识候选台账与七轴查重（路径判断）

### 候选 1：CMake `check_c_compiler_flag` 自动启用 host-CPU native 标志 → option 门控关闭

- 真实问题：上游 CMakeLists 用 `check_c_compiler_flag("-mcpu=native"/"-march=native")`
  动态探测并按构建机 CPU 注入 flags，OHOS 交叉构建产物不可复现；且该形态
  无 cache 变量可覆盖（区别于 ascon-c 的 REL_FLAGS），配方只能靠补丁加 option 门控。
- 根因：host-CPU native 标志把构建机 CPU 特性固化进产物。
- 修复：补丁 0001 新增 `FTE_DISABLE_NATIVE_CPU` option + if(NOT ...) 门控，
  配方 generate() 置 ON；arm64 NEON 由 `__aarch64__` 自动选择，无性能回退。
- 验证：conan create G2 通过（clang 15 / ohos-aarch64），test_package 1/1，
  鸿蒙专项端到端 1/1（l2norm=1.0）。
- 适用范围：CMake 项目在 CMakeLists 内动态探测 native CPU 标志的交叉构建。
- 正式知识（doc/）查重：无直接命中（E528 是 autotools 工具链 PATH 类，不同）；
  图谱（E*.kv）查重：无 `mcpu`/`march` 命中；
  草稿四范围查重：`DRAFT-ascon-c-1.3.0-cmake-rel-flags-combined-lib-naming`
  部分覆盖（同为 native 标志族，但 ascon-c 是 **cache 变量覆盖**形态，本条是
  **check_c_compiler_flag 动态探测 + option 门控**形态，属同族不同形态的新增差异）。

### 候选 2：上游 Git-LFS 托管 66MB 模型，官方 tarball 仅含 133B 指针 → 需获取 LFS 模型实跑 e2e（r02 达成 3/3）

- 真实问题：model.fte 是 LFS 指针，官方 tarball 不含实际权重，test_e2e 走上游
  SKIP 路径（"SKIP e2e", exit 0）；不可把 SKIP 当 PASS，也不可伪造模型。
- 根因：Git-LFS 对象不随 GitHub tag archive 分发（codeload 仅得指针）。
- r02 修复：从 LFS 官方端点实际拉取模型（media.githubusercontent.com/media/cemsina/fasttextembed/v1.0.2/model.fte，
  curl -L 实测 4.92s 完成，66561280 字节，SHA-256=a527daa2fe5cf8424f02d8d32e50836b0f1b8e9fcf29f24ae087182c2cbe3411
  与 LFS 指针 oid 完全一致），放入源码缓存后重建；test_e2e 真实 golden 对拍通过
  （doc0-3 cos≈0.9999997），上游全量通过率 **3/3 = 100%**；同时保留合成模型
  端到端验证（鸿蒙专项 + test_package 各 1/1，分别计数）。
- r01 验证记录（模型未获取时）：tarball 实测 model.fte=133B 指针；LFS 拉取
  60s/290s 仅 1.2~3.7MB/66MB（端点可达但极慢）；r02 网络恢复后 4.92s 完成。
- 适用范围：任何用 Git-LFS 托管模型/大数据资产、官方 tarball 不含实际文件的库；
  恢复条件=从 media.githubusercontent.com/media/<owner>/<repo>/<tag>/<file> 拉取
  并按 LFS 指针 oid 核验 SHA-256 后重跑测试。
- 查重：正式知识/图谱/草稿均无 Git-LFS 命中（E150 是 git submodule 类，不同机制）。

### 七轴查重结论（r02 复核；两候选均：未命中或部分覆盖 + 已验证 + 可跨库复用 → 路径 B）

| 轴 | 候选 1（native flag 门控） | 候选 2（LFS 模型资产） |
|---|---|---|
| exact_duplicate | 否（无同形态条目） | 否 |
| causal_duplicate | 部分（与 ascon-c 草稿同"native 标志"族，但机制不同，非同一因果链） | 否（E150 是 git submodule 机制，因果链不同） |
| trigger_overlap | 是（CMake + 交叉构建 + native 标志触发相似） | 部分（均为"tarball 不含运行时资产"类，机制不同） |
| solution_overlap | 部分（同为关闭 native 标志；ascon-c 用变量覆盖，本条用 option 门控） | 否（拉取 LFS 对象 + oid 核验 + 重建实跑的方案无既有条目覆盖） |
| combination_novelty | 是（check_c_compiler_flag 动态探测 + option 门控 + tc.variables 组合为新增形态） | 是（LFS 指针识别 → 官方端点拉取 → oid/SHA-256 核验 → 源码缓存恢复 → 重建实跑 → SKIP 转实跑通过 的完整处置链） |
| boundary_novelty | 是（精确边界：动态探测形态 vs cache 变量 vs 硬编码 flags） | 是（明确 LFS vs submodule vs 小资产随包分发；r02 补充恢复条件=media.githubusercontent.com/media/<owner>/<repo>/<tag>/<file>） |
| test_migration_novelty | 否 | 是（r01 SKIP 台账 → r02 获取模型后 test_e2e 实跑通过 3/3=100% 的迁移路径；双口径台账 + 合成模型端到端补充） |

### 路径决定（r02 复核更新）

- `new_draft`（路径 B，任务类型=知识库扩展）：两候选均满足"已验证、可跨库复用、
  查重未命中或部分覆盖且存在新增差异"，已建立同 stem 的 .kv/.md 草稿：
  - `knowledge/drafts/fasttextembed-1.0.2-cmake-native-cpu-flag-gate.kv/.md`（预留 E582）
  - `knowledge/drafts/fasttextembed-1.0.2-git-lfs-model-test-asset.kv/.md`（预留 E583；
    r02 将候选事实从"缺失 SKIP"更新为"获取 LFS 模型并实跑 e2e，3/3=100%"，
    草稿 .kv/.md 配对同步更新）
- 关系字段：候选 1 `similar_to=[DRAFT-ascon-c-1.3.0-cmake-rel-flags-combined-lib-naming]`；
  候选 2 `similar_to=[E150]`（机制不同，仅 trigger 相似）。草稿与 fasttextembed
  归档进入同一 PR（路径 B 知识草稿不入独立 PR）。
---

**编译结束**: 2026-09-22 21:30
**最终状态**: built
