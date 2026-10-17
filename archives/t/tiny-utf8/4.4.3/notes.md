# tiny-utf8 4.4.3 适配笔记

## 编译环境
- 构建系统: cmake（header-only，上游 CMake INTERFACE target）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ 15（OHOS SDK，aarch64-linux-ohos）
- 状态: built（conan create 验证通过）

## 编译步骤

tiny-utf8 为纯头文件 C++11 库（include/tinyutf8/tinyutf8.h，5107 行），配方为 header-library 类型：

1. `ohc-run.py init-build tiny-utf8 4.4.3 --url=<官方 GitHub tag v4.4.3 tarball>` — 下载官方源码、核验 SHA-256、创建归档骨架
2. `ohc-run.py conan-init tiny-utf8 4.4.3` — 生成配方骨架后人工改写为 header-only CMake 配方：
   - `conandata.yml`: 官方 URL + 实测 sha256=8e3f6165...
   - `conanfile.py`: package_type=header-library，source() 用 get(strip_root)，package() 拷贝 include/tinyutf8/tinyutf8.h 与 LICENCE，cmake_file_name=tinyutf8 / cmake_target_name=tinyutf8::tinyutf8
3. `ohc-run.py conan-verify tiny-utf8 4.4.3` — G1-G4 + L2/L4/L5 全部通过
4. test_package: 消费者测试 test.cpp（构造/码点长度/迭代/子串/比较）+ HarmonyOS 专项 test_ohos.cpp（CJK/emoji/码点边界 U+10FFFF）
5. `conan create`（profile ohos-aarch64，绝对路径）— 2/2 测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 编译失败：`use of undeclared identifier 'tinyutf8'` | 库命名空间是 `tiny_utf8`（下划线），非 `tinyutf8` | 改用 `tiny_utf8::string`（basic_string<char32_t,char> 的 typedef） |
| 2 | 上游测试编译失败：`std::function` CTAD + `if constexpr` 报错、缺 `gmock/gmock.h` | GTest 1.17 头需要 C++17 特性；test/src/helpers 包含 gmock 头 | 用 `-std=c++17` 编译并链接 gmock；库本身仍仅要求 C++11 |
| 3 | 相对路径 profile 报 `settings.os.version value not defined` | 同名缓存 profile（ci/conan/profiles/ohos-aarch64）遮蔽了文件，缓存版本缺 os.version | profile 用绝对路径传入，加载仓库内的官方 profile（os.version=6.0） |

## 源码修改

无补丁。上游源码零修改（header-only，无平台相关代码）。

## 依赖版本

- gtest/gmock 1.17.0（仅测试期使用，官方 tag v1.17.0 本地构建）
- 库本身无运行时依赖

## 验证结果

```bash
# 上游测试（主机 clang，GTest 1.17）
tinyutf8_test  # 16/16 PASSED（--gtest_list_tests 枚举 16 个独立 TEST 宏）
# OHOS aarch64 工具链消费者验证
conan create archives/t/tiny-utf8/4.4.3 -pr:h=<abs>/ohos-aarch64 -pr:b=<abs>/ohos-aarch64
# CTest: 1/2 test_tiny-utf8 Passed, 2/2 test_tiny-utf8-ohos Passed, 100% passed
```

## 注意事项

- 上游 CMake 根 project 版本号写死为 4.0.2（README 与 tag 不一致的历史遗留），配方版本号以任务与 tag 为准：4.4.3
- 命名空间为 `tiny_utf8`（下划线），consumer 需注意
- `operator[]` 按码点索引返回 char32_t，`length()` 返回码点个数、`size()` 返回字节数
---

**编译结束**: 2026-09-06 01:02
**最终状态**: built
