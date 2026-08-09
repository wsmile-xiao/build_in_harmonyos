# gadap 2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-03
- 编译器: clang/clang++ (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. 初始化编译环境并下载源码（Ubuntu archive 官方 orig.tar.gz）
2. 修复 configure 临时目录创建逻辑：HMDFS 上 `umask 077 && mktemp -d ./confstatXXXXXX`
   创建的目录权限 700、owner 映射异常，导致 config.status 写入被拒；改为普通 `mkdir -p`。
3. 将源码根目录的 `VERSION` 文件改名 `GADAP_VERSION`：HMDFS 大小写不敏感下，
   `VERSION`（内容 "2.0"）会遮蔽 libc++ 的 `<version>` 头，导致 `expected unqualified-id` 编译错误。
4. 适配 libdap 3.21.1 命名空间：上游源码（2008 年）针对无命名空间的旧 libdap，
   新版类型均在 `libdap::` 下，需在头文件中 `using namespace libdap;`。
5. VPATH 构建下 test 链接路径修复：`test_LDADD` 从 `$(top_srcdir)/src/` 改为 `$(top_builddir)/src/`。
6. 依赖通过系统预编译包提供（cmd-pkgs → ~/usr/local）：libdap 3.21.1、libxml2 2.15.3、curl、libtirpc 1.3.3；
   libxml2 同时以 conan 依赖声明。
7. conan-verify 验证通过（G0-G4 全绿）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++ compiler cannot create executables | PATH 中无 g++/c++，configure 找不到 C++ 编译器 | 设置 `CXX=/data/service/hnp/bin/clang++`、`CC=/data/service/hnp/bin/clang` |
| 2 | config.status: can't create ./confstatXXX (Permission denied) | HMDFS 上 umask 077 + SGID 权限映射问题 | 修改 configure 临时目录创建为 `mkdir -p` |
| 3 | `../version:1:1: expected unqualified-id`（"2.0"） | VERSION 文件遮蔽 libc++ `<version>` 头（HMDFS 大小写不敏感） | VERSION 改名 GADAP_VERSION |
| 4 | unknown class name 'Str'/'Byte' 等 | libdap 新版类型移入 `libdap::` 命名空间 | 添加 `using namespace libdap;` |
| 5 | test 链接失败: -lgadap 找不到 | VPATH 构建下 test_LDADD 用 top_srcdir 指向源码目录 | 改用 `$(top_builddir)/src/` |
| 6 | undefined symbol: libdap::Connect:: 等 | test_package 链接缺 libdap/curl/libtirpc 系统库 | package_info 添加 system_libs + linkflags |
| 7 | 运行期 libdap.so.27 not found | 系统预编译包位于 ~/usr/local/lib 未入 LD_LIBRARY_PATH | runenv_info.prepend_path("LD_LIBRARY_PATH") |

## 源码修改

7 个补丁（patches/）：
- 0001-configure.patch：临时目录创建修复 + VERSION → GADAP_VERSION
- 0002-src-gaBaseTypes.h.patch：`using namespace libdap;`
- 0003-src-gaReports.cc.patch：`#include <cstring>`
- 0004-src-gaTypeFactory.h.patch：`using namespace libdap;`
- 0005-src-gaUtils.h.patch：`using namespace libdap;`
- 0006-test-Makefile.in.patch：top_srcdir → top_builddir
- 0007-test-test.cc.patch：`#include <cstring>`

## 依赖版本

- libdap/3.21.1（系统预编译包）
- libxml2/2.15.3（conan 依赖 + 系统预编译包）
- curl/8.19.0（系统预编译包）
- libtirpc/1.3.3（系统预编译包）

## 验证结果

```bash
conan-verify gadap 2.0  # G0-G4 全部 PASS，test_package L1 测试通过
```

## 注意事项

- libdap/curl/libtirpc 未发布为 conan 配方，由系统预编译包（cmd-pkgs）提供，路径固定 ~/usr/local；
  未来若发布为 conan 包，可将 requirements/system_libs 收敛为 conan 依赖。
- configure 由 Autoconf 2.59 生成，构建时需避免 autotools 重生成（否则升级到 2.72 会破坏临时目录补丁）。

---

**编译结束**: 2026-08-03 19:10
**最终状态**: built
