# fasttext 0.9.2：硬编码 `-march=native` 字面量跨 CMake/Make/setuptools 三构建系统的统一剥离

> 草稿（DRAFT）— 来自 fasttext 0.9.2 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 `knowledge/drafts/fasttext-0.9.2-cmake-hardcoded-march-native-strip.kv`

## 软件与平台

- **软件**：fasttext 0.9.2（https://github.com/facebookresearch/fastText，MIT）
- **平台**：HarmonyOS PC aarch64，clang 15.0.4（/data/service/hnp/bin），conan 2.29.1（OHOS 适配版）
- **构建系统**：CMake（主）+ Makefile + setup.py（pybind11 Python 绑定）

## 现象

官方 tarball 在三个构建入口**同时硬编码** `-march=native`：

```
CMakeLists.txt: set(CMAKE_CXX_FLAGS " -pthread -std=c++11 -funroll-loops -O3 -march=native")
Makefile:      CXXFLAGS = -pthread -std=c++11 -march=native
setup.py:      extra_compile_args=[... "-O3 -funroll-loops -pthread -march=native"]
```

## 根因

字面量 `-march=native` 让编译器按**构建主机** CPU 特性生成指令。OHOS 交叉/干净
构建下，产物指令集随构建机漂移、CI 不可复现。CMake 侧是 `set()` 覆盖 CMAKE_CXX_FLAGS
（无 cache 变量可覆盖），Makefile/setup.py 也是字面量——配方侧 `tc.variables`
无法覆盖，只能补丁剥离。

## 方案（最小补丁，无平台宏）

`refresh-patch --auto` 生成三个补丁，三处一致移除 `-march=native`：

- `patches/0001-CMakeLists.txt.patch`：`set(CMAKE_CXX_FLAGS "... -march=native")` → 去掉标志
- `patches/0002-Makefile.patch`：`CXXFLAGS = ... -march=native` → 去掉标志
- `patches/0004-setup.py.patch`：`extra_compile_args=[... -march=native]` → 去掉标志

arm64 平台路径由 `__aarch64__` 自动选择（fasttext 无显式 NEON 分支），性能语义不变。

## 验证

- `conan create`（ohos-aarch64 profile，clang 15）：G2 通过，产物 libfasttext.a/.so/_pic.a + bin/fasttext 完整
- test_package 消费者（train→predictLine）：1/1 通过（ctest Passed）
- 鸿蒙专项端到端（tests/test_ohos_e2e.cpp）：1/1 通过，train_acc=1.000 / valid_acc=0.750
- 上游 Python 绑定单测：83/83（numpy 1.26.4）

## 查重与差异

- **similar_to**：`fasttextembed-1.0.2-cmake-native-cpu-flag-gate`（E582 预留）——同根因族，
  但该条覆盖 `check_c_compiler_flag` 动态探测 + `option` 门控形态；本条覆盖**三构建系统
  硬编码字面量的识别与统一剥离**（无探测、无门控、无 cache 变量）。
- 既有条目未覆盖"字面量跨 CMake/Make/setuptools 三处同时出现"的组合边界。

## 适用边界

- 适用：任何在 CMakeLists.txt / Makefile / setup.py 中写死 `-march=native` 的 C/C++ 库；
  剥离后不影响 `__aarch64__` 等自动平台路径。
- 反例：若上游使用 `check_c_compiler_flag` 动态探测（如 fasttextembed），应走 option 门控
  而非字面量剥离；若标志来自 cache 变量（如 ascon-c REL_FLAGS），可用 `tc.variables` 覆盖。
