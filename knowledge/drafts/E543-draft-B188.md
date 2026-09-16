# E543 — PREFER_CONFIG=ON 使 exiv2 静态闭包的 EXPAT::EXPAT 解析失败

## 错误特征

cmake configure 完成、进入 generate 阶段时报：

```
CMake Error at <exiv2-package>/lib/cmake/exiv2/exiv2Targets.cmake:61 (set_target_properties):
  The link interface of target "Exiv2::exiv2lib" contains:

    EXPAT::EXPAT

  but the target was not found.  Possible reasons include:
    * There is a typo in the target name.
    * A find_package call is missing for an IMPORTED target.
    * An ALIAS target is missing.
```

configure 阶段的 `find_package(exiv2 REQUIRED CONFIG)` 本身是通过的（`-- The following REQUIRED packages have been found: exiv2`），所以报错点看起来与 exiv2 无关，容易被误判为 exiv2 包损坏。ZLIB 一般不会报同类错误（模块模式 FindZLIB 仍会兜底创建 `ZLIB::ZLIB`）。

## 触发条件

- 构建系统: cmake（Conan 2，配方自带 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`）
- 依赖: exiv2/0.28.x 静态库（`EXIV2_ENABLE_XMP=ON` → `find_dependency(EXPAT REQUIRED)`）
- 阶段: configuration（generate）

## 根因分析

1. exiv2 包的 `exiv2Config.cmake` 导出 `Exiv2::exiv2lib`，其 `INTERFACE_LINK_LIBRARIES` 为
   `$<LINK_ONLY:EXPAT::EXPAT>;$<LINK_ONLY:ZLIB::ZLIB>`（大写命名空间，来自上游 exiv2 的模板）。
2. 这两个名字**只有 CMake 模块模式**的 `FindEXPAT`/`FindZLIB` 会创建（`if(NOT TARGET EXPAT::EXPAT) add_library(EXPAT::EXPAT UNKNOWN IMPORTED)`）。
3. Conan 的 expat 包安装的是上游 `expat-config.cmake`，它只定义 `expat::expat`（小写）。
4. `find_dependency(EXPAT REQUIRED)` 内部就是 `find_package(EXPAT REQUIRED)`，**不带 CONFIG/MODULE 参数**，
   因此搜索模式由 `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 决定：
   - 该变量为 ON → 先 CONFIG → 命中 `expat-config.cmake` → 成功找到但**只创建 `expat::expat`**，
     `EXPAT::EXPAT` 始终不存在 → generate 阶段报错。
   - 该变量未设置 → 先 MODULE → 命中 CMake 自带 `FindEXPAT` → 创建 `EXPAT::EXPAT` → 正常。

## 解决方案

### 推荐方案

**不设置** `CMAKE_FIND_PACKAGE_PREFER_CONFIG`（删除 `conan_cmakedeps_paths.cmake` 里的 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`）。
上游里需要 CONFIG 模式的调用都显式写了模式（`find_package(Qt6 ... NO_MODULE)`、`find_package(exiv2 REQUIRED CONFIG)`、
`find_package(ECM ... CONFIG)`），不受影响。

### 回退方案

必须保留 PREFER_CONFIG=ON 时，在 toolchain 注入的 cmake 片段里按 conan expat 包预定义：

```cmake
if(NOT TARGET EXPAT::EXPAT)
  add_library(EXPAT::EXPAT UNKNOWN IMPORTED)
  set_target_properties(EXPAT::EXPAT PROPERTIES IMPORTED_LOCATION "<expat-package>/lib/libexpat.so")
endif()
```

（kfilemetadata 6.28.0 采用该路径。）

### 禁止做法

- ❌ 修改 exiv2 包内的 `exiv2Config.cmake` / 删除其 `find_dependency`：越权修改依赖包产物，且丢失 expat/zlib 传递依赖信息。

## 验证

```bash
# configure 日志中不应再出现：
grep -n 'EXPAT::EXPAT but the target was not found' <build>/cmake-configure.log && echo "仍失败"
# 保留 PREFER_CONFIG=ON 的回退路径可确认片段已生效：
grep -n 'EXPAT::EXPAT' <build>/generators/conan_cmakedeps_paths.cmake
```

## 关联条目

- 相似: [E473]（同为 `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 导致的 imported target 名不一致）
