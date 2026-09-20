# fbthrift 2020.08.24.00 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build fbthrift 2020.08.24.00 --url=https://github.com/facebook/fbthrift/archive/refs/tags/v2020.08.24.00.tar.gz`
2. `cd $BUILD_SRC_DIR && mkdir build && cd build`
3. `cmake -DCMAKE_SYSTEM_NAME=OHOS -DBUILD_TESTS=OFF -Dcompiler_only=ON -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX ..`
4. `make -j2 thrift1 && make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FindBoost 模块缺失 | cmake 4.1.2 移除了 FindBoost 模块 | 使用 find_package(Boost CONFIG) + Conan CMakeDeps |
| 2 | thrift compiler 生成目录 CMakeLists.txt 需修改 | ${Boost_LIBRARIES} 未正确设置 | 改用 Boost::filesystem CMake target |
| 3 | patch stream is incomplete | 手写补丁 hunk 行数与 header 不符（-83,22 实际 18 行） | 用 diff -u 重新生成 0001/0002，删除 30 个未引用的 std::filesystem 补丁 |
| 4 | Compatibility with CMake < 3.5 has been removed | 2020 年项目声明 cmake_minimum_required < 3.5，CMake 4.x 不再兼容（E187） | CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | bison: /share/bison/m4sugar/m4sugar.m4 cannot open | conan bison 包 --prefix= 编译，pkgdatadir 固化为 /share/bison | generate() 注入 BISON_PKGDATADIR 指向包内 share/bison |
| 6 | undefined symbol: SHA1 | CONFIG 模式下 ${OPENSSL_LIBRARIES} 为空，thrift1 未链接 OpenSSL | 0003 补丁：${OPENSSL_LIBRARIES} → openssl::openssl target |
| 7 | thrift1 --version 退出码 1 | fbthrift 2020 的 thrift1 无 --version 参数（打印 usage 后退出 1） | test_package 改为功能性测试：编译 smoke.thrift 生成 cpp2 并校验产物 |

## 源码修改

- `CMakeLists.txt` (0001): 添加 `find_package(Boost CONFIG REQUIRED)` 和 `find_package(OpenSSL CONFIG REQUIRED)`，将 Boost include 路径加入 include_directories
- `thrift/compiler/generate/CMakeLists.txt` (0002): 将 `${Boost_LIBRARIES}` 改为 `Boost::filesystem` target
- `thrift/compiler/CMakeLists.txt` (0003): 将 `${OPENSSL_LIBRARIES}` 改为 `openssl::openssl` target（compiler_ast / compiler_generators 两处）

## 依赖版本

- openssl: 1.1.1w
- boost: 1.84.0 (1.87.0 未发布到制品仓，1.84.0 提供所需 libboost_filesystem.a)
- flex: 2.6.4 (tool_requires)
- bison: 3.8.2 (tool_requires)
- gflags/glog: 仅 lib_only 部分需要，compiler_only=ON 不需要

## 验证结果

```bash
thrift1 --gen mstch_cpp2 -o out smoke.thrift   # thrift1 2020 无 --version 参数
# 产物: out/gen-cpp2/{smoke_types.h,smoke_types.cpp,EchoService.h,...}
```

conan create (ohos-aarch64 profile) 全流程通过：构建 → 打包 → test_package 功能测试（编译 IDL 并校验生成文件）exit 0。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fbthrift-2020.08.24.00-ohos-aarch64.tar.gz | ~5MB | Release包（仅 thrift compiler） |
| fbthrift-2020.08.24.00-ohos-aarch64-debug.tar.gz | ~8MB | Debug包 |

## 注意事项

- 仅编译 thrift compiler (compiler_only=ON)，完整 fbthrift 库需要更多依赖（folly, wangle, fizz, fmt, double-conversion 等均未发布到制品仓；folly v2024.11.18.00 与本版本 API 不兼容）——按"无法完整适配则提交已完成部分"处理，待依赖生态补齐后再做完整适配
- cmake 4.1.2 无 FindBoost 模块，使用 find_package(Boost CONFIG) + CMakeDeps 替代
- boost/1.87.0 未发布到制品仓，使用 boost/1.84.0
- gflags/glog 仅 lib_only 部分需要，compiler_only=ON 时不需要
- 2026-09-03: 修复 CI 失败 — 补全 conanfile.py, conandata.yml, test_package/, commands.json
- 2026-09-17: 修复 CI 失败 — 重生成畸形补丁（patch stream incomplete）、CMAKE_POLICY_VERSION_MINIMUM、BISON_PKGDATADIR、openssl::openssl 链接、功能化 test_package、补 sha256、删除 30 个未引用补丁

---
**编译结束**: 2026-06-13 21:04
**CI 修复**: 2026-09-03
**最终状态**: built
