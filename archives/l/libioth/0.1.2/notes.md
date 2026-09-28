# libioth 0.1.2 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-26
- 编译器: clang/clang++
- 状态: built（待真机预检回填最终证据）

## Source

上游仓库：https://github.com/virtualsquare/libioth（VirtualSquare 团队，LGPL-2.1-or-later）。

版本说明：任务版本 0.1.2 对应上游官方 tag `0.1.2`，源码包为官方
`https://github.com/virtualsquare/libioth/archive/refs/tags/0.1.2.tar.gz`（R39 官方源），SHA256 如下：

```
0e3370a35116ea1e125ebb0f494cb484634211d02f505657f806a77b8e34dd84
```

源码包内容：`ioth.c` / `ioth.h` / `ioth_getifaddrs.c`（ioth 库本体）、`iothaddr.c` /
`iothaddr.h`（地址辅助库）、顶层 `CMakeLists.txt`、`test/`（两个手工交互示例）、
`modules/`（各栈插件）、`man/`（pandoc 文档页）、`README.md`、`COPYING`。无 `tests/` 目录。

附带 header-only 依赖 `nlinline 0.2.2`（`ioth.h` 包含 `nlinline+.h`）：
`https://github.com/virtualsquare/nlinline/archive/refs/tags/0.2.2.tar.gz`，
SHA256 `42d7d18ec31e07171e120bb71079d7ac96415f6231deb33fda9b87c57d7cd7db`，
在 `source()` 内获取并随包安装 `nlinline.h` / `nlinline+.h`。

## 上游测试审计（no_tests 依据）

逐项审计上游 0.1.2 发布包与构建文件，确认确实无任何自动化测试：

1. 顶层 `CMakeLists.txt`、 `test/CMakeLists.txt`、`modules/CMakeLists.txt`、
   `man/CMakeLists.txt` 全文无 `enable_testing`、`include(CTest)`、`add_test`、
   `add_subdirectory(tests)`；`test/CMakeLists.txt` 仅定义 `iothtest_server` /
   `iothtest_client` 两个手工示例可执行文件，未注册为 ctest。
2. `test/` 仅含 `iothtest_server.c` / `iothtest_client.c`，需 vde 交换机与三终端
   手工操作（先起 vde_switch，再分别起 server/client），无断言、无期望输出比对。
3. 发布包与 GitHub 树均无 `tests/`、`unittests/` 目录，无 `*test*.py/sh` 测试脚本，
   无 gtest/pytest/ctest 注册；`ctest -N` 确定性条目数为 0。
4. `man/` 仅用 pandoc/make 生成安装 man 页，无测试目标；`modules/` 仅定义各栈插件
   模块目标，无测试逻辑。
5. 因此 `build()` 不调用上游测试，直接输出 `status:"no_tests"` 标记；
   `test_package/MANIFEST.yml` 同步声明 `upstream_tests_exist: false`、
   `upstream_test_total: 0`（口径 `ctest_entries`）与本审计摘要。

## Build

配方使用 `CMakeToolchain`，`BUILD_SHARED_LIBS` 跟随 `shared` 选项（默认静态）。
平台校验仅接受 `Linux`/`OHOS`（R32 口径）。
上游头文件探针经 `CMAKE_REQUIRED_INCLUDES` 暴露 Conan 依赖头文件目录与 vendored
nlinline 源码目录；`CMAKE_C_COMPILER_WORKS` / `CMAKE_C_ABI_COMPILED` 跳过 OHOS
沙箱内跑不起来的 try_compile 探针（libfduserdata 0.1.2 同款）。

OHOS 适配点（`patches/0001-ohos-portability.patch` + `build()` 内确定性
CMake/source 改写，POSIX 兼容方式，未引入任何平台宏）：

1. 依赖可选化：顶层 `LIBS_REQUIRED` 去掉 `vdeplug`、`HEADERS_REQUIRED` 去掉
   `libvdeplug.h`；`modules/` 内 `vdestack` 插件仅在 `find_library(vdeplug)` 成功时构建。
2. `add_library(ioth/iothaddr SHARED ...)` 去掉 `SHARED` 关键字，使其跟随
   `BUILD_SHARED_LIBS`；补齐 `ARCHIVE`/`RUNTIME` 安装目标（上游仅安装 LIBRARY，
   静态构建将安装空包）。
3. `man/` 与 `test/`（手工示例）在 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"` 时跳过，
   Linux 保持上游行为不变。
4. HarmonyOS libc 内含 pthread API，跳过 `target_link_libraries(pthread)`。
5. 上游 `target_link_libraries(ioth dl fduserdata)` 改用 `find_library` 绝对路径，
   避免 OHOS 下 Conan 缓存库 `-l` 搜不到的问题。
6. musl 兼容（`_patch_upstream_sources`）：`ioth.c` 内 `dlmopen`/`LM_ID_*`
   回退为 `dlopen`；`nlinline.h` 与 `ioth_getifaddrs.c` 内隐藏内核
   `linux/socket.h` 的 `sockaddr_storage` tag 名；去掉无用的 `linux/if_arp.h`；
   直引 `netpacket/packet.h` 提供 `sockaddr_ll`。

`build()` 中真实执行 `cmake.configure()` + `cmake.build()` 后，输出
`HMBS_UPSTREAM_TEST_RESULT`（`status:"no_tests"`、`discovered:0`、`executed:0` 及具体 reason），
并落盘 `res/upstream_test_result.json` 供 test_package 重发（防缓存命中丢失证据）。

## Tests

test_package 消费者测试（`test.c`，TAP 13 检查，全部实质调用库 API，无网络、无 root 需求）：

- native 栈生命周期：`ioth_newstack(NULL,NULL)` 建内核栈、`ioth_get_defstack` 查默认栈、
  `ioth_set_defstack` 设默认栈、`ioth_msocket` / `ioth_socket` 真实建套接字、
  `ioth_close` 关闭、`ioth_delstack` 删栈。
- iothaddr 确定性向量：`iothaddr_hashmac("test.v2.cs.unibo.it")` 期望
  `6a:d6:2f:5a:5a:2e`、`ioth_macton` 解析及字节比对、`ioth_ntomac` 回显、
  `hasheui64` 与 `eui64(hashmac)` 一致性。

`test()` 中 `self.run` 真实执行二进制，再以 subprocess 解析 `ok` 行计数，
输出 `HMBS_TEST_PACKAGE_RESULT` 标记；用例失败时二进制非零退出且 `ok` 行缺失，
门禁可捕获（非静默通过）。同时重发包内 `res/upstream_test_result.json`，
并校验其为合法 `no_tests` 证据（`discovered==0` 且 `executed==0` 且 reason 非空）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | man/ 在真机缺 pandoc | 上游无条件构建文档页 | 补丁在 HarmonyOS 上跳过 man/ 子目录 |
| 2 | test/ 手工示例在 OHOS 无 vde 交换机 | 需三终端手工操作，非自动化测试 | 在 HarmonyOS 上跳过 test/ 子目录，Linux 保持不变 |
| 3 | 默认静态构建安装空包 | 上游只安装 LIBRARY 产物 | 补丁补齐 ARCHIVE/RUNTIME 安装目标 |
| 4 | HarmonyOS 链接 -lpthread 失败风险 | libc 已含 pthread，无独立 libpthread | 补丁按 CMAKE_SYSTEM_NAME 跳过 pthread 链接 |
| 5 | 真机 cmake C 编译器自检失败 | OHOS 沙箱 try_compile 跑不起来 + /tmp 只读 | `_writable_tmpdir` 透传 + `COMPILER_WORKS/ABI_COMPILED` 跳过 + 生成后改写 `conan_toolchain.cmake`（strategy-2，libfduserdata 同款） |
| 6 | nlinline+.h 探针失败 | 该 header-only 库暂无 OHOS 配方 | source() 内获取官方 0.2.2 tag 并按文件存在验收，替代 try_compile 探针 |
| 7 | musl 下 dlmopen / sockaddr_storage / if_arp 报错 | glibc 扩展与内核头重定义 | dlmopen 回退 dlopen、隐藏内核 sockaddr_storage tag、去掉无用 linux/if_arp.h |
| 8 | 本轮真机 evidence incomplete（no_tests 须显式声明） | test_package/MANIFEST.yml 为空，未声明 upstream_tests_exist/test_total | 按 spooles/libfduserdata 结构化审计补齐 MANIFEST.yml（exist=false + audit + total=0 + ctest_entries + 空命令 + assertion_count=13） |

## 依赖版本

- `libfduserdata/0.1.2`（本仓库已适配配方）
- `mhash/0.9.9.9`（本仓库已适配配方）
- `nlinline 0.2.2` 官方 tag 源码（build-local 头文件源，非 Conan requirement）

## 验证结果

待真机预检回填：`conan create` 需真实运行库构建 + test_package 13 检查，
并输出 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT(no_tests)` 两行合法 JSON 标记。
上轮真机已实测 13/13 通过（`test_libioth (13 TAP checks)`），本轮仅补齐 MANIFEST 声明，未改代码逻辑。

## OHOS notes

- 非系统同名库（OHOS `/lib` 无 libioth），保留动态库构建能力（默认静态），R26 不适用。
- 纯库项目，无可执行产物，不创建 `commands.json`（R38）。
- 未引入 `#ifdef __OHOS__` 平台宏；全部适配在 CMake/源码层按系统名或编译器特征条件完成。
- 申请人：gcw_uQ09W7jl（队伍：干）。
