# fasttextembed 1.0.2：CMake `check_c_compiler_flag` 自动启用 host-CPU native 标志的 option 门控

> 草稿（DRAFT）— 来自 fasttextembed 1.0.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/fasttextembed-1.0.2-cmake-native-cpu-flag-gate.kv`

## 软件与平台

- **软件**：fasttextembed 1.0.2（https://github.com/cemsina/fasttextembed，MIT）
- **构建系统**：CMake（C11，`project(fasttextembed C)`）
- **平台**：HarmonyOS PC / aarch64，Conan profile `ci/conan/profiles/ohos-aarch64`
  （os=OHOS 6.0, arch=armv8, clang 15.0.4, libc++, cppstd 17, Release）

## 现象

上游 `CMakeLists.txt` 顶部有一个 **host-CPU SIMD 自动探测块**：

```cmake
include(CheckCCompilerFlag)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "x86_64|AMD64|amd64|i[0-9]86")
    check_c_compiler_flag("-march=native" HAS_MARCH_NATIVE)
    if(HAS_MARCH_NATIVE)
        add_compile_options(-march=native)
    endif()
else()
    check_c_compiler_flag("-mcpu=native" HAS_MCPU_NATIVE)   # ARM
    check_c_compiler_flag("-march=native" HAS_MARCH_NATIVE)
    if(HAS_MCPU_NATIVE)
        add_compile_options(-mcpu=native)
    elseif(HAS_MARCH_NATIVE)
        add_compile_options(-march=native)
    endif()
endif()
```

- 非报错型适配点，但属 **可复现性硬约束**：`-mcpu=native`/`-march=native` 把
  **构建主机 CPU 特性**固化进产物，本机成功 ≠ CI/其他构建机可复现；
- 与 ascon-c（REL_FLAGS **cache 变量**含 `-march=native`，可用
  `tc.variables["REL_FLAGS"]=...` 直接覆盖）不同：这里是 `check_c_compiler_flag`
  **动态探测 + 直接 `add_compile_options`**，没有可覆盖的 cache 变量，
  配方侧无法单靠 tc.variables 关闭探测结果。

## 方案（fasttextembed 1.0.2 实测）

**最小补丁 + option 门控**（`patches/0001-add-native-cpu-flag-option.patch`，
仅改构建配置，不引入平台宏、不改源码语义）：

```cmake
option(FTE_DISABLE_NATIVE_CPU "Disable host-CPU -mcpu/-march=native flags (portable cross builds)" OFF)
if(NOT FTE_DISABLE_NATIVE_CPU)
include(CheckCCompilerFlag)
... 原探测块原样 ...
endif()
```

配方 `generate()`：

```python
tc.variables["FTE_DISABLE_NATIVE_CPU"] = "ON"
tc.variables["FTE_SHARED"] = "ON" if self.options.shared else "OFF"
```

- arm64 的 NEON 内核（`src/kernels/kernels_scalar.c`）由 `__aarch64__` 自动选择，
  关闭 host-CPU 微调不影响正确性与 arm64 加速路径；
- 补丁上下文行仅 2 行注释 + 1 行 include，未来上游变更易维护；
- 生成规范补丁时注意：`diff -u` 输出须带相对路径
  `--- a/CMakeLists.txt` / `+++ b/CMakeLists.txt`（用 `--label`），
  否则 conan `apply_conandata_patches` 报 "absolute paths are not allowed"。

## 验证

- `conan create`（ohos-aarch64 / clang 15.0.4）：补丁应用后 configure 通过，
  无 native 标志注入；libfte.a + fte_cli + vocab.tsv 打包完整；
- test_package 消费者 1/1 通过（真实调用 fte_init/fte_embed/fte_embed_batch）；
- 鸿蒙专项测试 1/1 通过（合成 .fte 模型端到端，384 维 L2 归一化输出）。

## 适用边界

- 适用于 CMake 项目在 CMakeLists 内用 `check_c_compiler_flag` **动态探测**并
  `add_compile_options` native CPU 标志的场景（无 cache 变量可覆盖）；
- cache 变量形态（如 ascon-c REL_FLAGS）仍走 tc.variables 覆盖，不需要补丁；
- 硬编码 `CXXFLAGS`/`CMAKE_C_FLAGS` 形态用移除补丁（clthreads 同源经验）。
- 反例：header-only/无编译产物库不涉及；纯 x86 宿主且目标同为 x86 的本地
  非 CI 构建可容忍，但 CI 交叉构建不可接受。
