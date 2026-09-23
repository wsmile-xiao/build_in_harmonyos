# numkong 7.8.1 适配笔记

## 库概况

- 上游：https://github.com/ashvardanian/NumKong （v7.8.1 tag，注意上游最新为 v7.8.2，任务指定 7.8.1）
- 性质：可移植混合精度数学/线性代数/检索库，2000+ SIMD 内核（x86 AVX/AMX、Arm NEON/SVE/SME、RISC-V RVV、LoongArch LASX、Power VSX、WASM SIMD128）
- 结构：header-heavy C 库——`include/numkong/`（246 个 .h/.hpp，含 C++ 模板封装）+ 可选动态分发库 `c/*.c`（26 个 dispatch TU → libnumkong.so）
- **不依赖 numpy 本体**（独立 C 库；python/ 目录只是 CPython 绑定源码，打包时不会编译）
- 语言分布实测：c:76 + cpp:74（含 test/bench）为主体 71%，rust:18/python:21/golang:14/swift:6/js:2 全部是绑定层（Cargo.toml `links="numkong"`、include 列表 `c/*.c + include/**/*.h` 证明 rust crate 是 FFI 绑定）
- ⚠️ lang-preflight 误判：判定器将 Cargo.toml（绑定 manifest）按最高优先级判为 rust；实际核心是 C 库，c/cpp 族占比 71% ≥ 70%。已在 PR/notes 记录，按 C/C++ 适配（与附录 D.4-2 pybind11 绑定判 cpp 同理）

## 平台与工具链

- HarmonyOS PC aarch64，musl libc，clang 15.0.4（/data/service/hnp/bin/clang）
- conan profile：ohos-aarch64（os=OHOS, arch=armv8, compiler=clang 15, libc++）

## 关键适配点（本次发现，最重要）

### 1. OHOS clang 15 忽略 per-function target attribute → SVE 探针误报

- 现象：`NK_BUILD_SHARED=ON` 直接构建失败，`arm_sve.h:15:2: error: "SVE support not enabled"`，20 errors
- 根因链：
  1. 上游 `cmake/nk_arm_isa_probes.cmake` 用全局 `-march=armv8.2-a+sve` 编译探针 TU → `check_source_compiles` 成功 → `NK_TARGET_SVE=1`
  2. `nk_shared` 分发库 TU 以基线 `-march=armv8-a` 编译（上游"portable baseline policy"），但 `NK_TARGET_SVE=1` 传入后 `types.h:640` 在 TU 层 include `<arm_sve.h>`
  3. 基线 TU 无 SVE 宏 → clang 15 自带 `arm_sve.h` 第 15 行 `#error "SVE support not enabled"`
  4. 上游设计本意：SVE 内核函数用 per-function `__attribute__((target("arch=armv8.2-a+sve")))` 指定目标（types.h 的 include 也在函数外层由 `#pragma clang attribute push` 推断）——但 OHOS clang 15 对 `target("arch=armv8-a+simd")` 报 `warning: unknown architecture ... 'target' attribute ignored`，该机制失效
  5. 上游 CMakeLists 注释明确"Float16 support: GCC 12+, Clang 16+；Intel AMX/Arm SME: GCC 14+, Clang 18+"——clang 15 处于 SVE/HALF/SDOT/BFDOT/FHM per-function 支持红线以下
- **对策（本配方）**：`generate()` 里 `tc.cache_variables` 预填探针结果——`nk_target_neon_compiles=True`，其余全部 `False`（neonhalf/neonsdot/neonbfdot/neonfhm/neonfp8/sve*/sme*）。NEON 是 armv8-a 基线自带的，探针通过且内核可用；运行时分发 `nk_capabilities()` 仍完整工作
- 效果：libnumkong.so 构建成功 + 上游测试全绿

### 2. 上游测试套（两条路径均实测通过）

- `NK_BUILD_TEST=ON` → `nk_test`（header-only 内联内核路径）：**All tests passed.** exit=0
  - 26 个断言组（vector/tensor/cast 实例化，全部 OK）+ 459 个内核精度行（ULP 误差分析）
- `NK_BUILD_SHARED_TEST=ON` → `nk_shared_test`（动态分发库路径，NK_DYNAMIC_DISPATCH=1）：**All tests passed.** exit=0
  - 26 个断言组 + 291 个内核精度行
- 运行时需 `LD_LIBRARY_PATH` 指向 OHOS SDK `libc++_shared.so` 目录（musl 测试二进制动态链接 libc++_shared.so）
- ISA 探针锁定后运行头显示 `ISA: NEON ◑ ...`（运行时 CPU 只有基础 NEON，与锁定一致）

### 3. 版本与源码

- 官方源：https://github.com/ashvardanian/NumKong/archive/refs/tags/v7.8.1.tar.gz
- sha256: cb5814875b2cee6a843fa458cde3f9684d4ed961f52803a25eb79a5f23a25ce4
- W0 预检：零 conan 依赖（预期直过，实测 preflight OK）

### 4. 安装布局

- `include/numkong/*`（246 头文件 + module.modulemap + README）
- `lib/libnumkong.so`（动态分发库）
- `share/doc/numkong/src/*.c`（dispatch 源码文档）
- 上游不安装 CMake Config 文件 → 配方 `package_info` 自带 `cmake_file_name=numkong` / `cmake_target_name=numkong::numkong`，test_package 的 `find_package(numkong CONFIG REQUIRED)` 由 conan CMakeDeps 生成
- CMake 4.1.2 遇上游 `cmake_minimum_required(3.20)` 需要 `CMAKE_POLICY_VERSION_MINIMUM=3.10` cache 变量

### 5. test_package（R34 实质测试）

- `test_package.c`：链接 libnumkong.so 调 C API——nk_capabilities()（断言 aarch64 NEON）、nk_dot_f32=32、nk_euclidean_f64=5、nk_haversine_f64 两极≈20015km
- `test_headeronly.cpp`：header-only 路径——nk_dot_f32=10、nk_f32_sqrt(4)=2

## 结论

- conan create（ohos-aarch64 profile）：通过（W3，.ci-result.json exit_code=0）
- 上游测试：nk_test 485/485、nk_shared_test 317/317 全过
- status: published
---

**编译结束**: 2026-09-03 19:21
**最终状态**: published
