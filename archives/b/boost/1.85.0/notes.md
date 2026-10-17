# Boost 1.85.0 编译笔记

## 底稿来源

以 `archives/b/boost/1.84.0/` 为底稿（依赖最简：仅 zlib/1.3.1），1.85.0 与 1.84.0 构建方式完全一致（b2 自举在 OHOS 不可用，手动 clang++ 编译）。

## 编译环境

- 构建系统: custom（手动 clang++ 编译，绕过 b2）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4（OHOS aarch64，musl libc）
- 平台: OpenHarmony PC (aarch64-linux-ohos)
- 状态: built

## 为什么不用 b2 / CMake

- **b2 构建系统（失败）**：Boost.Build 的 SHELL 执行机制在鸿蒙不兼容（`clang++ --version` 在 `tools/build/src/tools/common.jam` 的 match-command-output 失败），错误模式 E068/E099。1.84.0 底稿与历史归档（1.76.0/1.90.0 系列）均已实证。
- **CMake 构建（不适用）**：Boost 1.85.0 根目录无 CMakeLists.txt，官方 CMake 支持是 superproject 实验特性（1.90+ 才有官方 cmake tarball），无法独立构建。
- **方案（成功）**：与 1.84.0 相同——手动编译 4 个非 header-only 库（filesystem/regex/program_options/iostreams）为静态库，其余库 header-only 随 `boost/` 头文件目录整体安装。

## 编译步骤

1. `source()` 下载 boost_1_85_0.tar.gz（官方源 archives.boost.io，CI 自动 fallback 到 SourceForge），strip_root 解压
2. `build()` 应用 patches/0001（sp_thread_sleep.hpp 增加 BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性检测开关）
3. 以 `-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC -I<boost_root>` 逐库编译：
   - filesystem: 9 个 .cpp（跳过 windows_file_codecvt.cpp）
   - regex: 5 个 .cpp
   - program_options: 10 个 .cpp（跳过 winmain.cpp）
   - iostreams: 4 个 .cpp（file_descriptor/gzip/mapped_file/zlib，跳过 bzip2/lzma/zstd）
4. `llvm-ar rcs` 归档为 libboost_*.a
5. `package()` 复制完整 `boost/` 头文件目录 + libboost_*.a

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b2 无法构建 | Boost.Build SHELL 执行机制与 OHOS 不兼容（E068/E099） | 手动 clang++ 编译（沿用 1.84.0 方案） |
| 2 | sp_thread_sleep.hpp 引用 pthread_setcancelstate | OHOS musl 未实现该 API | patches/0001 + 编译宏 BOOST_SP_NO_PTHREAD_SETCANCELSTATE（R8：特性检测宏而非平台宏），并在 package_info 传播给所有下游 |
| 3 | 上游测试全部 rc=127（首跑 0/16） | 测试可执行文件动态链接 libc++_shared.so，该库不在 conan build 环境默认搜索路径（1.84.0 底稿当年在设备 shell 环境运行，未显式处理；干净环境暴露） | `clang++ -print-file-name=libc++_shared.so` 自省定位 SDK libc++ 目录，注入 LD_LIBRARY_PATH 后重跑；test_package 同步采用 VirtualRunEnv + LD_LIBRARY_PATH + OHOS 签名（对齐 1.90.0.2.1 先例） |

## 与 1.84.0 底稿的差异清单

| 项 | 1.84.0 | 1.85.0 |
|---|--------|--------|
| 源码 URL | boost_1_84_0.tar.gz | boost_1_85_0.tar.gz（sha256 实算 be0d9173...） |
| program_options 源文件 | `Convert.cpp`（大写 C） | `convert.cpp`（小写，1.85.0 重命名） |
| 0001 补丁 | 适用 | 仍适用（1.85.0 sp_thread_sleep.hpp 上下文未变，patch --dry-run 验证干净应用） |
| 构建方案 | 手动编译 4 库 | 完全一致 |
| 上游测试集 | 16 项 | 16 项（文件全部存在，路径未变） |
| 上游测试运行环境 | 未显式处理 libc++ 运行时（设备 shell 环境隐式可用） | LD_LIBRARY_PATH 注入 SDK libc++ 目录（clang++ -print-file-name 自省定位，CI 干净环境可复现） |
| test_package | cmake.test() + self.run 直接执行 | VirtualRunEnv + LD_LIBRARY_PATH + OHOS ELF 签名（对齐 1.90.0.2.1 先例） |

其余（cxxflags、components 定义、test_package）与 1.84.0 保持一致。

## 源码修改

- `patches/0001-ohos-pthread-cancel-fix.patch`：与 1.84.0 相同（boost/core/detail/sp_thread_sleep.hpp 三处 `#if defined(BOOST_HAS_PTHREADS) && !defined(__ANDROID__)` 增加 `&& !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)`）。1.85.0 该文件上下文与 1.84.0 一致，补丁无需修改。

## 依赖版本

- zlib/1.3.1（conan 制品仓，iostreams gzip 用）

## 验证结果

上游测试（手动编译各库 test/*.cpp 并真实运行，绕过 b2，16 项）：

```bash
# conan create 实测（2026-09-02，OHOS aarch64 clang 15.0.4）
# TOTAL 16: 15 passed / 1 failed
# FAIL 仅 libs/program_options/test/parsers_test.cpp rc=-11（段错误，
# 与 1.84.0 底稿完全一致的已知环境差异，非本版回归）
# 完整报告：conan build cache upstream-tests-report.txt
PASS libs/filesystem/test/copy_test.cpp (断言≈39) rc=0
PASS libs/filesystem/test/foreach_test.cpp rc=0
PASS libs/filesystem/test/large_file_support_test.cpp rc=0
PASS libs/filesystem/test/path_test.cpp (断言≈877) rc=0
PASS libs/filesystem/test/convenience_test.cpp (断言≈41) rc=0
PASS libs/regex/test/issue153.cpp (断言≈1) rc=0
PASS libs/regex/test/quick.cpp (断言≈10) rc=0
PASS libs/program_options/test/cmdline_test.cpp (断言≈43) rc=0
PASS libs/program_options/test/exception_test.cpp (断言≈24) rc=0
PASS libs/program_options/test/exception_txt_test.cpp (断言≈2) rc=0
PASS libs/program_options/test/optional_test.cpp (断言≈5) rc=0
PASS libs/program_options/test/options_description_test.cpp (断言≈40) rc=0
FAIL libs/program_options/test/parsers_test.cpp (断言≈61) rc=-11
PASS libs/program_options/test/positional_options_test.cpp (断言≈19) rc=0
PASS libs/program_options/test/quick.cpp (断言≈1) rc=0  # --path=initial
PASS libs/program_options/test/split_test.cpp (断言≈8) rc=0
```

test_package 实测输出（CMake find_package Boost COMPONENTS filesystem regex program_options iostreams，OHOS 签名后真实运行）：

```text
filesystem: path filename = "boost_test_dir"
regex: matched '1-85'
program_options: --name = boost185
iostreams: gzip round-trip OK (47 -> 63 bytes)
boost 1.85.0: filesystem + regex + program_options + iostreams OK
```

conan create 结果：`boost/1.85.0@ohpcd/stable: Package '32b74e3e19b062f993e717bc9d8150ae65c2c340' created`

## 注意事项

- b2 在 OHOS 不可用是长期已知问题（E068/E099）；后续如需更多编译库（thread/chrono/test 等），按本方案扩展 `_compile_lib` 源文件清单即可
- 远程分支 origin/feat/boost-1.85.0-23F9（Tianyi Wang，2026-07）是 b2 工具包（application 类型）方向的尝试，与本次 boost 库适配（static-library）范畴不同，未合并入 main；其 E099/E100 经验已吸收
---

**编译结束**: 2026-09-02 23:06
**最终状态**: built
