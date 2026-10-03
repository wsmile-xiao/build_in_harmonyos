# DRAFT-E5xx：ODBC 消费库交叉构建探测链改造模式

- **软件**：nanodbc 2.14.0（C++ ODBC 轻量封装库，MIT，cmake）
- **类别**：平台差异（OHOS 交叉构建 + CMake 探测链宿主专用）
- **error_signature**（可机器匹配）：`can not find a suitable odbc driver manager` / `Could NOT find ODBC_CONFIG` / `find_path.*uodbc_stats` / `iodbc-config`
- **状态**：draft（待主编定稿编号）

## 错误特征

OHOS aarch64 交叉构建 ODBC 消费库（nanodbc 2.14.0）时，CMake configure 直接 FATAL_ERROR：

```
CMake Error: can not find a suitable odbc driver manager
```

或探测三连全落空后变量为空导致链接失败。

## 根因（双坑叠加）

1. **上游探测链宿主专用**：nanodbc 顶层 CMakeLists 的探测序是
   `find_program(ODBC_CONFIG odbc_config)` → `find_path(UnixODBC_INCLUDE_DIR uodbc_stats.h)`
   → `find_program(ODBC_CONFIG iodbc-config)`。三者全部在**构建宿主**的
   PATH/系统目录里找：交叉构建环境下宿主没有 odbc_config（或即使有，产出的
   也是宿主路径，不可用于目标），探测必然落空 → `if(NOT ODBC_CONFIG)` 触发
   FATAL_ERROR。
2. **HarmonyOS 不定义 UNIX 变量**（更隐蔽的坑）：OHOS 适配版 conan 把
   `CMAKE_SYSTEM_NAME` 映射为 `HarmonyOS`，而 CMake 只对 Linux/Darwin/BSD 等
   定义 `UNIX`——`if(UNIX)` 守卫的探测块、链接库选择块（`set(ODBC_LIBRARIES
   ${ODBCLIB})`）、目标属性块（COMPILE_FLAGS/LIBRARY_OUTPUT_DIRECTORY）**整块
   静默跳过**，不报错但变量全空，后续链接报一堆 undefined symbol 或空库。

## 方案（显式注入 + 守卫扩展，四步）

1. **conanfile generate() 注入显式路径**（不动 patch 也能过 configure 的钥匙）：
   ```python
   dep = self.dependencies["unixodbc"]
   tc.variables["ODBC_INCLUDE_DIR"] = os.path.join(dep.package_folder, "include")
   tc.variables["ODBC_LIBRARY"] = self._odbc_library(dep)  # libodbc.so 全路径
   ```
2. **patch：探测链前插显式分支**：
   ```cmake
   if(ODBC_INCLUDE_DIR AND ODBC_LIBRARY)
     set(ODBCLIB "${ODBC_LIBRARY}")
     set(ODBC_CONFIG 1)   # 使后续 if(NOT ODBC_CONFIG) 守卫不触发
     set(ODBC_CFLAGS "-I${ODBC_INCLUDE_DIR}")
     get_filename_component(ODBC_LIB_DIR "${ODBC_LIBRARY}" DIRECTORY)
     set(ODBC_LINK_FLAGS "-L${ODBC_LIB_DIR} -lodbc")
   elseif(UNIX)
     ...上游原探测链...
   ```
3. **全文件 if(UNIX) 守卫同步扩展**为
   `if(UNIX OR (ODBC_INCLUDE_DIR AND ODBC_LIBRARY))`（探测/链接/属性三处，
   grep `if(UNIX` 逐一核对，漏一处就有静默空变量）。
4. `cmake_minimum_required(3.0.0)` → `3.10`（CMake 4.x 拒绝 <3.5，同场景必改）。

## 验证

nanodbc/2.14.0 本机 conan create 全链绿（ohos-aarch64 profile）：
- 库本体 libnanodbc.a + include/nanodbc/nanodbc.h + nanodbc-config.cmake 产出
- 上游 utility_test 真跑 7/7 断言（源码树同款 patch 配置构建）
- test_package 消费者冒烟 9 断言（find_package(nanodbc CONFIG) + 离线 API 面）

## 可迁移面

任何经 `odbc_config`/`iodbc-config`/`find_path(uodbc_stats.h)` 探测驱动管理器的
CMake 库（libdbi、squirrel、qtbase 的 sqlodbc 插件等）；更一般地，任何
"宿主专用探测程序 + if(UNIX) 守卫"组合的交叉构建失败都适用同款
"显式 cache 变量注入 + 守卫扩展"修法。
