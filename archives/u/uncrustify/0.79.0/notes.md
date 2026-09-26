# uncrustify 0.79.0 适配笔记

## 编译环境

- 构建系统: cmake（上游根 `CMakeLists.txt`，`cmake_minimum_required(VERSION 3.5)`）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（未合并、无 release upload，按工作区口径不标 published）
- 目标: OpenHarmony PC aarch64（`os=OHOS`、`arch=armv8`、`compiler.libcxx=libc++`、`cppstd=17`）

## 编译步骤

```bash
# 1) 设备原生（探索与上游测试清点）
cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release
cmake --build <build> -j4
ctest --test-dir <build> --output-on-failure -j2        # 14/14 Passed，491.87 s

# 2) Conan 配方（conanfile.py build()）
cmake.configure() -> cmake.build() -> cmake.test()      # 上游 ctest 真实集成
cmake.install()                                        # bin/uncrustify + man1 + doc/cfg

# 3) 采信轮（干净缓存的权威验证）
sh tools/conan_verify_round.sh uncrustify 0.79.0 --repo <worktree> --task-dir <task_dir>
```

`conanfile.py` 的 `build()` 第 4 步就是 `cmake.test()`，即 CI 的 `conan create`
会真实执行全部上游测试，失败即 CI 失败（不是空壳、不是可选步骤）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游对 OHOS/clang15/CMake 4.1 开箱即用，未出现任何编译错误 | 上游只用标准 C++17 与 POSIX/CMake 自带模块，无 ISA 专属头、无 glibc printf 钩子（W0 grep 0 命中） | 无需补丁，`patches: {}` 保持为空；不为「看起来像适配」而造补丁 |
| 2 | CMake 4.x 已移除 `FindPythonInterp`，担心上游 `tests/CMakeLists.txt` 的 `${PYTHON_EXECUTABLE}` 失效 | 根 `CMakeLists.txt` 在策略允许时回退到 `find_package(Python3 REQUIRED)` 并回填 `PYTHON_EXECUTABLE` | 实测设备 cmake 4.1.2 配置通过、14 项测试全绿，无需干预 |
| 3 | `sources_format`（上游自检自身源码风格）依赖 `tests/run_sources_tests.py` 遍历 `src/*.cpp|*.h` | 该用例属上游测试而非鸿蒙新增，必须如实运行 | 原样运行 193.15 s 通过（108 个源文件），计入上游分母 |

## 源码修改

无。本次适配 `patches/` 为空，`conandata.yml` 只有 sources 段，源码按 tag 原样构建。

## 依赖版本

- Conan 依赖: **0 个**（任务卡声明 0 依赖；上游 `CMakeLists.txt` 无任何 `find_package`
  外部库，构建只链 libc/libc++ 与标准数学库）
- 工具链: clang/clang++ 15.0.4、cmake 4.1.2、make 4.4.1、python 3.12.9（CTest 驱动脚本）

## 验证结果

```bash
# 上游测试（沙箱 HOME，2026-09-26）
$ HOME=$TASK_DIR/test-home ctest --test-dir <build> --output-on-failure -j2
100% tests passed, 0 tests failed out of 14
Total Test time (real) = 491.87 sec
# 逐用例清点（同一粒度）：格式化套件 1876 + src 风格 108 + cli_options 逐检查项 64 + sanity 1 = 2049 全部 PASS
#   cli_options 取数: ctest --test-dir <build> -V -R cli_options | grep -E '^[0-9]+: Test ' \
#                     | grep -v -e 'Test command:' -e 'Test timeout' | wc -l   ->  64

# 适配侧（test_package 消费者用例）
$ sh test_package/test.sh <package_folder>/bin <recipe_folder> <build_folder>
RESULT summary: PASS=13 FAIL=0 TOTAL=13 SKIP=0
```

| 口径 | TOTAL | PASS | FAIL | SKIP | NOT_RUN |
|------|-------|------|------|------|---------|
| 上游测试用例 | 2049 | 2049 | 0 | 0 | 0 |
| 适配侧断言（鸿蒙特有测试行） | 13 | 13 | 0 | 0 | 0 |

## 注意事项

- 上游测试用例数与 `test_package` 断言数分属两个口径，PR 正文按模板分栏，
  不混算、不把消费者用例计入上游分母。
- `uncrustify` 是纯 CLI 应用（`package_type="application"`、只装 `bin/`），
  软件级 `commands.json` 已声明（PF8/L0k 要求）。
