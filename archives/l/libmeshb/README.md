# libmeshb (libMeshb)

## 简介
libMeshb 是 INRIA Loïc Maréchal 维护的 Meshb.7 网格文件读写库，用于 .mesh/.meshb 格式（Mmg、ParMmg 等网格工具的基础 I/O 层）。

## OHOS 适配
- CMake 工程（LANGUAGES C），静态库目标 `Meshb.7`（产物 `libMeshb.7.a`）
- 保持上游默认：`WITH_GMF_AIO=OFF`（避免 rt/aio 依赖）、`WITH_GMF_CTEST=OFF`（release tarball 无 testing/ 目录）
- release tarball 中 `check_language(Fortran)` 在 OHOS 工具链下找不到 Fortran 编译器自动跳过，Fortran 示例不参与构建
- 上游无注册测试（无 testing/ 目录、examples 未注册 add_test），适配验证由 `test_package` 消费者测试承担：写 2 顶点+1 边网格并回读断言

## 依赖
- 无编译依赖（仅 libc/libm）

## 功能验证
```bash
conan create archives/l/libmeshb/7.80 -pr:h=ohos-aarch64
# test_package: test_libmeshb_consumer（Gmf 写读回环 + 断言）
```
