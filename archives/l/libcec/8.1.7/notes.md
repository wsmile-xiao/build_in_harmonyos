# libcec 8.1.7 适配笔记

## 编译环境
- 构建系统: cmake（init-build 由 URL 误判为 autotools，conan-init 需 CMake 模板）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤
1. `init-build libcec 8.1.7 --url=...`：ghfast 镜像下载官方 tag libcec-8.1.7 tarball
   （sha256 e4ac4d1d…），解压 .orig/.work 双轨
2. `lang-preflight`：源树含 src/cargo 绑定子目录（Cargo.toml）被工具误判 rust，
   按 R47 边界规则"绑定类包按主体语言判定"应判 cpp（根 CMakeLists.txt + 52 cpp 源）
3. 手动冒烟：`cmake -DDISABLE_BUILDINFO=ON -DCMAKE_BUILD_TYPE=Release`（必须
   DISABLE_BUILDINFO，否则 SetBuildInfo.cmake 的 `string(STRIP ${BUILD_USER})`
   因设备无 whoami 报 "sub-command STRIP requires two arguments"）→ make → install
4. 上游测试枚举：官方 tag 无 CTest/enable_testing/add_test、无 make check 目标；
   src/rust/tests（layout/safe_api/smoke）为 Cargo 绑定测试且 ENABLE_RUST_LIB=OFF
   默认不构建、设备无 cargo —— 独立上游 C++ 用例数 = 0
5. conan-init → 重写 CMake 配方（DISABLE_BUILDINFO=ON + CMAKE_SYSTEM_NAME=Linux）
6. test_package：test.c（消费者用例，公开 C API initialise/get_lib_info/destroy）+
   test_ohos.c（鸿蒙专项：版本宏断言 + detect_adapters 无适配器优雅返回）均真机 PASS
7. conan-verify：G0-G4/L2/L4/L5 全过（E017 镜像注入后恢复官方 URL）
8. finish published → built（知识 gap 警告 + test-report/packaging/.staging-verified 待补）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 string(STRIP) requires two arguments | OHOS 无 whoami，BUILD_USER 空 | -DDISABLE_BUILDINFO=ON |
| 2 | 下载 github.com 超时 | 设备侧 github 不可直连 | ghfast.top 镜像下载（conan-verify E017 自动注入后恢复） |
| 3 | make -j 报 jobserver mkfifo 失败 | ~/tmp HMDFS 不支持 FIFO | 串行 make（-j1） |
| 4 | cec-client 运行报找不到 libcec.so.8 | CMake 未生成版本化 SONAME | CMAKE_SYSTEM_NAME=Linux 生成 libcec.so.8 软链 |
| 5 | lang-preflight 判 rust | src/rust 绑定子目录 Cargo.toml 被当 manifest | 按边界规则判 cpp，工具子树扫描为误判 |

## 源码修改
无（纯配方适配，patches/ 为空）

## 依赖版本
无三方运行依赖（标准库 libc/libc++ 由 OHOS 提供）

## 验证结果
```bash
cec-client --version        # CEC Parser created - libCEC version 8.1.7
conan create ...            # ohpcd/stable, G0-G4/L2/L4/L5 PASS
test_libcec                 # PASS
test_libcec_ohos            # PASS
```
---

**编译结束**: 2026-09-16 22:30
**最终状态**: built
