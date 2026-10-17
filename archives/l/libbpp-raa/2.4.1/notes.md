# libbpp-raa 2.4.1 适配笔记

## 编译环境
- 构建系统：cmake；编译器 clang/clang++ 15.0.4
- 状态：built（本地交叉编译验证；无上游测试，消费者断言由 test_package 提供）
- 上游：https://github.com/BioPP/bpp-raa ，tag v2.4.1
  （sha256 21ed87b5c0c80f5b1632493127b30a77ae92ac0853985c048f31bed5fd0fb301）
- 依赖：libbpp-seq/2.4.1（已发布，合并 bpp-core）、zlib/1.3.1.1（OHOS -fPIC 重建版）

## 与同族的关系

本包是 Bio++ 家族 `bpp-core → bpp-seq → bpp-raa` 链上只依赖 bpp-seq 的一环，
配方骨架直接复用 `archives/l/libbpp-phyl/2.4.1`（同族先例 + E543 知识条），
差异仅三处：

1. **多了一个 zlib 依赖**（`find_package(ZLIB REQUIRED)`），并需要一个 portability 补丁
   （裸 `zlib` 目标名 → `ZLIB::ZLIB`）。
2. **上游没有任何测试目标**，因此不做 ctest 执行，MANIFEST 声明
   `upstream_test_in_build: false`（gtkspell3 同类的"上游无测试"处理）。
3. 公开 API 几乎全是数据库驱动，test_package 只能做"链接级 + 静态常量"冒烟。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `target_link_libraries(... zlib)` 会展开成 `-lzlib` 链接失败 | 上游把 zlib 写成裸目标名；CMake FindZLIB 只创建 `ZLIB::ZLIB` | portability 补丁：`zlib` → `ZLIB::ZLIB`（static 与 shared 两处） |
| 2 | `find_package(ZLIB)` 找不到 conan zlib | CMake 内置 FindZLIB 模块按系统路径找 | `ZLIB_ROOT` / `ZLIB_INCLUDE_DIR` / `ZLIB_LIBRARY` 指到 conan zlib 包 |
| 3 | 交叉编译静默产出 x86-64 | 上游 `set(CMAKE_CXX_FLAGS …)` 覆盖 --target（见 E543） | `CMAKE_<LANG>_COMPILER_TARGET` / `CMAKE_SYSROOT` 注入 |
| 4 | `find_package(bpp-seq)` 报 `references the file ... libbpp-core.so` 不存在 | libbpp-seq 包裁了 .so 但保留指向它的 CMake 导出 | 构建内 shim：复制依赖包、剔除 shared 目标（同 libbpp-phyl） |

## 验证结果

- 本地交叉编译（x86_64 → OHOS aarch64）：构建通过
- 产物架构：`libbpp-raa.a` 成员 = `ARM aarch64`
- test_package：3 项断言（RaaList 静态常量 ×3 + 默认构造），执行由官方 CI 给出
