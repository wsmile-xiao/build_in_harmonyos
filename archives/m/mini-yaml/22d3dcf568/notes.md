# mini-yaml 22d3dcf568 适配笔记

## 编译环境
- 构建系统: custom（上游为裸 makefile 测试构建，无 configure/CMake；库本体仅 yaml/Yaml.cpp + yaml/Yaml.hpp 两文件）
- 编译日期: 2026-09-28
- 编译器: clang/clang++（OHOS PC 真机，HongMeng Kernel 1.12.0 aarch64）
- 状态: built

## 编译步骤

库本体为两文件 C++11 库，无需 configure。Conan 配方内直接编译：

```bash
clang++ -std=c++11 -fPIC -Iyaml -c yaml/Yaml.cpp -o Yaml.o
llvm-ar rcs libmini-yaml.a Yaml.o
```

上游测试（test/test.cpp，13 个 gtest 用例，依赖 googletest 子模块）使用制品仓 gtest/1.17.0.2 编译运行：

```bash
clang++ -std=c++17 -I<gtest include> -Iyaml -c test/test.cpp
clang++ -o test test.o Yaml.o libgtest_main.a libgtest.a -lpthread
cd test && ./test   # 13/13 PASSED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 直接以仓库页 URL 下载返回 HTML | GitHub 仓库页不是 tarball | 改用 `archive/<full-sha>.tar.gz` 官方归档 URL |
| 2 | init-build F068 嵌套提升误将 test/ 当源码根，删除 yaml/ 库源码 | 仓库根无构建标记，test/ 含 makefile 被误判 | 手工按 tarball 真实结构重建 .orig/.work，保留 yaml/ 库源码 |
| 3 | 上游测试依赖 googletest 子模块（tarball 内为空） | 子模块内容不入归档包 | 用 ohpcd 制品仓 gtest/1.17.0.2 编译运行上游测试 |
| 4 | finish refresh-patch 自动生成伪补丁 0001-test-test_learnyaml.yaml.patch | 上游 Serialize 测试运行时写出 test_learnyaml.yaml 产物，被 per-file-difflib 误收 | 删除伪补丁；mini-yaml 无需任何源码补丁 |

## 源码修改

无（零补丁适配）。库本体两文件原样编译，无需平台宏或源码改动。

## 依赖版本

- gtest/1.17.0.2（仅测试用，制品仓 ohpcd）

## 验证结果

```bash
# 上游测试：13/13 PASSED（5 个 suite）
[  PASSED  ] 13 tests.
# HarmonyOS 专项测试（调用 Yaml::Parse/As/Serialize，9 项断言）：9/9 PASSED，exit 0
=== harmonyos_specific_test summary: 9 check(s), 0 failure(s) ===
```

## 注意事项

- 版本标识 22d3dcf568 为上游 commit（仓库无正式 tag/release），已核验官方源 commit 存在。
- conan-verify 全门禁通过（G1-G4 + L2/L4/L5），可标记 published。
---

**编译结束**: 2026-09-28 17:25
**最终状态**: built
