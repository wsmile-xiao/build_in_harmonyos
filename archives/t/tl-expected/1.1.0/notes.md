# tl-expected 1.1.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE library）
- 编译日期: 2026-09-01
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
# 1. 上游源码下载核验（codeload 可达）
curl -sL -o expected-v1.1.0.tar.gz \
  https://codeload.github.com/TartanLlama/expected/tar.gz/refs/tags/v1.1.0
sha256sum expected-v1.1.0.tar.gz   # 1db357f46dd2b24447156aaf970c4c40a793ef12a8a9c2ad9e096d9801368df6

# 2. 上游测试构建（Catch2 需本地源，避免 github.com 下载失败）
cmake -S <src> -B build -DEXPECTED_BUILD_TESTS=ON -DEXPECTED_BUILD_PACKAGE=OFF \
  -DCMAKE_CXX_STANDARD=17 -DFETCHCONTENT_SOURCE_DIR_CATCH2=<本地 Catch2-2.13.10>
cmake --build build -j2
ctest --output-on-failure   # 1/1 PASS（451 assertions / 36 test cases）

# 3. HarmonyOS 专项测试（test_package/test_tl_expected_ohos.cpp）
clang++ -std=c++17 -I <src>/include -Wall -Wextra -o tl-expected-ohos-test \
  archives/t/tl-expected/1.1.0/test_package/test_tl_expected_ohos.cpp
./tl-expected-ohos-test     # checks=17 ok=18 result=PASS

# 4. 消费者验证
cmake -S <consumer> -B build -DCMAKE_PREFIX_PATH=<prefix>   # find_package(tl-expected REQUIRED)
cmake --build build && ./build/consumer                     # value=15 ok=true, exit 0

# 5. Conan 配方
python3 scripts/ohc-run.py conan-verify tl-expected 1.1.0   # G1-G4 + L2/L4/L5 全通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 从 github.com 下载返回 HTML | github.com archive 路径不可达 | 用 codeload.github.com 手动下载并放置到 `$TMPDIR/builds/tl-expected-1.1.0.tar.gz` |
| 2 | 上游测试构建卡在 Catch2 FetchContent | github.com Catch2 v2.13.10 下载失败 | 手动下载 Catch2 到本地，`-DFETCHCONTENT_SOURCE_DIR_CATCH2=<本地>` |
| 3 | conan-verify G1 FAIL | 初始配方缺 `export_sources()` 与 `apply_conandata_patches` | 补全 conanfile.py 方法 |
| 4 | conan-verify G2 FAIL: CMakeToolchain 重复声明 + CMakeUserPresets.json 污染 | test_package 同时声明 generators 又在 generate() 实例化；preset 写回 source | E225: `generators=CMakeDeps` + generate() 内 `tc.user_presets_path=False` + `cmake_layout(build_folder="$TMP")` |
| 5 | W3 本地 CI JC 垃圾文件拦截（2 个） | 本分支尚未提交变更，`origin/main...HEAD` diff 为空 → junk_check 回退 full 整仓扫描，命中 main 基线其他库（goaccess tarball、scudo-malloc 隐藏文件） | 提交本库变更使 W3 走 incremental 模式只扫本库 diff；不修改其他库文件 |

## 源码修改

无（header-only 库，无补丁，patches/ 为空）。

## 依赖版本

- 无编译依赖
- 测试依赖：Catch2 v2.13.10（仅上游测试 FetchContent 用，本地提供）

## 验证结果

```bash
ctest --output-on-failure          # 1/1 tests passed（451 assertions in 36 test cases）
./tl-expected-ohos-test            # checks=17 ok=18 result=PASS
./build/consumer                   # consumer: value=15 ok=true, exit 0
python3 scripts/ohc-run.py conan-verify tl-expected 1.1.0   # 配方验证通过（可标 published）
```
---

**编译结束**: 2026-09-01 11:44
**最终状态**: built
