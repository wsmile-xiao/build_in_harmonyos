# mdspan 0.6.0 适配笔记

## 库简介

mdspan（Kokkos 团队维护的 **C++ 标准提案 P0009 参考实现**，`std::experimental::mdspan` /
`mdarray`）——header-only 多维数组视图与拥有容器。交付物为 `include/experimental/**`
**21 个头文件**（含两个无扩展名汇总头 `experimental/mdspan`、`experimental/mdarray`），
上游 CMake 目标是 `INTERFACE`，无编译产物、零依赖、无外部运行期需求。

## 编译环境

- 构建系统: cmake（header-only + 上游 INTERFACE 目标一致性校验）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 / clang++（`aarch64-unknown-linux-ohos`，OHOS SDK 26.0.0.18）
- Conan: OHOS 适配版 2.29.1；profile `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 /
  compiler=clang 15 / libc++ / **cppstd=17**）
- 状态: built（conan-verify + 设备原生上游测试 + W3 本地 CI 通过，未 upload）

## 编译步骤

1. **源码**：`https://github.com/kokkos/mdspan/archive/refs/tags/mdspan-0.6.0.tar.gz`
   （tag 带前缀形态、轻量 tag → commit `9ceface91483775a6c74d06ebf717bbb2768452f`；
   实测 215304 字节、解包 2.0M、sha256 `79f94d7f…48a592`，与 conandata/manifest 三路一致）。
2. **配方 `build()`**：上游 CMake configure + build（`MDSPAN_ENABLE_TESTS/EXAMPLES/
   BENCHMARKS/COMP_BENCH` 四项在 `generate()` 里逐项显式钉 OFF）——INTERFACE 目标不编译任何
   翻译单元，configure+build 用于校验工程自洽；**G2 干净轮必须离线**（上游测试树默认会用
   `ExternalProject` 联网克隆 googletest 且 `GIT_TAG main` 是移动靶）。
3. **`package()`**：`copy(include/* → include/)` + `copy(LICENSE → licenses/)`；
   `package_id()` 清空（单一 package_id）。
4. **`test_package`**：两个可执行消费者（`consumer` + `ohos_special_test`），
   `test()` 里逐个 `self.run(..., env="conanrun")` 真实执行。
5. **设备端上游测试**（不在配方内，见下「验证结果」）：原生 CMake
   `-DMDSPAN_ENABLE_TESTS=ON -DMDSPAN_USE_SYSTEM_GTEST=ON`，C++20 与 C++17 各跑一轮。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `task_init.sh` 首跑拒绝（包目录不存在） | `archives/m/mdspan` 在 upstream/main 无历史（首适配新包） | 按 §3.1 用 `--allow-unpublished` 放行；分支门禁 `feat/mdspan-0.6.0` 去前缀 == 包目录名-版本 **精确匹配** |
| 2 | 上游测试树默认联网克隆 googletest（`GIT_TAG main`） | `cmake/googletest/CMakeLists.txt.in` 用 `ExternalProject` 拉 HEAD | 配方 `generate()` 显式钉 `MDSPAN_ENABLE_TESTS=OFF`（G2 离线）；设备端测试改用 `MDSPAN_USE_SYSTEM_GTEST=ON` + 本地构建的 googletest v1.14.0（sha256 `8ad598c7…1bba5d7`） |
| 3 | gtest 只有 13 个 ctest 注册项、源码却有 148 个用例宏 | `TYPED_TEST` 按类型表展开（148 → 469@C++17 / **474**@C++20）；`compilation_tests/` 只 `add_executable` 不 `add_test` | 计数按「用例口径」四步清点：源码宏 → 运行期注册 → 编译期实编译 → 差额逐项归因（见 manifest `test_summary`） |
| 4 | 源码 151 条 `MDSPAN_STATIC_TEST` 只有 135 条被编译 | 上游 `MDSPAN_ENABLE_EXPENSIVE_COMPILATION_TESTS=0` 默认关闭（10 条）、`#if !defined(__GNUC__) \|\| (__GNUC__ > 10)` 在 clang（自报 `__GNUC__`=4）下恒假（4 条）、`#if 0` 死块（1 条）、`_MDSPAN_COMPILER_MSVC` 分支（1 条） | 不改上游测试源（零补丁）；预处理逐文件计数 151→135 留证，差额写进 manifest 与 PR 说明 |
| 5 | OHOS libc++15 无 `<memory_resource>`，`tests/test_mdarray_ctors.cpp` 的 102 条断言语面被编译掉 | `#ifdef __cpp_lib_memory_resource` 区块不激活 | 属 **OHOS 缺特性**（同 taskflow `std::pmr` 先例）；如实记入断言口径说明，不计入用例口径 N |
| 6 | 设备 toybox 族命令与 GNU 差异（`cat -A` 不可用等） | §一.35「名字对、实现不对」 | CRLF/结构核对改 `od -c` / python 断言 |

## 源码修改

**无补丁**（`patches_applied: []`）。W0-3 平台可移植性档：交付头树 grep ISA 专属头
（`altivec.h`/`mmx.h`/`xmmintrin.h`/`arm_neon.h`/`immintrin.h`…）、内联汇编与内建
（`asm(`/`__asm__`/`_mm_`/`__builtin_ia32`）、glibc printf 钩子族（`register_printf_`/
`<printf.h>`）**均 0 命中**；`include/` 系统头全集 18 个全为 C++ 标准库头且
`<concepts>`/`<span>`/`<version>` 均在特性测试宏守卫内；无 `.S` 汇编、无 arch 目录。

## 依赖版本

- **配方依赖：0**（`requires`/`tool_requires` 均为空；`conan list -r=ohpcd "mdspan/*"` → Found 0，本单为首适配）。
- 设备端上游测试依赖（不进配方）：googletest **v1.14.0**（本地构建安装到 `$TASK_DIR/w0/gt/prefix`；
  兜底可用性 `conan list -r=ohpcd "gtest/*"` → Found 3，1.17.0/1.17.0.1/1.17.0.2）。
- `benchmarks/` 的 `find_package(benchmark)` 与 `cmake/metabench.cmake` 的 Ruby 属**可选且默认 OFF**，不构建不申报。

## 验证结果

### 1) 配方面（conan create）

```bash
conan create archives/m/mdspan/0.6.0 -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 \
        -pr:b=<同profile> -c tools.build:jobs=2
# → rc=0；Conan: Target declared 'std::mdspan'
# → consumer: PASS 50/50 assertions (compile-time static_assert=11)
# → mdspan 0.6.0 OHOS special test: ALL OK (24 checks)
```

### 2) 设备端原生上游测试（沙箱 HOME，`HOME=$TASK_DIR/test-home`）

```bash
# 入口（上游 CMake，等价 README「Running tests」）
cmake -S <src> -B <build> -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ \
      -DCMAKE_CXX_STANDARD=20 -DMDSPAN_CXX_STANDARD=20 \
      -DMDSPAN_ENABLE_TESTS=ON -DMDSPAN_ENABLE_EXAMPLES=OFF \
      -DMDSPAN_ENABLE_BENCHMARKS=OFF -DMDSPAN_ENABLE_COMP_BENCH=OFF \
      -DMDSPAN_USE_SYSTEM_GTEST=ON -DCMAKE_PREFIX_PATH=<gtest-prefix>
cmake --build <build> -j2 && ctest --test-dir <build> --output-on-failure
# → C++20: configure rc=0（Using C++20 standard）build rc=0
#   ctest → 100% tests passed, 0 tests failed out of 13（Total Test time 0.58 sec）
#   运行期用例 474/474（13 个 gtest 可执行，failures=0 disabled=0）
#   compilation_tests 14/14 编译 + 运行通过
# → C++17（OHOS profile cppstd=17）同套件复跑：ctest 13/13、运行期用例 469、编译期 130，全通过
```

### 3) 计数口径（单位 = 上游测试用例；四口径分列，N 取用例口径最大）

| 口径 | 数值 | 取数命令 |
|---|---|---|
| 源码用例宏 | **148**（`TEST(` 116 + `TYPED_TEST(` 32；宽口径两目录 `grep -o 'TEST('` = 309） | `grep -rhoE '(?<![A-Z_])TEST\(' tests/*.cpp` |
| 框架注册数 | **474** 运行期用例（ctest 注册 13）+ **135** 编译期用例（compilation_tests 14 个可执行） | `ctest -N` / 运行期 XML `tests="…"` / 预处理 `static_assert` 计数 |
| 断言数（不同单位） | 541（运行期语面）+ 151（`MDSPAN_STATIC_TEST`）+ 21（`constexpr_assert`）= **713**；实编译 135 + 12 | `grep -rhoE '\b(ASSERT\|EXPECT)_[A-Z_]+\('` 等 |
| 消费者断言 | **74**（consumer 50 + ohos_special 24）+ 编译期 12 | `test_package` 运行输出 |

**申报 N = max(148, 309, 151, 474, 135) = 609 = 474 + 135**（用例口径）；
四分项 `PASS=609 / FAIL=0 / SKIP=0 / NOT_RUN=0`，通过率 **609/609（100%）**。

### 4) 消费者（test_package）

```text
consumer: PASS 50/50 assertions (compile-time static_assert=11)
mdspan 0.6.0 OHOS special test: ALL OK (24 checks)
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/experimental/**`（21 个文件） | 上游交付头树原样（含 `mdspan`、`mdarray` 两个汇总头） |
| `licenses/LICENSE` | 上游 Apache-2.0 WITH LLVM-exception |

## 注意事项

- 本包 `status: built`（未 upload，O5 口径：合并 + release upload 确认才 `published`）。
- 上游无版本宏，`test_package` 用**内容指纹**（安装头 sha256 + 交付文件数）替代版本宏断言。
- `packaging/` 为 ARCHIVE-SPEC v3.0 废弃项，不创建不提交；`reports/` 被 `.gitignore` 忽略不入 PR。
