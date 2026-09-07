# graaf 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only, C++20)
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++ (OHOS aarch64, libcxx-ohos)
- 状态: built（本地 W3 conan create + test_package 通过；未发布）

## 编译步骤

1. init-build 获取官方源码：`https://github.com/bobluppes/graaf` tag `v1.1.0`
   （tarball SHA-256 `e6bdd6ee...`，与 conandata.yml 一致）。
2. lang-preflight：detected=cpp，通过（R47）。
3. 上游测试本地构建：
   ```bash
   cmake -S . -B build -DCMAKE_CXX_STANDARD=20 -DSKIP_EXAMPLES=ON \
     -DSKIP_BENCHMARKS=ON \
     -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=.../googletest-release-1.12.1 \
     -DFETCHCONTENT_SOURCE_DIR_FMT=.../fmt-9.1.0
   cmake --build build -j2 --target Graaf_test
   ./build/test/Graaf_test
   ```
   结果：750/750 通过（746 上游 + 4 鸿蒙专项 OHOSAdaptation）。
4. conanfile.py + conandata.yml + test_package + MANIFEST.yml 编写完成。
5. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` 通过，
   test_package 消费者验证 OK（BFS=4, MST=3, K4 coloring proper）。
6. finish（W2/W3）通过：L0e MANIFEST 补全、JC prdiff 模式 pass（6 个 JC5 命中
   均为 main 中其他库已跟踪隐藏文件的基线噪声，非本库 diff 内容）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `no member named 'max_element' in namespace 'std::ranges'`（bron_kerbosch.tpp/prim.tpp/vertex_properties.tpp 共 3 处） | OHOS libc++（libcxx-ohos, llvm15）未实现 C++20 std::ranges 算法层 | 等价替换为 std::max_element/min_element/count_if + begin()/end()，带 projection 的改写为显式比较 lambda |
| 2 | `WelshPowellTest/0.CompleteGraph` 失败：K4 着色 (0,1),(1,1),(2,1),(3,0) 相邻同色 | 上游贪心着色依赖 unordered_set 邻居迭代顺序，OHOS libc++ 迭代顺序不同导致 | 改为收集已用色集合 + while 取最小未用色（确定性，与迭代顺序无关） |
| 3 | `ld.lld: duplicate symbol: detail::do_get_intersection/set_union/set_difference` | bron_kerbosch.tpp 中非模板自由函数无 inline，多翻译单元包含触发 ODR | 三个函数加 inline |
| 4 | test_package 编译报 C++20 `requires` 语法错误 | test_package CMakeLists 未声明 C++20 | CMakeLists 加 `set(CMAKE_CXX_STANDARD 20)` |
| 5 | `CMakeToolchain declared in generators but instantiated in generate()` | test_package conanfile 重复声明 | generators 只留 CMakeDeps，Toolchain 在 generate() 单次实例化 |
| 6 | W3 本地 CI 模拟 JC5 整仓扫描命中 6 个其他库隐藏文件 | main 中已跟踪的 captagent/flatcv/lsof/scudo-malloc/stb_image 等基线噪声；本地分支无提交时 fallback 到 full 模式 | 生成 pr.diff（仅本库 14 文件）使 W3 走 prdiff 模式（与 CI 真实口径一致），JC pass |

## 源码修改

4 个补丁（patches/）：
- 0001: bron_kerbosch.tpp — std::ranges::max_element → std::max_element + inline 三个 detail 自由函数
- 0002: welsh_powell.tpp — 确定性最小未用色分配
- 0003: prim.tpp — std::ranges::min_element → std::min_element
- 0004: vertex_properties.tpp — std::ranges::count_if → std::count_if

## 依赖版本

- googletest 1.12.1（上游测试，本地构建用）
- fmt 9.1.0（上游测试，本地构建用）
- 库本体零依赖（header-only C++20）

## 验证结果

```bash
./build/test/Graaf_test
# [==========] 750 tests from 210 test suites ran.
# [  PASSED  ] 750 tests.
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# test_package OK (BFS=4, MST=3, K4 coloring proper)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only Conan 2.x 配方（package_type=header-library） |
| conandata.yml | 官方源 + SHA-256 + 4 补丁声明 |
| test_package/ | 消费者验证（CMakeLists/conanfile/test_package.cpp/MANIFEST.yml） |
| patches/ | 4 个 OHOS 移植性补丁 |

## 注意事项

- graaf 上游 CMakeLists 无 install 规则，packaging 通过复制 include/（.h + .tpp）完成。
- 知识路径：知识库扩展（路径 B），新增 3 条 .md/.kv 草稿配对，覆盖
  std::ranges 缺失替换 / 贪心着色确定性 / header-only .tpp ODR 三方面。
- 交付需远端授权：remote_authorization=none 且 delivery_approval_required=true，
  本地门禁全部通过后仅生成 delivery_preview，等待分析端用户批准后再 commit/push/PR。