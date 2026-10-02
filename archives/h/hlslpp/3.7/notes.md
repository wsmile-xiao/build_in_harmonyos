# hlslpp 3.7 适配笔记

## 库简介

hlslpp 是一个 HLSL（High Level Shading Language）风格的 C++ 数学库，提供
`float1~float4`、`int1~int4`、`uint1~uint4`、`double1~double4`、`float1x1~float4x4`
矩阵与 `quaternion` 类型，让图形/游戏应用在 CPU 侧直接复用与着色器一致的数学写法。

- 语言：C++11 起（本配方与上游测试用 C++17）
- 形态：**header-only**，`include/hlsl++.h` + `include/hlsl++/*.h`（共 76 个 .h）
- 第三方依赖：**零**
- 许可：MIT

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | 上游 premake5（`hlsl++.lua` / `Linux.sh`）；配方自带 `test_upstream/CMakeLists.txt` |
| 目标平台 | OHOS / aarch64（armv8） |
| 编译器 | `aarch64-unknown-linux-ohos-clang++` 15.0.4 |
| libc++ | libc++（`-stdlib=libc++`） |
| sysroot | `/root/ohpc/sdk/ohos-6.0/native/sysroot` |
| Conan profile | `ohos-aarch64-run`（`CMAKE_CROSSCOMPILING_EMULATOR` → qemu-aarch64） |
| 编译日期 | 2026-10-01 |
| 状态 | built |

## 后端选择（无需任何配置）

`include/hlsl++/config.h` 依据预定义宏自动选择后端，鸿蒙 PC（aarch64）走 NEON：

```
!HLSLPP_ARM && (__arm__ || __aarch64__ ...) -> #define HLSLPP_ARM -> platforms/neon.h
```

`platforms/neon.h` 在 `__aarch64__` 下额外定义 `HLSLPP_ARM64` 与 `HLSLPP_DOUBLE`，
因此 **aarch64 默认就带 double 向量支持**（x86 SSE 路径的 `HLSLPP_FLOAT8`
则只在 `platforms/sse.h` 定义，NEON 下不存在）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游无 CMake/autotools/meson 入口，CI 无法直接调用其测试 | 上游仅提供 premake5（`hlsl++.lua`、`Linux.sh`），premake5 二进制未入库 | 配方自带 `test_upstream/CMakeLists.txt`（`exports_sources`）编译**同一批上游 `unit_tests/*.cpp` 源文件**（不改一个字符），源根目录由 `-DHLSLPP_SRC_DIR=<source_folder>` 传入 |
| 2 | `os=OHOS` 属交叉编译，`can_run()` 恒为 `False`，上游测试被静默跳过（违反 rule4） | Conan 的 `can_run()` 只看 os/arch 是否同构，不识别 profile 里已配置的 `CMAKE_CROSSCOMPILING_EMULATOR` | 配方新增 `_test_runner()`：`can_run()` 为假时回读 `tools.cmake.cmaketoolchain:extra_variables` 里的 `CMAKE_CROSSCOMPILING_EMULATOR`，识别到 qemu 包装脚本即照常编译并执行上游测试；两者都无才告警跳过 |
| 3 | `cmake.test(cli_args=[...])` 报 `Unknown argument --output-on-failure` | `CMake.test()` 映射为 `cmake --build --target test`，`cli_args` 会落到**底层 make** 而非 ctest（且本仓库 Conan 2.29.1 无 `conan.tools.cmake.CTest` 类） | 改为 `self.run("ctest --output-on-failure --test-dir <build_folder>")` 直接调用 ctest |
| 4 | `mul(mat_bar_2x2, mat_foo_2x3)` 的 `r[1][1]` 与上游期望值差 **+1 ULP**，`Float Matrix Multiplication` 用例失败（46 用例中 1 例） | aarch64 上 clang 默认 `-ffp-contract=fast`，而 **ARMv8 强制具备 FMA**，`0.3*2 + 0.4*5` 被融合成单条 `fmla`：融合结果 `2.60000014`（0x40266667），分步舍入结果 `2.5999999`（0x40266666）——上游该断言用 `tolerance=0.0f` 精确比较，故对 FMA 敏感。上游 AppVeyor 的 `Linux64 GCC/Clang` 未开 `-march=native`，x86 无 FMA 所以不暴露 | 仅对上游测试翻译单元加 `-ffp-contract=off`（见 `test_upstream/CMakeLists.txt`），恢复与上游 SSE/标量路径一致的分步舍入；**库源码零改动**，对外发布的头文件不附加任何编译选项 |
| 5 | 消费者用例里 `mul(M, v)` / `m[c][r]` 取值与预期不符 | hlslpp 默认行主序（`HLSLPP_LOGICAL_LAYOUT_ROW_MAJOR`）且乘法顺序是 `mul(vector, matrix)`；矩阵下标 `m[c][r]` 先列后行 | 实测确认元素映射为 `out[c] = sum_r v[r] * m[r][c]`，据此重写消费者用例的手写参照实现 |

### 问题 4 的判定依据（非猜测）

| 编译方式 | `r[1][1]` | 与期望值 ULP 差 |
|---|---|---|
| aarch64 clang `-O2`（默认 `-ffp-contract=fast`） | `2.60000014` | **+1** |
| aarch64 clang `-O2 -ffp-contract=off` | `2.5999999` | **0** ✅ |
| aarch64 clang `-O2` 强制 `HLSLPP_SCALAR` 后端 | `2.60000014` | +1 |
| x86_64 clang 单独计算 `fmaf(0.4,5, 0.3*2)` | `2.60000014` | +1 |
| x86_64 clang 单独计算分步舍入 `round(0.3*2)+round(0.4*5)` | `2.5999999` | 0 |

结论：偏差来自**编译器乘加融合**，与 NEON 后端实现无关（强制 scalar 后端同样复现），
且 ARMv8 架构上无法通过关闭 FMA 指令来规避，只能通过关闭收缩语义解决。
这是**上游测试对 FMA 敏感的固有精度假设**，不是适配引入的功能缺陷，故不修改上游测试文件。

## 源码修改

**无。** 库源码与上游 3.7 标签完全一致，`patches: {}` 为空。
唯一新增的是配方自带的 `test_upstream/CMakeLists.txt`（测试工程描述，不改上游测试源码）。

## 依赖版本

无第三方依赖（header-only，零 `.so`/`.a` 产物）。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | header-library 配方；`build()` 中真实编译并执行上游测试 |
| `conandata.yml` | 官方 GitHub 3.7 归档 + sha256 `819a3d20...` |
| `test_upstream/CMakeLists.txt` | 编译上游 `unit_tests/*.cpp` 的测试工程（含 `-ffp-contract=off`） |
| `test_package/` | 消费者端到端用例 + `MANIFEST.yml` 上游测试声明 |
| `manifest.yaml` / `notes.md` | 版本级元数据与适配笔记 |

## 验证结果

- 编译状态：**通过**（`conan create` exit 0，产出 76 个 `.h` + 1 个 `.natvis` + LICENSE）
- 上游测试用例通过率：**46/46（100.00%）**，0 失败
  - 执行方式：qemu-aarch64 经 profile 的 `CMAKE_CROSSCOMPILING_EMULATOR` 运行
  - 明细：`unit_tests_vector_float.cpp` 12、`unit_tests_vector_int.cpp` 12、
    `unit_tests_vector_double.cpp` 10、`unit_tests_matrix_float.cpp` 8、
    `unit_tests_matrix_transform.cpp` 4（共 46）
  - ctest：`100% tests passed, 0 tests failed out of 1`
- 消费者端到端用例：**30/30 检查通过**（`test_hlslpp`，exit 0）

## 注意事项

- 上游 `unit_tests.cpp` 的 `main()` 支持 `experiments` / `perf_tests` 参数；本配方只执行
  `unit_tests`（性能测试在 qemu 下无意义，上游 CI 亦不上报）。
- `HLSLPP_FLOAT8` 为 SSE/AVX 专属（`platforms/sse.h` 定义），NEON 下不存在，
  故 aarch64 上不编译 `unit_tests_vector_float.cpp` 中 `#if defined(HLSLPP_FLOAT8)` 的段落
  —— 这是上游自身条件编译行为，非适配裁剪。
- `conandata.yml` 源 URL 保持官方 GitHub（R39），CI 自动注入镜像 fallback。
- 本库为 header-only，无 `commands.json`（无 bin 产物）。
