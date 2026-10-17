# lwjson 1.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify 通过后更新为 published）

## 编译步骤

lwjson 为纯 C 的轻量 JSON 解析/序列化库（MaJerle），CMake 构建，产出静态库
`lwjson`（核心）与 `lwjson_debug`（调试模块），公开头文件在
`lwjson/src/include/lwjson/`。上游无 install() 规则。

1. 源码核验：官方 tag v1.9.0 归档（github archive 与 codeload 双路径下载，
   SHA-256 均 = fd1aae664f5fac34e6e57e67e21c421a2bb6559046e81323e1a69c3b5ba7af50）
2. 语言预检 (R47)：detected=c（17/20 C 源文件，85%），task=cpp 兼容族，通过
3. 本地验证构建：
   ```bash
   cmake -S . -B __build__ -DCMAKE_BUILD_TYPE=Release
   cmake --build __build__ -j2
   ctest --test-dir __build__/tests --output-on-failure   # 1/1 Passed
   ```
4. 上游测试全量枚举（tests/test.py 驱动的 6 个独立入口，逐项配置+构建+运行）：
   6/6 全部通过（见"上游测试台账"节）
5. 补丁：`patches/0001-lwjson-library.cmake.patch` 在 `lwjson/library.cmake`
   末尾追加 install 规则（install TARGETS lwjson lwjson_debug + 头文件目录 +
   构建期生成的 lwjson_opts.h）
6. Conan 配方：CMakeToolchain + CMake + cmake_layout；build() 内跑默认 ctest
   入口（L1）；package() 用 cmake.install()
7. 消费者用例：test_package/test.c（真实 API：lwjson_parse/find/类型值/数组
   遍历）+ test_ohos.c（鸿蒙专项：UTF-8 中文/emoji 往返、令牌预算守恒、
   深层嵌套遍历）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 install() 规则，conan create 后无产物 | lwjson/library.cmake 只注册 target 不安装 | 最小补丁追加 install(TARGETS/DIRECTORY/FILES) 规则 |
| 2 | 消费者编译缺 lwjson_opts.h | lwjson_opt.h `#include "lwjson_opts.h"`，该文件由构建期 configure_file COPYONLY 生成（默认模板） | install(FILES <build>/lib_inc/lwjson_opts.h) 一并安装默认配置 |
| 3 | 顶层 ctest 报 "No tests were found" | 上游 add_test 在 tests/CMakeLists.txt，CTestTestfile.cmake 只生成在 <build>/tests 子目录 | ctest --test-dir 指向 <build>/tests |
| 4 | 直连 github.com 下载超时 | 网络环境 github 直连不可达 | 经 gh-proxy.com 镜像下载（conandata 仍保留官方 URL，CI 预下载自动加镜像） |

## 源码修改

- `lwjson/library.cmake`：追加 install 规则（补丁 0001-lwjson-library.cmake.patch，
  无平台宏，纯打包 portability 变更）

## 依赖版本

- 无第三方运行时依赖（纯 C 标准库）

## 上游测试台账（R51 全量枚举）

| 入口 | 源文件 | 分类 | 独立用例? | 运行结果 |
|------|--------|------|-----------|----------|
| test_stream | tests/test_stream/test_stream.c | 用户测试源 | 是（独立 CMake 入口） | 通过（默认 CTest 注册入口） |
| test_json_parse_basic | tests/test_json_parse_basic/test_json_parse_basic.c | 用户测试源 | 是 | 通过 |
| test_json_find | tests/test_json_find/test_json_find.c | 用户测试源 | 是 | 通过 |
| test_json_data_types | tests/test_json_data_types/test_json_data_types.c | 用户测试源 | 是 | 通过 |
| test_parse_token_count | tests/test_parse_token_count/test_parse_token_count.c | 用户测试源 | 是 | 通过 |
| test_serializer | tests/test_serializer/test_serializer.c | 用户测试源 | 是 | 通过 |
| test_main.c | tests/test_main.c | 测试主程序（test_run 入口） | 否（被各入口复用） | 参与各入口构建 |
| test.h | tests/test.h | 测试断言宏头 | 否（框架头） | - |
| tests/json/*.json | 4 个 fixture | 测试数据 fixture | 否（数据） | - |
| test.py | tests/test.py | 上游测试驱动脚本 | 否（脚本，非独立用例） | 本地逐项复现其动作 |

统计口径：
- source_declared_total = 6（独立上游用户测试入口）
- configured_executable_total = 6（逐项 CMake 配置构建为 6 个独立可执行程序）
- executed_passed_total = 6（6/6 全通过）
- 全量通过率 = 6/6 = 100%（6/6=100% 实际执行通过率同值）

## 验证结果

```bash
# 默认 CTest 入口
ctest --test-dir __build__/tests --output-on-failure   # 1/1 Passed
# 6 个上游入口逐一
for d in tests/test_*; do cmake -S . -B b -DTEST_CMAKE_FILE_NAME=$d/cmake.cmake \
  && cmake --build b -j2 && ctest --test-dir b/tests; done  # 6/6 Passed
# install 规则验证
cmake --install __build__ --prefix $TEST_PREFIX   # liblwjson.a + 头文件 + lwjson_opts.h
```

## 注意事项

- conandata.yml 注释中不含任何 https:// URL（CI pre-download 会将其误提取为
  源码 URL 并做 file:// 替换，腐蚀真实 URL）
- lwjson 非 CLI 库（无可执行产物，纯库），无需 commands.json
- 系统无同名库冲突（非 system 同名），默认静态链接

### 对话 #1 (2026-10-04 R01)

- 问题 1: 上游无 install() 规则 → 补丁 0001-lwjson-library.cmake.patch 追加
  install(TARGETS/DIRECTORY/FILES)（含构建期生成的 lwjson_opts.h）
- 问题 2: test_package ctest 报 SegFault → 根因是 assert() 内含副作用调用
  （lwjson_init/parse），-DNDEBUG（CI Release）下整个调用被删除导致未初始化
  段错误；修复：副作用调用移出 assert（知识候选 3）
- 问题 3: 本地 W3 JC6 报 107 个软件包 → 本地 main 与 origin/main 分叉（214 个
  local-only commits），改用 pr.diff 模式（真实 CI 同款）模拟 PR 文件清单后通过；
  PR 基线从 origin/main 重建保证远端 PR diff 干净
- 结论: 上游测试 6/6、消费者+鸿蒙专项 2/2、conan-verify G0-G4+L2/L4/L5 全通过、
  W3 本地 CI 模拟通过

## 结束

最终状态: built（conan-verify 通过、W3 本地 CI 模拟通过；CI 发布后升级 published）

## 知识候选台账（路径 B 查重）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 四范围查重 | 决定 |
|---|------|---------|------|------|------|----------|-----------|------|
| K1 | CMake 库零 install 规则 | conan create 后无产物/消费者缺头 | library.cmake 只 add_library 不 install；生成配置头漏装 | 最小补丁 install(TARGETS/DIRECTORY/FILES)+生成头 | conan-verify G2-G4 通过、消费者编译运行 OK | 零 install 规则 CMake C 库 | 官方库未命中；草稿 DRAFT-21002（对 E309/E217 部分覆盖） | new_draft |
| K2 | ctest "No tests were found" 假通过 | 顶层 ctest 0 测试 | add_test 在 tests/ 子目录，顶层无 CTestTestfile | ctest --test-dir <build>/tests | 1/1 Passed（本地+conan build） | 子目录 add_test 的 CMake 工程 | 官方库未命中（E292/E294 不同主题） | new_draft |
| K3 | assert 副作用 + NDEBUG 段错误 | test_package SegFault | -DNDEBUG 删除 assert(init/parse) 调用 | 副作用调用移出 assert | 修复后 Release 下 2/2 Passed | 任何 C/C++ Release 测试 | 官方 E259 完全命中 | reuse_existing（E259） |
| K4 | conandata 注释 URL 被 pre-download 提取替换 | conan create 失败（file:// 腐蚀） | 正则不识别注释行 | 注释禁 https:// URL | 规避后 create 全绿（libfixmath64 先例） | 所有 conandata 配方 | 官方 E333 相邻（trigger_overlap）；草稿 DRAFT-21004 | new_draft |
| K5 | 分叉 main 致 W3 JC6 误拦 107 包 | 本地 W3 w3_local_ci_failed | 本地 main 与 origin/main 分叉，三点 diff 被污染 | pr.diff 模式 + 从 origin/main 重建分支 | W3 prdiff 模式通过、远端 diff 干净 | 多执行器共享主机新分支 | 草稿 DRAFT-boost-te 部分覆盖；草稿 DRAFT-21005 | new_draft |

- exact_duplicate: K3（E259）；causal_duplicate: 无；trigger_overlap: K4（E333）、K5（DRAFT-boost-te）
- solution_overlap: K1（E309/E217）、K4（E333）、K5（DRAFT-boost-te）
- combination_novelty: K1/K2/K4/K5 均有（见各草稿）
- boundary_novelty: 各草稿含适用边界/反例
- test_migration_novelty: K2（R51 台账衔接）、K1（R34 消费者验证落地）
- similar_to: E309/E217（K1）、E292/E294（K2）、E333（K4）、DRAFT-boost-te（K5）
- caused_by / prerequisite_of / conflicts_with: 无冲突

路径决定: **path_b_new_draft**（任务类型=知识库扩展；K1/K2/K4/K5 新建
DRAFT-21002/21003/21004/21005 四组 .kv/.md 草稿，与 lwjson 归档同 PR；
K3 复用 E259）
---

**编译结束**: 2026-10-04 20:07
**最终状态**: published
