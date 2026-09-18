# DRAFT-400: CMakeDeps 多包同名 cmake_file_name 互覆盖致 DEPS_TARGET 断链

## 基本信息
- **严重度**: 2
- **类别**: packaging
- **作者**: calbee21 <calbee21@users.noreply.gitcode.com>
- **来源任务**: litecoin 0.21.4 适配（contrib-258）

## 错误特征
```
The link interface of target "X_DEPS_TARGET" contains:
  boost::boost
but the target was not found.
CMake Generate step failed.
```

## 根因分析
ohpcd 制品仓的 boost 体系拆为三个包：boost/1.84.0（主包，cmake_file_name="Boost"，组件 Boost::headers/filesystem/regex/...）、boost1.84-thread（抢注 cmake_file_name="Boost"，组件 Boost::thread）、boost1.84-system（cmake_file_name="boost_system_pkg"）。

CMakeDeps 对每个 conan 包按其 cmake_file_name 生成 `<name>-Target-release.cmake`。boost/1.84.0 与 boost1.84-thread 同名 "Boost" → 生成文件互相覆盖，最终 Boost-Target-release.cmake 只含 Boost::thread。

下游包（litecoin）若 package_info 用包级 `cpp_info.libs`（无 components），CMakeDeps 在下游的 `litecoin-Target-release.cmake` 里为每个直接依赖生成**包级默认 target**（`boost::boost`），该名字在任何生成文件中都不存在 → cmake Generating 失败。

## 推荐方案
1. **下游配方用 components**：`comp.requires` 引用依赖包的组件（`boost::boost_headers`、`boost1.84-thread::boost_thread`、`db::db_cxx` 等）——组件链展开不生成包级默认名。
2. **完整性检查**：conan 要求所有直接 requires 出现在某组件 requires 中，否则 `package_info()` 报 "The direct dependency 'boost' is not used by any '(cpp_info/components).requires'"。
3. **INTERFACE 占位**：被覆盖掉的组件 target（Boost::headers）在 test_package 的 CMakeLists.txt 里 `if(NOT TARGET Boost::headers) add_library(Boost::headers INTERFACE IMPORTED) endif()`（consumer 不实际使用它，空接口合法）。

## 验证/命令
```
conan create . -pr:h=... -pr:b=... --build=missing  # test_package cmake configure 过
grep "boost::boost" build/*/generators/*-Target-release.cmake  # 应无结果
```

## 已知实例
- litecoin 0.21.4（archives/l/litecoin/0.21.4）：依赖 boost 三包，package_info components + test_package INTERFACE 占位双管齐下后全绿。

## 关键词
cmake_file_name, CMakeDeps, DEPS_TARGET, target was not found, boost::boost, components, comp.requires, INTERFACE IMPORTED, 占位 target

---
