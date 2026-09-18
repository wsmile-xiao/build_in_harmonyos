# DRAFT: OHOS 上 CMake UNIX 变量为假导致逻辑门控特性关闭（-DUNIX=ON 恢复）

> 对应 `.kv`: `DRAFT-opentracing-cpp-1.5.1-cmake-not-unix-logic-gate-option-invalid.kv`
> 来源: opentracing-cpp 1.5.1（pc1-29, 2026-09-16）· 路径 B 知识草稿

## 问题现象

在 HarmonyOS PC (aarch64) 上配置 opentracing-cpp 1.5.1：

```bash
cmake .. -DBUILD_DYNAMIC_LOADING=ON ...
```

配置成功但输出 `Building without dynamic loading support.`，`make` 后
`dynamic_load_test`、`multiple_tracer_link_test` 两个测试目标**未生成**，
`ctest -N` 只注册 9 项（缺这 2 项）。

## 根因

1. HarmonyOS/OHOS 没有 CMake Platform module（configure 时打印
   `System is unknown to cmake`），CMake 内置变量 `UNIX` 为 **假**。
2. 上游用**运行时逻辑门控**而非 option 默认值门控：

   ```cmake
   option(BUILD_DYNAMIC_LOADING "Build with dynamic loading support" ON)
   if (BUILD_DYNAMIC_LOADING)
     if (NOT WIN32)
       if (NOT SUPPORTS_WEAK_SYMBOLS OR NOT UNIX)   # OHOS: NOT UNIX == TRUE
         set(BUILD_DYNAMIC_LOADING OFF)             # ← 覆盖命令行 -D 值
       endif()
     endif()
   endif()
   ```

3. `set(BUILD_DYNAMIC_LOADING OFF)` 在 configure 后期把命令行
   `-DBUILD_DYNAMIC_LOADING=ON` **直接覆盖**——传 option 无效。
4. 该 option 同时控制 `add_subdirectory(test)` 内两个测试入口的注册，
   因此测试入口未实例化（ctest -N 缺项）。

## 解决方案

```bash
cmake -DUNIX=ON -DBUILD_DYNAMIC_LOADING=ON ...   # 置真 CMake 内置 UNIX 变量
```

`-DUNIX=ON` 令门控整体 `(NOT SUPPORTS_WEAK_SYMBOLS OR NOT UNIX)` 为假，
option 保持 ON，两个测试入口恢复实例化。复跑后 `ctest -N` 注册 9→11 项。

> 注意：这是**逻辑门控**形态；若上游是 option **默认值**门控
> （`if(UNIX OR MINGW) option(X ON)`），直接 `-D<OPT>=ON` 即可，无需 `-DUNIX=ON`
> （见 E555-draft-9C21）。

## 验证证据（opentracing-cpp 1.5.1, pc1-29）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1 | `cmake .. -DBUILD_DYNAMIC_LOADING=ON` | `Building without dynamic loading support.`；make 后无两个测试二进制 |
| 2 | `cmake .. -DUNIX=ON -DBUILD_DYNAMIC_LOADING=ON` | 门控为假，option 保持 ON；make 生成 dynamic_load_test / multiple_tracer_link_test |
| 3 | `ctest --output-on-failure` | 11/11 Passed（0 failed）；dynamic_load_test 16 assertions、multiple_tracer_link_test 链接断言通过 |
| 4 | 运行期相对 NEEDED 恢复 | `.build/mocktracer/output`、`.build/example/output` 建 libopentracing.so 符号链接 + `LD_LIBRARY_PATH=build/output`（同 DRAFT-libjpeg-turbo） |

## 适用范围

- 上游 CMake 用 `if (NOT ... OR NOT UNIX)` / `if (NOT UNIX)` 逻辑门控包裹
  平台特性、示例或测试入口的 C/C++ 库；
- OHOS/HarmonyOS 交叉编译（无 CMake Platform module，UNIX 变量为假）；
- 特征: 传 `-D<OPT>=ON` 后 configure 仍输出 "Building without ..." 或 option 仍为 OFF。

## 反例 / 边界

- option 默认值门控（E555 形态）不需要 `-DUNIX=ON`，直接 `-D<OPT>=ON`；
- 非门控场景勿滥用 `-DUNIX=ON`——可能触发上游 Unix 专用代码路径导致意外编译错误；
- 门控放行后若再遇斜杠相对 NEEDED 运行时解析失败，按
  DRAFT-libjpeg-turbo-3.0.4-slash-relative-NEEDED-ctest-loading 处理。

## 查重关系

- similar_to: E555-draft-9C21（UNIX 变量为假/平台门控，option 默认值形态）、
  E375（NOT UNIX/WIN32 capability 选择）、DRAFT-itsy_bitsy（CMAKE_SYSTEM_NAME=Linux 进 Unix 分支）
- caused_by: OHOS 无 CMake Platform module（同 E092/E140/E267 根因）
- 新增差异: 门控形态区分（逻辑 vs 默认值）+ `-DUNIX=ON` 置真内置变量 + 测试入口恢复实例化联动
