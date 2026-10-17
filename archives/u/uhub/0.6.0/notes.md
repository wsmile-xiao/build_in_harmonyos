# uhub 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-24
- 编译器: OHOS SDK clang (aarch64-linux-ohos, C23/gnu23)
- Conan profile: `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8）
- 状态: built（conan-verify G0-G4 全通过；尚未经 CI upload，按 R29 记 built）

## 编译步骤

```bash
# W3 完整链路（本机 OHOS 真机，aarch64）
conan install . -pr=ci/conan/profiles/ohos-aarch64 -of build/gen --build=missing
cmake -S src -B build -DCMAKE_TOOLCHAIN_FILE=build/gen/conan_toolchain.cmake \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=Linux
cmake --build build -j4
DESTDIR="$PWD/stage" cmake --install build
conan create . -pr=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `target "uhub" links to OpenSSL::SSL but the target was not found`，且 `${OPENSSL_INCLUDE_DIR}` 为空 | Conan CMakeDeps 默认 config 模式生成的 `openssl-config.cmake` 不定义 `OpenSSL::SSL/Crypto` 目标，也不填 legacy MODULE 变量；上游 CMakeLists 走 `find_package(OpenSSL)` + `${OPENSSL_INCLUDE_DIR}` + `SQLite::SQLite3` | 配方 `generate()` 中 `deps.set_property(..., "cmake_find_mode", "none")` 关掉自动生成文件，改用工具链变量把 `OPENSSL_ROOT_DIR/OPENSSL_INCLUDE_DIR/OPENSSL_SSL_LIBRARY/OPENSSL_CRYPTO_LIBRARY/SQLite3_INCLUDE_DIR/SQLite3_LIBRARY` 钉到 conan 包内实际路径（同仓 broker/brpc 配方既有做法） |
| 2 | configure 输出 `System is unknown to cmake, create: Platform/HarmonyOS`，随后 `if(UNIX)` 分支全部不生效 → install 规则不执行、`pthread` 未链接、`uhub-admin` 不构建 | 真机上 CMake 主机探测得到 `CMAKE_SYSTEM_NAME=HarmonyOS`，CMake 无 `Platform/HarmonyOS.cmake`，`UNIX` 变量为假。注意 `tc.cache_variables` 只写进 `CMakePresets.json`，直接使用 toolchain 文件时不生效 | 配方中 `tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"`（写入 `conan_toolchain.cmake`，在 `project()` 之前生效），与 `cache_variables` 同时设置 |
| 3 | 链接失败：`undefined reference to pthread_cancel`（且 sysroot 头文件无该声明） | OHOS libc 未提供 `pthread_cancel()`，`libc.so` 中无该符号 | 见补丁 0002：用 `SIGUSR1` + `pthread_exit()` 实现等价语义（信号定向投递到目标线程，处理函数内退出该线程） |
| 4 | `make install` 把插件与配置装到宿主机 `/usr/lib/uhub`、`/etc/uhub`，conan 包内没有这些文件 | 上游 install 使用绝对 `DESTINATION`，越过 `CMAKE_INSTALL_PREFIX` | 补丁 0001：改为相对路径 `lib/uhub`、`etc/uhub` |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001-CMakeLists.txt.patch | `CMakeLists.txt` | install DESTINATION 由绝对路径改为 prefix 相对路径（`/usr/lib/uhub`→`lib/uhub`，`/etc/uhub`→`etc/uhub`） |
| 0002-threads.c.patch | `src/util/threads.c` | `uhub_thread_cancel()` 不再调用 OHOS 缺失的 `pthread_cancel()`，改用 `pthread_once` 安装 `SIGUSR1` 处理函数（内部 `pthread_exit(NULL)`）+ `pthread_kill(handle, SIGUSR1)`；新增 `#include <signal.h>` |

> 两个补丁均未引入平台宏（无 `__OHOS__` 分支），平台差异全部收敛在 conanfile.py 的 `generate()` 与上述两处等价替换中。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| openssl | 3.5.8.1 | 制品仓（静态库 libssl.a / libcrypto.a） |
| sqlite3 | 3.53.4 | 制品仓 |

## 验证结果

```bash
# 1) conan-verify（G0 预扫描 / G1 配方完整性 / G2 conan create / G3 系统同名库隔离 / G4 产物）
$ ohc-run.py conan-verify uhub 0.6.0
✅ 配方验证通过: uhub 0.6.0

# 2) 上游测试套件（真机原生执行 autotest-bin）
$ ./autotest-bin
 * Tests passed:          817 (~100%)
 * Tests failed:            0 (~0%)
--------------------------------------------

# 3) test_package 运行时测试（conan create 内自动执行，日志见 reports/conan-create.log）
uhub/0.6.0-release
user	conan
OK                                    # uhub -C 配置解析通过
INFO: Starting uhub/0.6.0, listening on :::1511...
INFO: Loaded plugin: .../lib/uhub/mod_welcome.so: Welcome plugin, version 0.1.
ALL OK
```

### 上游测试用例申报表（R51）

| 项目 | 内容 |
|------|------|
| 上游测试位置 | `autotest/test.c`（单测驱动，链接 `uhub_SOURCES` 全部源文件；CMake 目标 `autotest-bin`，L152/L181） |
| 是否注册 ctest | 否，上游未使用 `enable_testing()/add_test()`，测试通过直接执行 `autotest-bin` 触发 |
| 上游用例数（断言） | 817 |
| 实测通过 | 817 / 817（100%） |
| 运行环境 | OHOS aarch64 真机（原生执行）；CI 交叉编译容器无法执行目标二进制，故 CI 通过 test_package 的 `can_run` 保护性跳过运行时用例 |
| 是否修改上游测试 | 否，未修改任何测试用例 |
| 是否补全测试 | 否，上游已有测试覆盖；本包按 application 类型补充 test_package 运行时冒烟（版本/用户库/配置解析/服务启动与插件加载） |

## 注意事项

- 本包为 **application**（`uhub`、`uhub-passwd` 两个可执行文件 + 10 个插件 `.so`），无对外头文件/库；插件与示例配置分别落在包内 `lib/uhub/`、`etc/uhub/`。
- 插件运行时搜索路径由配置项 `file_plugins` 指定（默认 `/etc/uhub/plugins.conf`），安装到 `etc/uhub/` 后用户可按需指向包内路径。
- `pthread_cancel` 替代方案保持"仅中断目标线程"的语义；调用点（`src/network/dnsresolver.c` 的 `shutdown_free_jobs` / `net_dns_job_cancel`）在下发取消后都会 `uhub_thread_join`，与替代实现的行为一致。
- 未启用 TLS 之外的额外平台特性；`server_alt_ports`、IPv6（`server_bind_addr=any` → `:::1511`）在真机上均正常。
---

**编译结束**: 2026-09-24 23:17
**最终状态**: built（与 manifest.yaml `status: built` 一致；未经 CI upload，按 R29 记 built）
