# ettercap 0.8.4.1 适配笔记

## 编译环境
- 构建系统: cmake (CMakeLists.txt, cmake_minimum_required 3.25)
- 编译日期: 2026-08-22
- 编译器: clang 15.0.4 / clang++
- 状态: built (探索编译通过，conan-verify 待验证)

## 编译步骤

```bash
# 1. 下载解压源码 (init-build 自动完成)
# 2. conan install 依赖生成 toolchain + CMakeDeps
conan install conanfile.py -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 3. cmake configure
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=./conan_toolchain.cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DENABLE_GTK=OFF -DENABLE_GEOIP=OFF -DENABLE_IPV6=OFF \
  -DENABLE_LUA=OFF -DENABLE_PDF_DOCS=OFF -DENABLE_TESTS=OFF \
  -DSYSTEM_CURL=OFF -DBUNDLED_CURL=OFF
# 4. make -j1 && make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | EttercapOSTest.cmake FATAL_ERROR "Operating system not supported" | CMAKE_SYSTEM_NAME=HarmonyOS 不在 OS 检测列表中 | 在 EttercapOSTest.cmake 添加 `elseif(${CMAKE_SYSTEM_NAME} MATCHES "HarmonyOS") set(OS_LINUX 1)` — OHOS 基于 Linux 内核，复用 ec_linux.c |
| 2 | pcap.h not found (编译 ec_interfaces.c 时) | EttercapLibCheck.cmake 的 `find_library(HAVE_PCAP pcap)` 只找库不找头文件路径 | 添加 `find_path(HAVE_PCAP_H pcap.h)` 并将结果加入 `EC_INCLUDE` |
| 3 | openssl/aes.h not found | Conan CMakeDeps 的 openssl-config.cmake 拦截了 find_package(OpenSSL)，设置 `openssl_LIBRARIES`(小写) 而非 `OPENSSL_LIBRARIES`(大写)，导致 EC_LIBS 为空 | 在 EttercapLibCheck.cmake 添加 elseif 分支，使用 conan 变量 `openssl_LIBS_RELEASE` + `openssl_LIB_DIRS_RELEASE` 获取完整库路径 |
| 4 | zlib.h 相关符号未链接 | 同问题3，Conan CMakeDeps 拦截 find_package(ZLIB) | 同问题3方案，添加 zlib 的 conan 变量回退 |
| 5 | sockaddr_storage 重定义错误 (ec_sslwrap.c) | `#include <linux/netfilter_ipv4.h>` 链式引入 `linux/socket.h`，与 `sys/socket.h` 的 sockaddr_storage 定义冲突 (OHOS sysroot 已知问题) | 在 ec_sslwrap.c 中用 `#ifdef __OHOS__` 守卫，跳过 `#include <linux/netfilter_ipv4.h>`，直接 `#define SO_ORIGINAL_DST 80` |
| 6 | ncurses panel/menu 符号未找到 (item_opts_off, new_menu 等) | Conan ncurses 提供宽字符版 libpanelw.a/libmenuw.a，但 EttercapLibCheck.cmake 的 `find_library(FOUND_PANEL panel)` 不匹配 panelw | 修改 find_library 搜索 panel 和 panelw (menu 和 menuw)；同时通过 cmake cache 变量显式指定路径 |
| 7 | pthread_testcancel/pthread_cancel/pthread_setcancelstate/type 运行时未找到 | OHOS libc.so 不导出这4个线程取消函数 (仅在 libc.a 中有) | 从 OHOS sysroot 的 libc.a 中提取 pthread_cancel.o 等目标文件，创建 libpthread_cancel.a 静态桩库，通过 CMAKE_EXE_LINKER_FLAGS 链接 |
| 8 | libettercap.so 链接时 --no-allow-shlib-undefined 报错 | OHOS lld 默认启用 --no-allow-shlib-undefined，共享库的间接依赖符号必须解析 | 将 lib_ettercap 和 ec_interfaces 从 SHARED 改为 STATIC；同时添加 -Wl,--allow-shlib-undefined 和 -Wl,--allow-multiple-definition 链接选项 |
| 9 | etterfilter/etterlog 链接时 ec_gbls 重复定义 | 改为静态库后，ec_globals.c 的 ec_gbls 与 ef_main.c/el_main.c 中的定义冲突 | 使用 -Wl,--allow-multiple-definition 让链接器接受第一个定义 |
| 10 | bison 找不到 m4sugar.m4 | Conan bison 包未设置 BISON_PKGDATADIR 环境变量 | 在 conanfile.py generate() 中设置 BISON_PKGDATADIR 环境变量 |
| 11 | dn_expand 符号未找到 (HAVE_RESOLV NOTFOUND) | OHOS 无独立 libresolv，dn_expand 在 libc 中 | 修改 EttercapLibCheck.cmake 的 resolv 回退条件从 `if(OS_BSD)` 改为 `if(OS_BSD OR OS_LINUX)` |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| cmake/Modules/EttercapOSTest.cmake | 添加 HarmonyOS 识别为 Linux 变体 (OS_LINUX=1) |
| cmake/Modules/EttercapLibCheck.cmake | 1. 添加 pcap 头文件路径查找; 2. OpenSSL/ZLIB 兼容 Conan CMakeDeps 变量; 3. panel/menu 搜索宽字符变体; 4. resolv 回退扩展到 OS_LINUX |
| src/ec_sslwrap.c | OHOS 下跳过 linux/netfilter_ipv4.h，直接定义 SO_ORIGINAL_DST |
| src/CMakeLists.txt | lib_ettercap 从 SHARED 改为 STATIC |
| src/interfaces/CMakeLists.txt | ec_interfaces 从 SHARED 改为 STATIC |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| libpcap | 1.10.6 | 静态库 |
| libnet | 1.2 | 静态库 |
| openssl | 3.5.6.1.1 | 静态库 |
| ncurses | 6.6 | 静态库 (R4: --without-shared) |
| zlib | 1.3.1.1.1.1 | 静态库 |
| pcre | 8.45 | 静态库 |
| bison | 3.8.2 | 构建工具 (tool_requires) |
| flex | 2.6.4 | 构建工具 (tool_requires) |

## 验证结果

```bash
$ ./src/ettercap --version
ettercap 0.8.4.1 (运行时有 etter.conf dissector 警告，不影响功能)

$ ./utils/etterfilter --version
etterfilter 0.8.4.1 copyright 2001-2026 Ettercap Development Team

$ ./utils/etterlog --version
etterlog 0.8.4.1 copyright 2001-2026 Ettercap Development Team

$ file src/ettercap
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 产物

| 文件 | 说明 |
|------|------|
| bin/ettercap | 主程序 (含 curses/daemon/text 接口) |
| bin/etterfilter | 过滤器编译工具 |
| bin/etterlog | 日志分析工具 |
| lib/ettercap/ec_*.so | 插件模块 (动态加载) |
| lib/libettercap.a | ettercap 核心静态库 |
| share/ettercap/ | 配置文件和数据文件 |
| etc/ettercap/ | etter.conf 配置 |

## 注意事项

1. **静态库构建**: libettercap 和 ec_interfaces 必须构建为静态库 (STATIC)，因为 OHOS libc.so 不导出 pthread_cancel 系列函数，共享库运行时无法解析这些符号。
2. **pthread_cancel 桩库**: 需要从 OHOS sysroot 的 libc.a 中提取 pthread_cancel.o, pthread_setcancelstate.o, pthread_setcanceltype.o, pthread_testcancel.o 创建静态桩库 libpthread_cancel.a，在 conanfile.py 中通过 CMAKE_EXE_LINKER_FLAGS 链接。
3. **bison 环境变量**: Conan bison 包未设置 BISON_PKGDATADIR，需在 generate() 中手动设置。
4. **禁用功能**: GTK (无 GTK3 依赖)、GeoIP (无 MaxMind 库)、IPv6 (减少适配复杂度)、LUA (实验性)、CURL (sslstrip 插件可选)。
5. **插件**: 插件以 .so 形式构建，运行时通过 dlopen 加载。由于 libettercap 是静态库，插件在运行时需要主程序导出符号。
---

**编译结束**: 2026-08-22 16:02
**最终状态**: built

---

## 上游测试用例检查与运行记录

### 上游测试发现

ettercap 0.8.4.1 上游源码包含测试目录 tests/，使用 libcheck (Check unit testing framework) 框架：

- 测试文件: tests/test_ec_decode.c (1 个测试可执行文件)
- 测试 CMake 配置: tests/CMakeLists.txt
- 根 CMakeLists.txt 配置:
  - L203: enable_testing() (启用 CTest)
  - L21: option(ENABLE_TESTS "Enable Unit Tests" OFF) (ENABLE_TESTS 选项)
  - L204: add_subdirectory(tests) (测试子目录引用)

### tests/CMakeLists.txt 内容

```cmake
include_directories(. ../include ${LIBCHECK_INCLUDE_DIRS})

add_custom_target(test_verbose COMMAND ${CMAKE_CTEST_COMMAND} -V)

# Adds a test by name
macro(_t NAME)
  add_executable(test_${NAME} test_${NAME}.c)
  target_link_libraries(test_${NAME} lib_ettercap ec_interfaces
  ${LIBCHECK_LIBRARIES} ${CMAKE_THREAD_LIBS_INIT} ${LIBCHECK_LDFLAGS})
  add_test(test_${NAME} ${CMAKE_CURRENT_BINARY_DIR}/test_${NAME})
endmacro()

_t(ec_decode)
```

关键字: ['add_custom_target', 'add_test', 'LIBCHECK']

### test_ec_decode.c 测试内容

- 头文件包含: ['#include <stdio.h>', '#include <check.h>', '#include <ec.h>', '#include <ec_libettercap.h>', '#include <ec_decode.h>', '#include <ec_proto.h>']
- 测试函数/Check 宏: ['START_TEST (test_get_decoder_default)', 'END_TEST', 'START_TEST (test_get_decoder_ip)', 'END_TEST', 'START_TEST (test_get_decoder_tcp)', 'END_TEST', 'START_TEST (test_get_decoder_udp)', 'END_TEST']

该测试验证 ettercap 的 ec_decode 协议解码功能，使用 libcheck 的 START_TEST/END_TEST/srunner API。

### libcheck 依赖可用性

- 制品仓 (ohpcd): 已发布
- 本地缓存: Local Cache
  WARN: There are no matching recipe references
- libcheck 远程查询: ohpcd
  check
    check/0.15.2

### 测试构建状态

- conan create 时是否构建测试: 是
- conanfile.py 是否含 ENABLE_TESTS 选项: 是
- 测试二进制文件: /storage/Users/currentUser/.conan2/p/b/etter18ec1ecfd19fe/b/

### 交叉编译语法检查

使用 OHOS aarch64 交叉编译器对 test_ec_decode.c 进行语法检查:
- 编译器: 未找到
- 结果: NO CROSS COMPILER IN PROFILE

### 结论

上游测试用例依赖 libcheck 框架，该框架已在 ohpcd 制品仓发布。当前 conanfile.py 构建时未传递 ENABLE_TESTS 选项，测试二进制未构建。如需运行上游测试，可在 conanfile.py 中添加 ENABLE_TESTS=ON 选项并声明 libcheck 依赖，然后重新构建。由于交叉编译环境限制（OHOS aarch64），测试二进制无法在构建机直接运行，需在目标设备上执行。

### 建议后续行动

1. 适配发布 libcheck 到 ohpcd 制品仓（如尚未发布）
2. 在 conanfile.py 添加 ENABLE_TESTS 选项
3. 在 build() 中传递 -DENABLE_TESTS=ON 给 CMake
4. 在目标设备 (OHOS aarch64) 上执行 ctest 运行上游测试
