# DRAFT-21002: CMake 库（library.cmake 风格）上游零 install() 规则 → 最小补丁补全 install 规则

- **来源**：lwjson 1.9.0 适配（2026-10-04，PR 待定）
- **关联 PR**：【知识库扩展】feat(lwjson): 1.9.0 适配 HarmonyOS PC
- **前置/相邻条目**：E309（直拷源码漏掉构建阶段生成的公共头）、E217（头装到
  include/<subdir> 的 includedirs 对齐）

## 问题（一类）

嵌入式/单文件风格的 CMake C 库（MaJerle 系 `library.cmake` 模式）只
`add_library()` 注册 target，**整个工程没有任何 `install()` 规则**。此时：

1. 配方 `package()` 用 `cmake.install()` → 安装空目录（G4 产物缺失 /
   test_package 找不到头/库）；
2. 配方用手工 `copy()` 打包 → 容易漏文件，且与上游真实安装布局脱节；
3. **隐蔽陷阱**：用户配置头（如 `lwjson_opts.h`）由 `configure_file(模板, 构建目录,
   COPYONLY)` 生成，而公开头（`lwjson_opt.h`）`#include "lwjson_opts.h"`——
   即使补了 `install(TARGETS)` 和 `install(DIRECTORY src/include/)`，漏掉
   `install(FILES <构建目录>/.../lwjson_opts.h)` 仍会让消费者 `fatal error`。

## 方案（最小补丁 + 工具化打包）

在库的 CMakeLists/library.cmake 末尾追加（无平台宏，portability 类补丁）：

```cmake
include(GNUInstallDirs)
install(TARGETS lwjson lwjson_debug
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/src/include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES ${LWJSON_CUSTOM_INC_DIR}/lwjson_opts.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/lwjson)
```

配方 `package()` 用 `cmake.install()`；`test_package` 消费者必须实际 `#include`
公开头、编译、链接、运行（不是只查文件存在）。

## 验证（lwjson 1.9.0 实测）

- 补丁后 `cmake --install` → `lib/liblwjson.a`、`lib/liblwjson_debug.a`、
  `include/lwjson/*.h`（含生成的 `lwjson_opts.h`）全部就位；
- `conan-verify` G1-G4 + L2/L4/L5 全通过；`conan create` 内 build() ctest 1/1、
  test_package 2/2（消费者 + 鸿蒙专项）通过；
- 消费者（test.c）解析业务 JSON：`lwjson_init/parse/find` + 类型化取值 +
  数组遍历，退出码 0。

## 适用边界

- 适用于 CMake 工程零 install 规则或规则不全的静态库；header-only 库（INTERFACE）
  走 E322 模板；系统同名共享库走 R26 静态化。
- 反例：上游已有完整 install 规则时不需要此补丁；纯 Makefile 工程见 binn 配方。

## 与既有知识的关系（七轴查重）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否（无同主题官方条目） |
| causal_duplicate | 否 |
| trigger_overlap | E309 同源（生成头漏装），但 E309 场景是"手工 copy 配方"，本条是"补全 install 规则"配方路径 |
| solution_overlap | 部分（E309 的 run-upstream-configure / 复现生成头；本条直接 install(FILES 生成头)） |
| combination_novelty | 有：install(TARGETS/DIRECTORY/FILES) 三件套 + 生成头一并安装的完整最小补丁模式 |
| boundary_novelty | 有：零 install 规则工程的判别（grep install() 为空）+ 生成配置头依赖链（公开头 include 生成头） |
| test_migration_novelty | 有：消费者必须编译链接运行验证（R34 落地示例） |

**决策**：new_draft（DRAFT-21002）——既有 E309/E217 仅部分覆盖，新增差异已由
lwjson 真实日志验证且可跨库复用。
