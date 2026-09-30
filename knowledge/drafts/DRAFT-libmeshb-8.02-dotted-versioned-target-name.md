# DRAFT-libmeshb-8.02-dotted-versioned-target-name

**来源**: libMeshb 8.02 适配 HarmonyOS PC（7.80 → 8.02 升级复验）
**路径**: Path B（知识库扩展）| **状态**: 草稿（待审核 promote）

## 问题

CMake 库目标名内嵌主版本号且带点号：

```cmake
add_library(Meshb.8 libmeshb8.c ../utilities/libmeshb8_helpers.c)
```

产物为 `libMeshb.8.a`。Conan 配方生成器按包名（libmeshb）猜 libs 名会猜错，
链接器无法解析 `-lMeshb.8`；公开头文件 `libmeshb8.h` / `libmeshb8.ins` /
`libmeshb8_helpers.h` 同样内嵌主版本号。版本升级（7.80 → 8.02）时目标名与
头文件全部联动改名（`Meshb.7`→`Meshb.8`、`libmeshb7.h`→`libmeshb8.h`），
打包 copy 与 `cpp_info.libs` 必须逐项同步，否则打包缺头或缺库。

## 根因

上游将主版本号直接编码进 CMake 目标名与公开头文件名（版本化命名策略），
Conan 自动推导按包名猜测，与上游实际命名脱节。

## 方案

1. 显式 `cpp_info.libs = ["Meshb.8"]`（跟随目标名，点号原样保留，`-lMeshb.8`
   可被链接器解析）。
2. `package()` 按上游实际头文件名 copy（`libmeshb8.h`、`libmeshb8.ins`、
   `libmeshb8_helpers.h` → `include/`），不调用 `cmake.install()` 避免示例
   二进制进入库包。
3. 版本升级时先 diff 上游 `sources/CMakeLists.txt` 的 `add_library` 目标名与
   公开头文件名，联动更新 `libs` 与 copy 源。
4. test_package 消费者用 `find_package(libmeshb)` 真实编译、链接、运行验证
   （CMakeDeps 导出 target 为 `libmeshb::libmeshb`，与带点号库文件名不冲突）。

## 验证

- libMeshb 8.02 OHOS aarch64：`cpp_info.libs=["Meshb.8"]`，conan create 成功；
  test_package 消费者 `test_libmeshb_consumer` 9/9 checks passed、
  `test_libmeshb_ohos` 22/22 checks passed。
- 先例：7.80（`Meshb.7`）同构验证成功，证明该模式随版本迁移。

## 适用边界

- 适用：CMake 静态库目标名/公开头文件名内嵌主版本号的 C/C++ 库；
  Meshb 系列（Mmg/ParMmg 同族）与同类版本化命名库。
- 不适用：目标名与包名一致且不含版本号的库（如 zlib）；共享库 SONAME 含
  版本号但目标名不含时走 E537 系规则。

## 关系

- `similar_to`: E221（部分相关）、E478（dotted version 包 ID，相关但不同）
- `caused_by`: 上游将主版本号编码进 CMake 目标名与公开头文件名
- `prerequisite_of`: 消费者通过 CMakeDeps 导出 target 链接带点号库
