# boinc-client 8.0.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，CI 沙箱无 automake，使用预生成 autotools 输出）
- 编译日期: 2026-09-17
- 编译器: clang/clang++（OHOS arm64 交叉）
- 状态: built

## 编译步骤

conan 配方（conanfile.py）核心步骤：

1. `source()`: 从官方 GitHub tag 下载 `client_release/8.0/8.0.4.tar.gz`（sha256 校验一致）并解包。
2. `generate()`: 生成 AutotoolsToolchain，configure 参数：
   - `--disable-server --enable-client --disable-manager --disable-fcgi`
   - `--with-ssl=<openssl pkg>` `--with-libcurl=<curl pkg>`
   - `--prefix=/`（使二进制安装到 package 的 `bin/`，命中 test_package VirtualRunEnv 的 PATH）
   - 附加 `-I/-L` 指向 openssl/curl/zlib 依赖的 package 目录。
3. `build()`:
   - 恢复 `_autosetup/config.guess/config.sub/install-sh/missing` 等脚本可执行位（E490）。
   - 修复 `Makefile.am` 中 `pkgconfigdir` 未定义、`configure.ac` 缺 `subdir-objects` 的问题。
   - 复制 `patches/autotools/` 下预生成的 configure/Makefile.in/aclocal.m4 覆盖源码树，跳过 autoreconf（CI 无 automake）。
   - 将 patch 影响的 autotools 输入文件（configure.ac/Makefile.am/m4）mtime 钉到过去，防止 make 重跑 aclocal/automake。
   - `./configure <参数>` + `make -j1`。
4. `package()`: `make install DESTDIR=$package_folder`，复制 COPYING 到 licenses。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 沙箱无 automake，`./_autosetup` 报 "Couldn't find a new-enough version of 'automake'" | 沙箱缺 automake 二进制 | 本机预生成 configure/Makefile.in 等 77 个文件，随配方 `patches/autotools/` 分发，build() 覆盖源码树，跳过 autoreconf |
| 2 | `pkgconfigdir` 未定义导致 configure 失败 | 上游 `Makefile.am` 引用 `pkgconfigdir` 但未声明 | build() 中在 `lib_LTLIBRARIES =` 前插入 `pkgconfigdir = $(libdir)/pkgconfig` |
| 3 | `make install` 后二进制装到 `$package_folder/usr/local/bin/`，test_package 报 `boinc_client binary not found in PATH` | autotools 默认 `ac_default_prefix=/usr/local`，`bindir='${exec_prefix}/bin'`；VirtualRunEnv 只把 `cpp_info.bindirs`（`["bin"]`）加入 PATH | configure 增加 `--prefix=/`，使二进制装到 `$package_folder/bin/` |
| 4 | 上游 autotools 源码树不可写 / 脚本权限丢失 | 归档解包后部分文件只读、可执行位缺失 | build() 递归 `os.chmod` 整个源码树为可写，恢复脚本可执行位 |

## 源码修改

- 本配方未修改上游功能源码；`patches/autotools/`（77 个文件）为本机 autotools 生成产物，用于在无 automake 的 CI 沙箱中完成 configure/make。
- 配方级修改集中在 `conanfile.py`（构建流程编排），见上文编译步骤。

## 依赖版本

- openssl/3.5.6.1
- curl/8.15.0
- zlib/1.3.1.1

## 验证结果

- `conan create` 的构建与打包（configure + make + make install）成功。
- test_package 为静态校验（application 包，交叉产物无法在 x86 沙箱运行二进制）：
  - `boinc_client` / `boinccmd` 二进制存在且为 ELF
  - 依赖库 libcurl/libssl/libcrypto/libz 存在
  - `boinc_client` ELF 类型为 EXEC 或 DYN
- 上游测试（rule4 清点）：**44 用例 = lib 42 + sched 2**，lib 42 例已真实编译并运行（gtest 1.17.0 OHOS armv8 包挂接），结果 **37 通过 / 4 失败 / 1 崩溃**；sched 2 例依赖 MySQL + 服务端 libsched.a（client-only 构建不产出），无法在 client 配方中运行。详细原因见 `test_package/MANIFEST.yml`。

## 交付物

| 文件 | 说明 |
|------|------|
| boinc-client/8.0.4/bin/boinc_client | BOINC 客户端主程序（arm64 ELF） |
| boinc-client/8.0.4/bin/boinccmd | BOINC 命令行控制工具（arm64 ELF） |
| boinc-client/8.0.4/licenses/COPYING | LGPL-3.0 许可证 |

## 注意事项

- 上游 BOINC 8.0.4 自带 gtest 单元测试 44 个（`tests/unit-tests/`，lib 8 文件 + sched 1 文件），上游仅注册在 CMake 构建树；本配方在 autotools 构建后，用 `test_requires("gtest/1.17.0")`（ohpcd registry 的 OHOS armv8 二进制包）直接编译 `tests/unit-tests/lib/*.cpp` 并逐个 suite 真实运行，输出 `HMBS_UPSTREAM_TEST_RESULT`。42 例中 37 通过，4 失败 1 崩溃均有具体平台原因：
  - `test_synch.synch`：崩溃（Signal 31 = SIGSYS）。用例创建 SysV 信号量（`create_semaphore`→`semget`），OHOS 沙箱不允许该系统调用。
  - `test_shmem.shmem`：`shmget: Permission denied`（-144）。同上，SysV 共享内存在 OHOS 沙箱被拒绝。
  - `test_util.drand`：`drand() > 0` 为 false。`drand()` = `rand()/RAND_MAX`，OHOS 上首次 `rand()` 返回 0。
  - `test_util.linux_cpu_time`：`linux_cpu_time(1) > 0` 为 false。实现读取 `/proc/1/stat` 的第 14/15 字段（utime/stime），OHOS 沙箱中该文件不存在或字段不可解析（fscanf 返回非 2），返回 0。
  - `test_str_util.precision_time_to_string`：期望值与实际值差一个符号位。上游期望串 `"...10.-2147483648"` 含 INT_MIN 溢出伪影（`abs()` 对 INT_MIN 溢出），实际输出 `"...10.2147483647"` 才是正确格式化；属上游测试自身 bug。
  - sched 2 例（`test_credit`）：其链接目标是服务端调度库 `libsched.a`（sched/Makefile.am 中 `lib_LTLIBRARIES = libsched.la`），由 68 个服务端源（含 handle_request/sched_main 等）+ db 层构成；本配方为 client-only（`--disable-server`），configure 后 sched/ 目录不产出该库。审计复核（2026-09-17）确认 ohpcd registry 实际存在 mariadb/11.8.8 的 OHOS armv8 二进制包（mysql.h + libmariadbclient.a 齐全），MySQL 客户端依赖本身可解，但即便接入 mariadb + wolfSSL，test_credit 仍依赖完整服务端 libsched.a，属完整服务端构建范畴，超出 client-only 配方边界，故如实声明未执行。
- 本包为 application 类型（无 include/lib 交付），`package_info` 清空 includedirs/libdirs。
