# simpleini 4.26 适配笔记

## 编译环境
- 构建系统: cmake（CMake INTERFACE header-only target）
- 编译日期: 2026-09-02
- 编译器: clang/clang++（OHOS SDK 15，target aarch64-linux-ohos）
- 状态: built

## 编译步骤

simpleini 是单头文件（SimpleIni.h）header-only 库，无二进制编译。

1. 上游测试构建（OHOS 主机本机运行）：
   ```bash
   cmake -S . -B build-ohos -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
     -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DBUILD_TESTING=ON
   cmake --build build-ohos -j4
   ctest --output-on-failure
   ```
   结果：253 tests / 250 passed / 3 skipped / 0 failed。

2. Conan 配方（header-only）：`conan-init` → 改写 conanfile.py 为
   `package_type=header-library` + CMakeToolchain，`BUILD_TESTING=OFF`；
   conan-verify G0-G4/L2/L4/L5 全部 PASS。

3. `finish`（状态 built）：conan-verify + W3 本地 CI 模拟 + test_package 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 `LoadFileRegression.LoadsFromFilePointer` 失败 | OHOS `/tmp` 只读（E002），`tmpfile()` 硬编码 `/tmp` 返回 NULL(errno 13) | 改测试用 `mkstemp()` 于当前可写目录，生成补丁 0001-tests-ts-iostream.cpp.patch |
| 2 | init-build 下载仓库主页报"下载内容是 HTML" | 传入 `--url` 是仓库主页而非 tarball | 改传官方 `.../archive/refs/tags/v4.26.tar.gz` |
| 3 | finish W3 JC 门禁 fail（Junk Files: 3） | JC full 模式整仓扫描命中 main 基线中其他库的历史已跟踪 junk（flatcv/goaccess/lsof/scudo-malloc/stb_image） | 按知识库 DRAFT-jc-full-mode-git-index-isolation 做索引级临时隔离（git rm --cached），W3 通过后恢复 |

## 源码修改

- `patches/0001-tests-ts-iostream.cpp.patch`：`LoadsFromFilePointer` 测试改用
  `mkstemp()`，避免 OHOS `/tmp` 只读导致的 `tmpfile()` 失败（平台专属）。

## 依赖版本

- 无第三方运行时依赖（header-only）。
- 测试依赖 GoogleTest v1.14.0（FetchContent，仅上游测试构建，不进配方）。

## 验证结果

```bash
ctest --output-on-failure        # 253 tests: 250 passed / 3 skipped / 0 failed
conan-verify simpleini 4.26      # G0-G4/L2/L4/L5 全部 PASS
finish simpleini 4.26 built      # W2 结构/R36 依赖/W3 编译/test_package PASS
```

## 交付物

- conanfile.py（header-only 配方）
- conandata.yml（官方源 v4.26 + sha256）
- test_package/（消费者测试 test.cpp 实质调用 SimpleIni API）
- patches/0001-tests-ts-iostream.cpp.patch

## 注意事项

- header-only 库 `package_type=header-library`，`cpp_info.libs` 清空。
- `generate()` 必须设 `BUILD_TESTING=OFF`，否则 conan create 会尝试 FetchContent gtest。
- OHOS `/tmp` 只读，凡涉及临时文件一律用 `$TMPDIR`/当前目录。
---

**编译结束**: 2026-09-02 00:31
**最终状态**: built
