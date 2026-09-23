# libmsym 0.2.3 适配笔记

## 编译环境
- 构建系统: cmake（上游 `project(libmsym)` + `-std=c99`）
- 编译日期: 2026-09-15
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18，target aarch64-linux-ohos）
- 目标: OpenHarmony/HarmonyOS PC aarch64（conan profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

```sh
# 1) 源码（官方 GitHub tag，sha256 见 conandata.yml）
curl -sSL -o libmsym-v0.2.3.tar.gz \
  https://github.com/mcodev31/libmsym/archive/refs/tags/v0.2.3.tar.gz

# 2) 设备原生验证（同一份源码，先行确认可编译可运行）
cmake -S <src> -B build -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DMSYM_BUILD_EXAMPLES=OFF \
  -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=<prefix>
cmake --build build -j2 && cmake --install build

# 3) 配方验证（干净缓存轮，与 CI 同路径）
conan create archives/l/libmsym/0.2.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2
```

安装产物：`lib/libmsym.a`（默认静态）、`include/libmsym/{msym.h,msym_error.h,msym_EXPORTS.h}`、
`lib/cmake/libmsym/*`（上游自带 config）；`MSYM_BUILD_EXAMPLES=OFF` 时不安装 examples。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 直接失败（CMake 4.x） | 上游 `cmake_minimum_required(VERSION 2.8.11)`，CMake 4.x 移除了 <3.5 兼容分支 | recipe 在 `build()` 的 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`（configure 命令行缓存变量）传入；**不能**写进 `CMakeToolchain` 文件（对首行策略检查不可达）。未改上游源码 |
| 2 | lang-preflight 报 `mixed` → `env_unsupported` | 工具在**全树文件名集合**上匹配 manifest，`bindings/python/setup.py` 命中 python 分支，与 C 主体 87% 冲突 | 该 Python 绑定目录属 R47 明列的「语言绑定目录」；排除后同一源码重跑：`cmake` + C 源 20 个（占比 100%），judgement `c`（与任务 `cpp` 同兼容族）。命令与输出见本文「验证结果」段 |
| 3 | 交付库自报版本是 0.2.2 而非 0.2.3 | 上游 v0.2.3 tag 内 `CMakeLists.txt` 的 `LIBMSYM_PATCH_VERSION` 仍是 2（tag 未同步版本号），`libmsymConfigVersion.cmake` 由它生成 | 不改上游源码（属上游事实）；配方/包目录版本按上游 tag 取 0.2.3，`conandata.yml` 固定 tag commit 5b7aa16e。此处已留档，不视为适配缺陷 |
| 4 | 点群轴阶数断言与直觉不符 | `msymGetPointGroupType` 的 `n` 是**最高阶真转动**阶数：Td 的主转动是 C3，故 `n=3`（不是 0） | 以点群理论为准修正测试期望（Td → n=3），未改库行为 |
| 5 | `shared=True` 变体的 `.so` 无 `DT_SONAME` | OHOS 无 CMake `Platform/HarmonyOS.cmake` → `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空；上游虽设 `VERSION`/`SOVERSION` 也不生效 | recipe 在 `os == "OHOS"` 时 `tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"]="TRUE"` + `tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"]="-Wl,-soname,"`；实测 `readelf -d` 由无 SONAME 变为 `SONAME libmsym.so`。默认静态交付面不受影响 |

## 源码修改

无补丁（`patches: {}`，`patches_applied: []`）。上游源码按 tag v0.2.3 原样构建，
CMake 4.x 兼容开关通过 recipe 的 `CMAKE_POLICY_VERSION_MINIMUM` 注入，不落源码补丁。

## 依赖版本

无外部依赖；`conan install --build=never` 对空依赖集成立（按工作区口径写 `none`）。
系统库：`libm`（recipe `cpp_info.system_libs = ["m"]`，与上游 `target_link_libraries(msym m)` 对齐）。

## 验证结果

上游测试：**无任何测试入口**（N=0）——tag v0.2.3 源码树只有 `src/` 与 `examples/`，
顶层 `CMakeLists.txt` 无 `enable_testing()`/`CTest`/`add_test`，仓库无 `test/` 目录，
`pre-scan` 亦报告 `有测试: False`。因此上游通过率写 `0/0（不适用——上游 0 个可运行测试入口）`。

适配后消费者测试（`test_package/test_libmsym.c`，鸿蒙侧新增）：

```sh
# 设备原生（同一源码 + 同一头文件/库，先于 conan create）
clang -std=c99 -Wall -I<prefix>/include test_libmsym.c -o test -L<prefix>/lib -lmsym -lm
./test
# assertions: 92 passed, 0 failed
# libmsym consumer test: ALL PASS
```

问题 2（语言预检）的重跑命令与输出（排除语言绑定目录 `bindings/` 后用同一源码）：

```sh
cd "$TARGET_REPO" && python3 scripts/ohc-run.py lang-preflight libmsym 0.2.3 \
  --src <排除 bindings/ 的源码副本> --project-dir "$TARGET_REPO"
# ✅ 语言匹配: task=cpp, detected=c
# build_system=cmake, manifest=CMakeLists.txt, 源文件 20 个（c:20），主体占比 100%
```

断言覆盖 4 个标准几何（期望值来自分子点群理论，不取自本库输出）：

| 分子 | 点群 | 群阶 | 真转动/非真转动/反映/反演 | 特征标表维数 | 等价集 |
|------|------|------|---------------------------|--------------|--------|
| H2O | C2v (n=2) | 4 | 1/0/2/0 | 4 | {1,2} |
| NH3 | C3v (n=3) | 6 | 2/0/3/0 | 3 | {1,3} |
| CH4 | Td (n=3) | 24 | 11/6/6/0 | 5 | {1,4} |
| C6H6 | D6h (n=6) | 24 | 11/4/7/1 | 12 | {6,6} |

每个分子另断言 `msymCreateContext`/`msymSetElements`/`msymFindSymmetry`/
`msymGetPointGroupName`/`msymGetSubgroups`/`msymGetRadius`/`msymGetDefaultThresholds`/
`msymReleaseContext` 的返回码与结果，合计 92 项断言（4×23）。

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libmsym.a` | 静态库（默认 `shared=False`；`shared=True` 时产出 `libmsym.so`） |
| `include/libmsym/msym.h`、`msym_error.h`、`msym_EXPORTS.h` | 公开头文件（`msym_EXPORTS.h` 由 CMake `generate_export_header` 生成） |
| `lib/cmake/libmsym/*.cmake` | 上游自带 CMake package config |

## 注意事项

- 本包为**纯库**（无 `bin/` 产物，examples 不安装），故不需要 `commands.json`。
- 上游 `bindings/python/` 是**独立 `setup.py`** 的 Python 绑定（上游无 `MSYM_BUILD_PYTHON` 之类 CMake 选项，
  全树 grep 无此符号），默认不构建，不在本次 C 库适配面内。
- 该库的 `msymFindSymmetry` 对**精确对称**几何最稳；测试几何取自标准键长/键角
  （水 O-H 0.9575 Å/104.5°、氨 N-H 1.0124 Å/106.7°、甲烷 1.089 Å、苯 C-C 1.397 Å/C-H 1.084 Å），
  未放宽默认阈值。

## 发现与知识

- ✅ CMake 4.x 移除了 `cmake_minimum_required(<3.5)` 的兼容分支：`CMAKE_POLICY_VERSION_MINIMUM=3.5`
  必须在 `cmake.configure(variables=...)`（configure 命令行缓存变量）上给；写进 `CMakeToolchain`
  文件对上游 CMakeLists 首行的策略检查不可达（本机 cmake 4.1.2 实测；知识条目 E187）。
- ✅ CMake 目标平台识别由 Conan `CMakeToolchain`（`os=OHOS`）解决；G0 命中的 E092「CMake 不认识
  HarmonyOS」对已有工具链的配方**不适用**，仅作提示，不构成配方缺陷（本轮 G2 实证 PASS；知识条目 E092）。
- ✅ 上游 tag v0.2.3 内 `CMakeLists.txt` 的 `LIBMSYM_PATCH_VERSION` 仍是 2：产物 SONAME 与
  `libmsymConfigVersion.cmake` 自报 0.2.2（tag 未同步版本号），属上游事实，未打补丁改写上游源码。
- ✅ `msymGetPointGroupType` 返回的 `n` 是最高阶真转动阶数：Td 的主转动是 C3，故 `n=3`（不是 0）；
  Cnv/Dnh 则为主轴阶数。断言期望值按点群理论写，不按库输出反推。
- ✅ OHOS 目标在 CMake 中**没有** `Platform/HarmonyOS.cmake`，`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`
  为空：即使上游设了 `VERSION`/`SOVERSION`，shared 产物也没有 `DT_SONAME`。配方侧显式补
  `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` + `-Wl,-soname,` 后 `readelf -d` 实测
  `SONAME libmsym.so`（知识条目 E383；同族先例 DRAFT-libharu-2.3.0-missing-dt-soname）。
