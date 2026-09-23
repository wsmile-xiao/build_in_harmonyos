# DRAFT: Conan CMakeDeps 下上游 POP_FRONT CMAKE_MODULE_PATH 弹错目录导致 bundled 依赖配置崩溃

## 现象

启用 Apache Arrow 的 bundled thrift（`ARROW_PARQUET=ON` + `THRIFT_SOURCE=BUNDLED`）在 Conan `conan create` 下配置阶段崩溃：

```
-- Thrift: Building without tests
CMake Error at .../build/Release/_deps/thrift-src/CMakeLists.txt:134 (PRINT_CONFIG_SUMMARY):
  Unknown CMake command "PRINT_CONFIG_SUMMARY".
```

## 根因

两个叠加问题：

### ① POP_FRONT 弹错目录

- Conan CMakeToolchain 生成的 `conan_toolchain.cmake` 内有：
  `list(PREPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR})` —— generators 目录在**最前**，且先于上游任何 CMakeLists 执行
- Arrow `cpp/CMakeLists.txt` 随后 `list(PREPEND CMAKE_MODULE_PATH cmake_modules)`
- Arrow `build_thrift()` 想移除自己的模块路径让 thrift 用自带的：`list(POP_FRONT CMAKE_MODULE_PATH)`
- **实际弹出的是 conan generators 目录**——Arrow 的 `DefineOptions.cmake` 仍在路径上
- thrift 的 `include(DefineOptions)` 按查找顺序命中 **Arrow 的** DefineOptions.cmake（定义 `define_option` 系列宏，无 `PRINT_CONFIG_SUMMARY`）
- thrift CMakeLists 尾部 `PRINT_CONFIG_SUMMARY()` → Unknown CMake command → 配置失败

### ② SYSTEM boost 下 thrift 缺 boost include

- bundled thrift 头（TTransportException.h 等）include `boost/numeric/conversion/cast.hpp`
- Arrow 只在 `BOOST_VENDORED=TRUE` 时执行 `target_link_libraries(thrift PUBLIC Boost::headers)`
- `BOOST_SOURCE=SYSTEM`（Conan 预编译 boost）下 thrift 目标无 boost include → parquet 源码编译报 `file not found`

## 修复（fix_bundled_thrift_module_path.patch）

```cmake
# ① 按路径显式移除（ThirdpartyToolchain.cmake 自身所在目录即待移除条目）
-  list(POP_FRONT CMAKE_MODULE_PATH)
+  list(REMOVE_ITEM CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")

# ② SYSTEM boost 下补挂 Boost::headers
+  if(NOT BOOST_VENDORED AND TARGET Boost::headers)
+    target_link_libraries(thrift PUBLIC $<BUILD_LOCAL_INTERFACE:Boost::headers>)
+  endif()
```

## 打包要点（同场景必读）

1. bundled thrift 对象由 Arrow 聚合进 `libarrow_bundled_dependencies.a` 并随 install 分发——**不要**再手动拷贝 `libthrift.a` 进包（双重符号 → ODR 冲突 → 运行期 SIGSEGV）
2. thrift 公共头需随包分发（parquet 公共 API 头传递依赖 thrift 头）；生成的 `config.h` 在 `thrift-build/thrift/config.h`，须落到 `include/thrift/config.h`
3. 下载源用 `ARROW_THRIFT_URL` 环境变量固定到 `archive.apache.org`（上游默认 closer.lua/dlcdn 在受限环境不可达；archive.apache.org 与 apache 系源码包同域，CI 已验证可达）
4. thrift 0.22.0 要求 CMake >= 3.26（bundled 构建的硬检查）

## 适用范围

任何"上游 CMake 用 FetchContent 拉 bundled 依赖 + 依赖方 CMake 用 POP_FRONT 清理模块路径"的组合，在 Conan CMakeDeps 环境下都会踩 ①；任何"bundled 依赖头 include boost + BOOST_SOURCE=SYSTEM"会踩 ②。与具体库名无关（libparquet 实证，Arrow 家族全适用，其他 FetchContent 型上游同理）。

## 验证

- 本地 conan create 8 轮迭代（补丁前后对比日志 conan_create2 vs conan_create4+）
- 62 个上游测试目标全部构建成功，11227 gtest 用例执行
- parquet 专用 10 目标带 parquet-testing 数据 2150/2153 = 100%

## 五要素

- error_signature: `Unknown CMake command "PRINT_CONFIG_SUMMARY"` + `list(POP_FRONT CMAKE_MODULE_PATH)`
- root_cause: Conan generators 目录占据 CMAKE_MODULE_PATH 前端 → POP_FRONT 弹错目录 → bundled 依赖 include 命中错误的模块文件
- solution: 按路径 REMOVE_ITEM + SYSTEM boost 下补挂 Boost::headers（补丁全文见归档）
- fallback: THRIFT_SOURCE=AUTO + 系统 thrift / CMAKE_PREFIX_PATH；或禁用 ARROW_PARQUET
- verify_builds: 本地 conan create 全绿 + 62 测试目标构建

- 关联 PR: libparquet 23.0.1（feat/libparquet-23.0.1）
- 日期: 2026-09-17
- 作者: 2404_87638649
