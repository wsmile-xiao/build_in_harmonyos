# CMake 4 不再提供 FindBoost：旧式 Boost 变量须由配方补齐

- **草稿 ID**: DRAFT-SCHROOT-1613-CMAKE4-FINDBOOST
- **条目文件**: `knowledge/drafts/schroot-1.6.13-cmake4-no-findboost.kv`
- **来源事件**: schroot 1.6.13 configure/编译阶段（2026-10-01）
- **严重程度**: 🟡 medium

## 1. 现象

上游 CMakeLists 使用 `find_package(Boost ...)` 后读取**旧式变量**
（`${Boost_INCLUDE_DIRS}`、`${Boost_LIBRARIES}`、`Boost_<COMPONENT>_LIBRARY_RELEASE`），
在 CMake 4 + 交叉编译（conan 提供 Boost）环境下失败：

```
Could NOT find Boost (missing: Boost_INCLUDE_DIRS) ...
或后续编译：fatal error: 'boost/…' file not found
```

## 2. 根因

CMake 4 **移除了 `FindBoost` 模块**：Boost 只能通过 `BoostConfig.cmake`（CONFIG 模式）被发现。
BoostConfig 只定义 **imported target**（`Boost::filesystem` 等），
**不设置**旧式变量 `Boost_INCLUDE_DIRS` / `Boost_LIBRARIES` / `Boost_<COMPONENT>_LIBRARY_RELEASE`。

上游若按旧式写法取变量（2016-2019 年代的常见写法），configure 阶段就拿不到头/库。
交叉编译下系统路径搜索被关闭，问题更突出。

## 3. 解决方案（配方侧，优先）

```python
tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
tc.cache_variables["BOOST_ROOT"] = boost_pkg            # BoostConfig 生效
tc.cache_variables["Boost_INCLUDE_DIRS"] = os.path.join(boost_pkg, "include")
tc.cache_variables["Boost_LIBRARY_DIRS"] = os.path.join(boost_pkg, "lib")
# 按组件实际产物逐个赋值（无 .a/.so 的组件不要赋值！）
tc.cache_variables["Boost_FILESYSTEM_LIBRARY_RELEASE"] = …/libboost_filesystem.a
tc.cache_variables["Boost_PROGRAM_OPTIONS_LIBRARY_RELEASE"] = …/libboost_program_options.a
```

并把 Boost 头/库目录通过工具链旗标注入（`extra_cflags` / `extra_cxxflags` /
`extra_exelinkflags` / `extra_sharedlinkflags`，**须为列表**），绕开上游找不到头的问题。

### ⚠️ boost ≥ 1.84 的坑

`boost_system` 在 boost ≥ 1.84 已是 **header-only**，制品仓的 boost 包里**没有**独立
`libboost_system.a/.so`。若在链接命令行给 `-lboost_system`，会得到
`cannot find -lboost_system`，把排查方向带偏。

正确做法：遍历组件时**只对实际存在的 `.a/.so` 赋值**，不存在的组件跳过。

## 4. 备选方案

若上游 CMakeLists 结构复杂、旧式变量散落多处，可打补丁改用 imported target
（`Boost::filesystem`），更现代也更稳；但需评估侵入面并在 notes.md 说明。
优先用配方变量，尽量不改上游。

## 5. 验证

```bash
cmake -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON -DBOOST_ROOT=<boost pkg> ...
grep -n "Boost_INCLUDE_DIRS" CMakeCache.txt      # 已赋值 = 配方注入生效
# 必须走到链接期验证（只 configure 通过不算数）
```

## 6. 适用范围

`find_package(Boost)` 且读旧式变量的上游项目；CMake ≥ 4 环境；交叉编译 + conan 依赖提供 Boost。
