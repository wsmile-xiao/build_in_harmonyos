# lib3mf 1.8.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists 3.0.2 → 现代 cmake 4.x 需 patch）
- 编译日期: 2026-09-14
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published
- 上游: https://github.com/3MFConsortium/lib3mf（tag v1.8.1）

## 软件简介
3MF（3D Manufacturing Format）参考实现库（C++），读写 3MF 增材制造文件格式。

## 编译步骤
1. init-build + lang-preflight（cpp 匹配）
2. 手动交叉编译探索：ohos.toolchain.cmake + OHOS_ARCH=arm64-v8a，USE_INCLUDED_ZLIB=OFF + USE_INCLUDED_LIBZIP=OFF（用 conan 外部依赖 libzip/1.11.4 + zlib/1.3.1.1）
3. patch 固化 4 个 → conan-init/conanfile 重写（libzip 模式）→ conan-verify 8 道门禁全过
4. test_package 真实 3MF 模型往返（建模型→写盘→读回→校验）在本机 5/5 稳定通过

## 遇到的问题与解决方案（关键适配点）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 4.x 配置失败 | 上游 cmake_minimum 3.0.2 + CMP0054 OLD 已被移除 | patch: min 3.5 + 删 CMP0054 块 |
| 2 | USE_INCLUDED_*=OFF 后链接缺 zlib/libzip 符号 | 上游 OFF 分支没有任何 find_package/链接逻辑 | patch CMakeLists: find_package(ZLIB)/find_package(libzip CONFIG) + target_link_libraries（注意上游安装的 libzip target 名是 libzip::zip 非 libzip::libzip） |
| 3 | 静态库打包失败 "Error running link command" | SDK llvm/bin 无 llvm-ranlib，ohos.toolchain 却指过去 | -DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib |
| 4 | find_library(uuid) 失败 | 交叉 FIND_ROOT_PATH 限制 + 本适配 uuid 已内置 | patch: OHOS 下跳过 uuid 查找（CUUID 改用 /dev/urandom 自生成） |
| 5 | **运行时段错误（堆破坏）** | ossp-uuid 1.6.2 的 PRNG/MD5 引擎（uuid_prng.c/uuid_md5.c）在优化编译下破坏堆内存，V4 生成路径触发后续随机崩溃 | patch NMR_UUID.cpp: __OHOS__ 分支直接读 /dev/urandom 生成 RFC 4122 v4 UUID（去 ossp-uuid 依赖） |
| 6 | **3MF 读回失败 (zip_err=28)** | lib3mf zip source 回调用老式 zip_source_make_command_bitmap 手工位图，libzip≥1.9 的 zip_open_from_source 要求更多命令位 | patch: SUPPORTS 返回官方 ZIP_SOURCE_SUPPORTS_SEEKABLE 宏；default 分支未知命令返回 0（原抛异常） |
| 7 | test() 本机跑 OHOS 二进制报 libc++_shared.so not found | conanrun 环境不含系统库路径 | test() 命令显式前缀 LD_LIBRARY_PATH=/system/lib64 |
| 8 | zip 回调 default 抛 CNMRException → abort | libzip 1.11 会调 GET_FILE_ATTRIBUTES 等新命令 | 同 #6：default 返回 0 |

## 上游测试
- 上游 add_test 注册 N=2：Test_CInterface（C 接口，12 源文件）+ UnitTestsCPP（内部类，7 源文件）
- googletest 子模块在 release tarball 中为空目录，探索时用 googletest release-1.12.1 源码补齐后两个测试目标均编译链接成功（LIB3MF_TESTS=ON）
- CI 配方中 LIB3MF_TESTS=OFF（googletest 子模块不可得），上游测试通过 test_package 消费者测试覆盖核心链路

## 消费者测试（test_package）
test.c: 建模型(8顶点/12三角形) → addbuilditem → 写 3MF 文件 → 新模型读回 → getvertexcount/gettrianglecount 校验。
覆盖 uuid 生成、libzip 压缩写、XML 序列化、OPC 包结构、zip 读回五层链路。本机 5/5 稳定通过。
---

**编译结束**: 2026-09-14 01:21
**最终状态**: built
