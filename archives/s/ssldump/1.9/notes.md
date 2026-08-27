# ssldump 1.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化环境: `ohc-run.py init-build ssldump 1.9`
2. Conan 依赖自动管理（CMakeToolchain 设置 CMAKE_PREFIX_PATH）
3. CMake 配置: `cmake.configure()` — Conan 工具链自动定位依赖
4. 编译: `cmake.build()`
5. 安装: `cmake.install()`
6. 验证: `ssldump -v` 成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fts.h` not found | OHOS 平台无 fts.h 头文件 | 补丁 0001 移除未使用的 fts.h include |
| 2 | CMake 自定义 FindXXX 模块定位依赖 | 非标准 Conan CMakeDeps | CMakeToolchain 设置 CMAKE_PREFIX_PATH 自动定位 |
| 3 | lld linker fails (libxml2.so.16 not found) | OHOS SDK lld depends on libxml2.so.16 in SDK llvm/lib | build() injects SDK llvm/lib to LD_LIBRARY_PATH |

## 源码修改

- 补丁 0001-remove-unused-fts-include.patch: 移除 pcap/sys.c 中未使用的 `#include <fts.h>`

## 依赖版本

- openssl/1.1.1w（Conan 制品仓）
- libpcap/1.10.6（Conan 制品仓）
- libnet/1.2（Conan 制品仓）
- json-c/0.18（Conan 制品仓）

## 验证结果

```bash
$ ssldump -v
Version: 1.8 (20230814)
Compiled with OpenSSL: decryption enabled
```

## 注意事项

1. ssldump 是命令行工具 (application)，无正式测试套件
2. 上游 CMakeLists.txt 中 project VERSION 为 1.8，但 git tag 为 v1.9
3. Conan 依赖通过 CMakeToolchain 自动管理
4. CI worker 需要 SDK llvm/lib 在 LD_LIBRARY_PATH 中（build() 自动注入）

---

**编译结束**: 2026-08-22
**最终状态**: built
