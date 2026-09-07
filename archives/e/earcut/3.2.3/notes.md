# earcut 3.2.3 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，无实际编译产物）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (aarch64-linux-ohos) / clang++
- 状态: built

## 编译步骤

```bash
# 源码（官方 tag v3.2.3，本地经 ghfast.top 镜像拉取并核对 SHA-256）
#   https://github.com/mapbox/earcut.hpp/archive/refs/tags/v3.2.3.tar.gz
#   sha256 = e40bac21c47fc8bb56779a1754e16b3cb692e03ff8dd1c4c87ac9c5113a22f72
# 配方: conanfile.py (package_type=header-library, CMakeToolchain, EARCUT_BUILD_TESTS/BENCH/VIZ=OFF)
# 补丁: patches/0001-guard-fixtures-fetchcontent.patch（fixtures FetchContent 门控到构建选项）
conan create archives/e/earcut/3.2.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 上游测试（离线复现，本地绑定 FetchContent 依赖）
cmake -DEARCUT_BUILD_TESTS=ON -DEARCUT_BUILD_BENCH=OFF -DEARCUT_BUILD_VIZ=OFF \
  -DFETCHCONTENT_SOURCE_DIR_EARCUT_JS=<本地 earcut.js v3.2.3> \
  -DFETCHCONTENT_SOURCE_DIR_PICOJSON=<本地 picojson v1.3.0> \
  -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=<本地 googletest v1.15.2> && ninja tests && ./tests
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-verify G2 configure 失败: `CMake step for earcut_js failed: 1`（GIT_VERSION_STRING=''） | 上游 CMakeLists 顶层无条件 FetchContent_MakeAvailable(earcut_js/picojson)，未挂在构建选项 if 块内；本机无 GitHub 直连 | patches/0001-guard-fixtures-fetchcontent.patch：把 fixtures + 两个 FetchContent 块包进 `if (EARCUT_BUILD_TESTS OR EARCUT_BUILD_BENCH OR EARCUT_BUILD_VIZ)`，纯 header 打包离线可过；上游测试用 FETCHCONTENT_SOURCE_DIR_* 本地绑定离线复现 → 新建 E345 草稿 |
| 2 | test_package/测试源编译失败: `no matching function for call to 'earcut'` | earcut.hpp v3.2.3 API 现代化：`earcut(poly)` 单参直接返回 std::vector<N>（旧 2.x 双参 `earcut(indices, poly)`） | 改用新 API：`auto indices = mapbox::earcut<uint32_t>(poly);`（K2，库特定 L3 笔记，不建草稿） |
| 3 | conan-init 生成 autotools 模板 | 构建系统探测把无 configure 的 CMake header-only 库误判为 autotools | 手工重写 conanfile.py 为 header-library + CMakeToolchain（配方模式复用 E322，不建新草稿） |
| 4 | finish W3 JC 全仓扫描误报其他库 junk | JC 在 `git diff origin/main...HEAD` 为空时回退 full 模式（ls-files 全仓扫描），命中 main 基线中其他库历史脏文件 | 先把本库变更提交到 feat 分支，使 JC 进入 incremental 模式只检查本库新增 11 文件 |

## 源码修改

- `patches/0001-guard-fixtures-fetchcontent.patch`：CMakeLists.txt fixtures FetchContent 门控
  （详见 0001-guard-fixtures-fetchcontent.patch，`patch -p1` 可独立验证）

## 依赖版本

- 无第三方运行时依赖（header-only，std-only）
- 测试依赖（本地绑定，仅测试构建用）: earcut.js v3.2.3 / picojson v1.3.0 / googletest v1.15.2

## 验证结果

```bash
# conan-verify: G0-G4/L2/L4/L5 全部 PASS（conan create 成功，test_package 两个可执行测试实际运行通过）
# 上游测试: 69/69 PASSED（10 TEST + 59 fixture 参数），退出码 0
# 上游测试统计（双口径）:
#   source_declared_total = 11（10 TEST + 1 TEST_P 套件，59 fixture 参数 -> 69 注册）
#   configured_executable_total = 69；executed_passed_total = 69；failed = 0；未运行 = 0
#   全量通过率 69/69 = 100%（69/69 当前配置可执行集合）
# 鸿蒙专项测试: test_earcut（消费者冒烟 8 三角形/面积守恒）+ test_earcut_ohos（3 用例）全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（R32/R34/R39 合规） |
| conandata.yml | 官方 URL + sha256（e40bac21...） |
| patches/0001-guard-fixtures-fetchcontent.patch | fixtures FetchContent 门控补丁 |
| test_package/ | 消费者冒烟 + HarmonyOS 专项测试（真实调用 API） |
| reports/test-report.md | 全量测试报告（双口径统计） |
| reports/knowledge-candidate-ledger.md | 知识候选台账 + 七轴查重 + 路径决定 |
| knowledge/drafts/E345-draft-7657.kv/.md | 路径 B 知识草稿（无条件 FetchContent 门控） |

## 注意事项

- v3.2.3 API 与 2.x 不兼容（K2）：消费者必须用 `earcut(poly)` 返回 indices 的新形式，
  可选 `mapbox::refine(triangles, coords)` Delaunay 后处理
- 上游测试默认运行时读取 earcut.js fixtures JSON，需要网络/FetchContent；本地跑需
  FETCHCONTENT_SOURCE_DIR_* 绑定（见 E345 草稿）
- 本任务未获远端交付授权（remote_authorization=none, delivery_approval_required=true），
  交付预览待分析端批准

## 发现与知识（knowledge_candidate_ledger 摘要）

- ✅ K1（new_draft → E345）：上游无条件 FetchContent 离线门控补丁 + FETCHCONTENT_SOURCE_DIR_* 本地绑定，跨库可复用（knowledge_ref: knowledge/drafts/E345-draft-7657.kv）
- ✅ K2（path_a_no_knowledge）：earcut.hpp v3.2.3 API 现代化（本库 L3 笔记，无跨库知识价值）
- ✅ K3（reuse_existing → E322）：header-only CMake INTERFACE 配方模式，复用既有条目 E322（knowledge_ref: knowledge/graph/E322.kv）

---

**编译结束**: 2026-09-05 04:17
**最终状态**: built