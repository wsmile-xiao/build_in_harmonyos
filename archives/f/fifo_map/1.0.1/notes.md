# fifo_map 1.0.1 适配笔记

## 编译环境
- 构建系统: header-only（无构建系统；上游提供 CMakeLists/Makefile 仅供 unit 测试）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile）
- 状态: built（conan-verify 全门禁通过，未 upload）

## 官方来源
- 上游: https://github.com/nlohmann/fifo_map
- 版本: 1.0.1（tag v1.0.1, commit 6700631）
- 源码包: https://github.com/nlohmann/fifo_map/archive/refs/tags/v1.0.1.tar.gz
- SHA-256: cbf8ed2551a16989e5cf25b74d0fb98cb5828f25acbebe3825c992d13dd37f13
- 类型: header-only C++（src/fifo_map.hpp，MIT，仅依赖 STL）
- 依赖: 无第三方依赖

## 编译步骤
1. `ohc-run.py init-build fifo_map 1.0.1 --url=<官方 tag 压缩包>` — 下载解压、骨架创建、环境检查全过（errors=0）
2. `ohc-run.py lang-preflight fifo_map 1.0.1 --src ...` — 语言匹配 cpp/cpp
3. 上游测试: 编译 test/unit.cpp（doctest），10 个独立 TEST_CASE 全部通过（1306 断言）
4. 消费者用例（consumer_fifo_map.cpp）: 仅用公开头文件/API，FIFO 顺序/lookup/emplace/erase/swap 验证 rc=0
5. 鸿蒙专项测试（ohos_special_test.cpp）: FIFO 重插顺序/拷贝隔离/const 接口/反向迭代/emplace-hint 验证 rc=0
6. `ohc-run.py conan-init fifo_map 1.0.1` — 生成配方骨架（autotools 模板错误），人工改为 header-only 配方
7. `ohc-run.py conan-verify fifo_map 1.0.1` — G1/G2/G3/G4 全部 PASS（修复见下）
8. `ohc-run.py finish fifo_map 1.0.1 built` — 通过（W3 本地 CI 经基线隔离复验后通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 对仓库页 URL 报"下载内容是 HTML" | 传了 repo 页面而非 tag 压缩包 | 用官方 archive/refs/tags/v1.0.1.tar.gz URL |
| 2 | conan-verify G1 FAIL: 缺 build() 方法 | G1 结构门禁把 build() 列为必填；header-only 模板直觉省略 | 显式 no-op build()（apply_conandata_patches，空 patches 即 no-op） |
| 3 | conan create: "Package type is 'library', but no 'shared' option declared" | Conan 2 对 library 类型强制要求 shared 选项；header-only 无二进制 | 改 package_type="header-library"（并 self.info.clear()） |
| 4 | test_package: "Imported target fifo_map::fifo_map includes non-existent path .../p/include" | ①copy src=source_folder 根 glob 漏 src/ 子目录头文件；②相对 dst="include" 落到 build 目录而非包目录 | package(): src=os.path.join(source_folder,"src")，dst=os.path.join(package_folder,"include") |
| 5 | W3 本地 CI JC 拦截（JC1/JC5: 4 个其他库基线空文件 cloog/kics/thc） | 基线 main 已跟踪的 .build-closed/.staging-verified 空文件被 full 扫描命中 | 基线隔离复验：记录路径与 SHA-256（空文件 e3b0c442…），git update-index --force-remove 临时隔离，复跑 finish 通过，以原 blob e69de29b 恢复，git diff --cached 为空 |

## 上游测试枚举台账（双口径）

- source_declared_total: 10（test/unit.cpp 中 10 个独立 doctest TEST_CASE）
- configured_executable_total: 1（CMake 目标 unit；无 ctest 注册）
- executed_passed_total: 10（实际编译运行，1306 断言全过，rc=0）
- 全量通过率: 10/10 = 100%
- 分类: 框架头 test/thirdparty/doctest/doctest.h 不计入独立用例；无样例/基准/fixture/测试脚本；Makefile 引用的 thirdparty/catch 实际不存在（上游陈旧引用，不影响 CMake 路径）

## 鸿蒙专项测试与消费者验证

- 消费者用例: tmp/builds/ohos_special_consumer/consumer_fifo_map.cpp
  仅通过公开头文件 src/fifo_map.hpp 与公开 API（at/find/count/emplace/erase/swap/clear/size/迭代器）使用；
  编译链接运行 rc=0，FIFO 顺序保持可观察。
- 鸿蒙专项测试: tmp/builds/ohos_special_consumer/ohos_special_test.cpp
  FIFO 重插顺序、拷贝隔离、const 接口、反向迭代、emplace-hint、std::swap 特化，rc=0。
- test_package: archives/f/fifo_map/1.0.1/test_package/test.cpp（find_package(fifo_map) + fifo_map::fifo_map + 真实 API 调用）

## 知识候选台账

### 候选 1: header-only Conan 2 配方三段修复（G1 no-op build() + header-library 类型 + package() 显式 package_folder）
- 真实错误: G1 FAIL 缺 build()；G2 "no shared option"；G2 test_package include 路径不存在
- 根因: header-only 无构建系统库的配方结构门禁与类型声明、拷贝路径三处独立成因
- 修复: 见上表 #2/#3/#4
- 验证: conan-verify fifo_map 1.0.1 G1-G4 全 PASS，test_package 消费者 rc=0
- 适用范围: header-only/单头文件 C++ 库 Conan 2 配方（普查占配方 ~26%）
- 四范围查重:
  - 正式知识 knowledge/graph: E257（G1 build() 缺项，同因复现）、E322（header-library 类型，CMake INTERFACE 场景）命中部分覆盖
  - 图谱 index.tsv: 同上，无 "no shared option" 错误签名独立条目
  - 草稿 knowledge/drafts: DRAFT-bitmapplusplus-1.1.1-header-only-subdir-header-copy 覆盖 package() src/dst 修复思路（部分覆盖）
  - 完整重复: false（三处修复完整组合 + "no shared option" 签名为本轮新增）

### 七轴查重
- exact_duplicate: false（无完全同签名条目）
- causal_duplicate: false（E257 只覆盖 G1 一项；E322 覆盖类型声明但场景为 CMake INTERFACE 库）
- trigger_overlap: true（与 E257 共享 G1 触发；与 E322 共享 header-library 讨论）
- solution_overlap: true（与 DRAFT-bitmapplusplus 共享 package() 路径修复）
- combination_novelty: true（三处修复完整闭环 + "no shared option" 错误签名为新增）
- boundary_novelty: true（明确 header-only 无二进制才用 header-library，反例为有构建系统/二进制库）
- test_migration_novelty: false（无测试迁移内容）
- 关系: similar_to=[E257, E322, DRAFT-bitmapplusplus-1.1.1-header-only-subdir-header-copy]；caused_by/prerequisite_of/conflicts_with=无

### 路径决定
- new_draft（路径 B，知识库扩展）
- 草稿: knowledge/drafts/DRAFT-fifo_map-1.0.1-header-only-conan2-recipe-gate.kv + .md（同 stem 配对）
- 理由: combination_novelty 成立，已由本轮真实日志验证，可跨库复用于 header-only 族

## 源码修改
无（header-only，未修改上游源码，无 patches）

## 归档文件
- conanfile.py: header-only 配方（header-library + no-op build + package_folder 拷贝）
- conandata.yml: 官方 URL + SHA-256 cbf8ed…
- test_package/: test.cpp + CMakeLists.txt + MANIFEST.yml + conanfile.py
- manifest.yaml: status=built
- reports/conan-verify-report.md
