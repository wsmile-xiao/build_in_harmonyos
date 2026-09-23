# DRAFT — CMake PUBLIC_HEADER 拍平安装导致 test_package 找不到规范 include 子路径

- **草稿 ID**: DRAFT-btor2tools-1.0.2-git20250918.d33c73f-cmake-public-header-flatten
- **触发事件**: btor2tools 1.0.2-git20250918.d33c73f HarmonyOS PC 适配（archives/b/btor2tools/1.0.2-git20250918.d33c73f）
- **Gate**: conan-verify G2（test_package 编译阶段）

## 问题

上游 CMake 用 `set_target_properties(btor2parser PROPERTIES PUBLIC_HEADER btor2parser/btor2parser.h)` +
`install(TARGETS btor2parser PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})` 安装头文件。
CMake 的 PUBLIC_HEADER 安装会**丢弃相对子目录**，将 `btor2parser/btor2parser.h` 拍平成
`include/btor2parser.h`。而消费者（test_package 与真实下游）按上游源码规范
`#include "btor2parser/btor2parser.h"` 引用，包内 `include/` 下不存在 `btor2parser/` 子目录
→ test_package 编译报 `fatal error: 'btor2parser/btor2parser.h' file not found`。
`conanfile.py` 的 `includedirs` 默认 `["include"]` 无法补救——缺口在包内目录结构本身。

## 根因

CMake `PUBLIC_HEADER` 安装语义是"把列出的头文件安装到指定 DESTINATION，文件名取 basename，
不保留相对路径"。上游库常把 `x/x.h` 写进 PUBLIC_HEADER（源码内以 `x/x.h` include），
安装后结构变成 `include/x.h`，与消费者 include 路径不一致。

## 方案

在上游 `CMakeLists.txt` 的 PUBLIC_HEADER install 之外追加：

```cmake
install(FILES btor2parser/btor2parser.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/btor2parser)
```

显式把头文件装回规范子目录，保持消费者 include 路径与上游源码一致。用
`refresh-patch --auto` 落成 `patches/*.patch` 并在 `conandata.yml` patches 列表登记。

备选（配方级，不通用）：conanfile `package()` 内 `cmake.install()` 之后把
`include/<name>.h` 移动到 `include/<name>/<name>.h`。

## 验证

- `conan-verify` G2 通过：test_package `find_package(btor2tools)` + `#include "btor2parser/btor2parser.h"` 编译链接成功
- `tar -tzf packaging/*.tar.gz` 确认 `include/btor2parser/btor2parser.h` 存在
- 包缓存 `p/include/` 下存在 `btor2parser/btor2parser.h`（而非仅 `btor2parser.h`）

## 适用边界

- 上游用 PUBLIC_HEADER 安装带相对路径头文件的 CMake 库（GNUInstallDirs 场景）
- 消费者按上游源码子路径 include（`x/x.h`）
- 在 OHOS Conan 2（CMakeToolchain/CMakeDeps）下适配时

## 反例与限制

- **禁止**只改 test_package include 为 basename 绕过：真实下游仍失败，包内结构偏离上游规范
- **禁止**删除 PUBLIC_HEADER 行或清理 include 产物：破坏安装完整性
- 若上游同时存在多个子路径头文件，需逐条追加 install(FILES) 或改 install(DIRECTORY)

## 查重差异

- 与 E217（上游 install(FILES ... DESTINATION include/<subdir>) 但 includedirs 未指向子目录）同症状
  （test_package header not found）但根因相反：E217 是头已在子目录而配方 includedirs 缺；
  本条目是 PUBLIC_HEADER 拍平导致子目录缺失，修复在 source 补丁而非 package_info。
- 与 E309（generated public header 安装）无关：本条目不涉及 configure_file 生成头。

## 字段一致性

- `.kv` 与 `.md` 同 stem，`doc_file` 指向配对 md，id/error_signature/root_cause/rec_approach 均已填写。
