# sljit 0.0-git20260924.b706c11 适配笔记

## 编译环境
- 构建系统: makefile（上游 GNUmakefile，无 configure）
- 上游提交: b706c11ca471c3da773ee595164acb6efd2c5574（2026-09-24）
- 编译日期: 2026-09-29
- 编译器: clang / clang++
- 状态: built（待真机预检回填实测数字）

## 编译步骤

```bash
# 源码包（官方 GitHub 归档，镜像优先、官方回退）
#   https://github.com/zherczeg/sljit/archive/b706c11ca471c3da773ee595164acb6efd2c5574.tar.gz
#   sha256 = fe9e38173aaab65e509babf96ef9b904cde75b6ae628018690f4c89e312920a5

# 配方内步骤（Conan 编译器经 make 命令行注入）
clang -O2 -fPIC -Wall -Isljit_src -c sljit_src/sljitLir.c -o sljitLir.o
llvm-ar rcs libsljit.a sljitLir.o
llvm-ranlib libsljit.a
# shared=True 时另行链接 libsljit.so
make -j1 CC="<Conan compiler>" CFLAGS="-O2 -fPIC -Wall"   # 构建 bin/sljit_test + bin/regex_test
./bin/sljit_test     # 上游测试 1/2 → SLJIT tests: all tests PASSED（138 内部用例）
./bin/regex_test     # 上游测试 2/2 → REGEX tests: all tests PASSED
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMakeLists 无 install 且声明仅为无 GNU make 平台的辅助 | CMake 仅构建 sljit_test 单二进制、无安装规则 | 不用 CMake；按 GNUmakefile 语义直接编译 sljitLir.c 单 TU 成库 |
| 2 | regex_test 失败时退出码仍为 0 | run_tests 为 void，仅打印汇总，main 只对溢出回归返回非零 | 逐二进制判定必须同时满足退出码 0、日志非空、汇总行存在、`all tests PASSED` 存在且无 FAILED/FAIL 标记 |
| 3 | Windows 工作区无法检出上游个别文件 | gama 补丁文件名含回车、libXext/libxext 大小写冲突 | 本机稀疏检出排除 archives/g/gama 与 archives/l/libXext；与本配方无关，真机归档以远端完整树为准 |
| 4 | 上游两二进制明明打印 PASSED 却被判失败（rc=0） | 上游非 Windows 用 `\33[32mPASSED\33[0m` 彩色输出，日志含 ANSI 转义，字面 `all tests PASSED` 不存在，判定直接在原串上匹配 | 判定前用 `re.sub(r"\x1b\[[0-9;]*[A-Za-z]","",out)` 去色后再做单一 `summary_tag + all tests PASSED + 无 FAILED/FAIL` 判定 |
| 5 | test_package CMake configure 失败：`System is unknown to cmake / Platform/HarmonyOS` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang broken`，主库与上游 2/2 测试已过 | 双因子：① Conan os=OHOS 默认生成 `CMAKE_SYSTEM_NAME=HarmonyOS`，真机 vanilla cmake 4.4.3 无此平台模块（E092）；② profile 的 `compiler_executables` 钉死已迁移的 `/data/service/hnp/bin/clang` 绝对路径，CMakeToolchain 原样烘焙致编译器检测失败（lz4 DRAFT 证据；首轮仅修①复检仍报 `C compiler identification is unknown`） | test_package 改显式 `generate()`：`CMAKE_SYSTEM_NAME=Linux`（Linux/OHOS）+ OHOS 下 `CMAKE_SYSTEM_PROCESSOR=aarch64`；新增 stale-toolchain 兜底（cvector/bzrtp 先例）：conf 绝对路径存在才用否则 `shutil.which` 回退，经 `tc.cache_variables[CMAKE_C/CXX_COMPILER]` 强制并用 `replace_in_file` 重写 `conan_toolchain.cmake` 残留旧路径 |

## 源码修改

- 无 patches/（无需 OHOS 适配补丁）。

## 依赖版本

- 无第三方构建依赖（仅需 libc / libm / libpthread 系统库）。

## 验证结果

```bash
# 上游 2 个测试二进制（GNUmakefile TARGET），口径 auto：
#   bin/sljit_test（138 内部 LIR 用例）+ bin/regex_test（regex 用例表）
#   conanfile.py build() 逐个运行并输出 HMBS_UPSTREAM_TEST_RESULT 标记。
# test_package 消费者 5 断言待真机预检回填。
```

## 注意事项

- 上游测试计数口径为 auto（GNUmakefile TARGET 行 2 个二进制）。
- JIT 依赖 mmap/mprotect 可执行内存，HarmonyOS PC 内核提供。
- 本轮仅完成工作树；实测数字以真机预检日志为准，不估算、不推断。
