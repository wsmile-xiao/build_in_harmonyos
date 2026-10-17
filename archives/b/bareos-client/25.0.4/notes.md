# bareos-client 25.0.4 适配笔记

## 上游信息

- 软件：Bareos（Backup Archiving Recovery Open Sourced），开源备份套件
- 版本：25.0.4（2026-07-02 维护版本）
- 仓库：https://github.com/bareos/bareos（tag `Release/25.0.4`）
- 官网：https://www.bareos.org
- 许可证：AGPL-3.0-only
- 构建系统：CMake（最低 3.17，C++20）
- 源码包：`Release/25.0.4.tar.gz`，13,155,666 字节，
  sha256 `273037beeef9a43b2a629bacdf7cf949857e17c722a679d723a8d2ba1422ce6e`
  （2026-09-06 自官方 GitHub 下载实测）

## 适配范围

本配方只构建上游官方 **universal client**（可移植客户端）配置：
`core/src/{lib,findlib,fastlz,filed,lmdb（内建）,plugins}`，
产物为文件守护进程 `bareos-fd` 单二进制（内部库全静态链接）。
Director / Storage Daemon / bconsole / WebUI 不在范围内，
这是上游为可移植客户端定义的构建边界，不是裁剪。

关键开关（均为上游原生 CMake 选项，无补丁）：

| 开关 | 来源 | 作用 |
|------|------|------|
| `-DBUILD_UNIVERSAL_CLIENT=ON` | 上游预设 | client-only；关闭 python/gfapi/jansson/lzo/capability/bconsole |
| `-DBUILD_SHARED_LIBS=OFF` | 标准选项 | 内部库静态链接，交付二进制不依赖未发布的 `.so` |
| `-DENABLE_WEBUI=OFF` | 上游选项 | WebUI 需 npm，OHOS 无此工具链 |
| `-DENABLE_SYSTEMTESTS=OFF` | 上游选项 | systemtests 需 live Director/SD/FD 集群，client-only 下游上也不启用 |
| `-Dacl=OFF` | 上游选项 | OHOS 无 `sys/acl.h`，默认 ON 会在 configure 触发 FATAL_ERROR |
| `-DENABLE_NLS=0` | 上游选项（CACHE STRING "1"/"0"） | OHOS 无 gettext/libintl，默认 1 会在编译期报 `gettext` 未声明 |
| `-DOPENSSL_ROOT_DIR/-DZLIB_ROOT` | 标准查找变量 | 强制使用 conan 的 openssl/3.5.6 与 zlib/1.3.1 |

xattr 保持默认 ON：上游 `filed` 源码中全部以 `#if defined(HAVE_XATTR)`
守卫，缺失时自动降级，无需像 bacula-fd 那样打 stub。
（2026-09-06 更正：该假设对 `xattr.cc` 本身不成立——见下表 #18；
现以 `-Dxattr=OFF` + 配方 `build()` 内子串级文本编辑关闭（曾用 0009 补丁，
因手写 hunk 行号两次错位改走无行号依赖的 recipe 编辑路线），`filed` 内其他
`HAVE_XATTR` 守卫仍正常降级。）

## 上游测试审计（2026-09-06 解包实测）

- `core/src/tests/`：101 个条目，86 个 gtest `.cc` 文件，
  约 409 个 `TEST/TEST_F/TEST_P` 宏（`^\s*TEST(_F|_P)?\s*\(` 计数），
  71 个 `bareos_add_test()` 测试二进制，
  经 `gtest_discover_tests` 以 `gtest:` 前缀注册进 ctest。
- `systemtests/`：5195 个条目，需 Director+SD+FD 完整备份集群；
  上游在 client-only 构建中默认不启用（`add_subdirectory(systemtests)`
  被 `if(NOT client-only)` 守卫），故不纳入。
- `core/src/droplet/{tests,utests}`：droplet（S3 云后端）在
  64 位 client-only 下才会构建；OHOS 下是否启用以后续预检 configure
  日志为准，未计入本次审计数。

GTest 补齐：制品仓的 `googletest/1.15.2` 归档无 conan 配方（仅旧式
notes），无法 `requires`；按 aevol/9.4.0 已验证模式，把 googletest
1.14.0（sha256 沿用 aevol 真机验证值）在 build() 内构建安装到
构建目录私有前缀，再以 `GTest_ROOT` 传给主 configure。
CPM 六包（CLI11 v2.4.2 / fmt 11.0.2 / GSL v4.0.0 /
expected v1.1.0 / utfcpp v4.0.4 / xxHash v0.8.3）同理以
`CPM_<NAME>_SOURCE` 注入，configure 阶段零网络访问。

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| openssl | 3.5.6 | ohpcd 制品仓（软件级 manifest 标 published） | bareos `find_package(OpenSSL 1.1.1 REQUIRED)` |
| zlib | 1.3.1 | ohpcd 制品仓（bacula-fd 已验证可用） | `ZLIB::ZLIB`（filed 压缩/解压） |
| googletest | 1.14.0 | conandata `deps` 自带（aevol 验证 hash） | 仅构建期测试用，不进交付物 |
| CPM 六包 | 见上 | conandata `deps` 自带 | 构建期源码注入，不进交付物 |

## 编译步骤（真机 conan create 实际执行）

```bash
cd archives/b/bareos-client/25.0.4
conan create . --user=ohpcd --channel=stable \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

流程：`source()` 解包 → `generate()` 写 CMakeDeps/CMakeToolchain（含
CPM/GTest/SSL 路径变量）→ `build()` 内先备齐 CPM 源码、构建安装
gtest，再 `cmake configure/build`，随后 `ctest --output-on-failure`
并打印 `HMBS_UPSTREAM_TEST_RESULT` 标记 → `package()` 从构建树挑出
ELF `bareos-fd` 到 `bin/` → `test_package` 执行 `test_bareos_fd.py`。

构建超时预算：`ci/config/build_timeouts.txt` 登记
`bareos-client/25.0.4 14400`（4h；数百个 C++20 翻译单元单任务构建
+ 71 个测试二进制链接 + ctest 串行执行）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 通用客户端仍需 jansson/lzo 等外部库？ | 否。`BUILD_UNIVERSAL_CLIENT` 预设已强制关闭 | 只保留 openssl+zlib 两个 requires |
| 2 | configure 期 CPM 从 GitHub 拉源码 | 上游 `BareosCpmPackages.cmake` 默认在线获取 | 六包写入 conandata `deps`，`CPM_<NAME>_SOURCE` 注入（CPM.cmake 689 行分支支持） |
| 3 | GTest 缺失导致 `add_subdirectory(tests)` 被静默跳过 | 上游 `core/src/CMakeLists.txt` 无 gtest 即跳过 | build() 内先构建安装 vendored gtest，再主 configure |
| 4 | `acl` 默认 ON 在 OHOS 上 configure 失败 | 上游 `HAVE_SYS_ACL_H` 缺失即 FATAL_ERROR | `-Dacl=OFF`（原生选项） |
| 5 | 交付物形态 | 动态内部库会污染包 | `-DBUILD_SHARED_LIBS=OFF` + 只交付 `bin/bareos-fd` |
| 6 | `BUILD_UNIVERSAL_CLIENT` 在 Clang 上 configure 直接 FATAL（`core/CMakeLists.txt:128 Cannot (yet) do static runtime-libraries on Clang`） | 上游顶层预设 `force_option(ENABLE_STATIC_RUNTIME_LIBS ON)`（CACHE FORCE，命令行 `-D` 覆盖无效），而 `core/` 仅对 GNU 实现静态运行时，非 GNU 直接 FATAL；OHOS 工具链是 Clang | `patches/0001-clang-static-runtime-libs.patch`：Clang（含 AppleClang）分支降为 WARNING 并继续（动态运行时），GNU 行为不变；配方经 `export_conandata_patches`/`apply_conandata_patches` 接入；补丁 hunk 以 sha256 校验通过的官方包内 `core/CMakeLists.txt` 第 123 行原文逐行生成（首轮手写 `@@ -117,7` 与真实包行号错位导致真机 `hunk no.1 doesn't match`，已修正为 `@@ -123,7 +123,12 @@`并做严格位置匹配校验） |
| 7 | configure 在 `core/platforms/CMakeLists.txt:40` 报错 `add_subdirectory given source "unknown"` | `distname.sh` 在 HarmonyOS 上无 lsb_release 且无匹配的 `/etc/*-release`，回退为 `PLATFORM=unknown`，而 `core/platforms/` 下无此子目录；该目录只装发行版打包文件，配方 `package()` 并不执行 `cmake install`（只拷贝 `bareos-fd` 二进制） | `patches/0002-unknown-platform-guard.patch`：`add_subdirectory` 前加 `EXISTS` 守卫，未知平台报 WARNING 并跳过，不伪装成已知发行版；同首轮方式以官方包原文逐行生成并严格校验 |
| 8 | configure 跑完（82s）后 generate 阶段报错 `Target "bareos" links to ZLIB::ZLIB but the target was not found`（`core/src/lib:145`、`fastlz:35`、`filed:58` 同款） | 本仓 `zlib/1.3.1` 配方只设 `cpp_info.libs=["z"]`、未声明 `cmake_file_name/target`，CMakeDeps 生成的是 `zlib-config.cmake`/`zlib::zlib`，而上游 `core/cmake/BareosFindAllLibraries.cmake` 用 `find_package(ZLIB REQUIRED)` 并链接 `ZLIB::ZLIB`，大小写/目标名对不上（OpenSSL 走 `FindOpenSSL` 模块命中故不受影响） | 配方 `generate()` 内 `CMakeDeps.set_property("zlib", cmake_file_name=ZLIB / cmake_target_name=ZLIB::ZLIB / cmake_find_mode=config)`，使生成的 `ZLIBConfig.cmake` 直供 `ZLIB::ZLIB`；无新补丁，`manifest.yaml` 无需变更 |
| 9 | 真机 `source()` 下载主源码包两次 `ConnectTimeoutError(github.com:443)` 后失败 | 真机直连 github.com 超时（30s 连接超时×2 次重试）；属守则“源码包下载超时例外”，须加镜像回退而非改代码 | `conandata.yml` 的 `sources` 与 7 个 `deps` 的 `url` 改为有序列表：`https://gh-proxy.com/<原URL>`（`ci/conan/build_and_test.sh` 的 GitHub 镜像映射）在前、官方原 URL 最后回退；全部 `sha256` 保持不变；配方 `download()`/`get()` 均支持 URL 列表按序尝试 |
| 10 | 构建阶段 `core/src/lmdb/mdb.c` 报 `pthread_mutexattr_setrobust`/`pthread_mutex_consistent` 未声明（-Werror implicit-function-declaration， `cmake.build()` 失败） | OHOS 头文件定义 `EOWNERDEAD`却未提供 pthread robust-mutex API；mdb.c 默认 `MDB_USE_ROBUST=1`导致 `MDB_ROBUST_SUPPORTED=1` 使 robust 调用站 (行 5011/10881) 被编译 | 首轮曾尝试 `patches/0003` 在 `core/src/lmdb/CMakeLists.txt` 加 `add_definitions(-DMDB_USE_ROBUST=0)`，但手写 hunk 头 `@@ -23,5 +23,10 @@` 与正文实际 11 个新行不符（5 行新增定义+1 空行，正文共 11 行），真机 `apply_conandata_patches` 报 `WARN: extra lines for hunk no.1` 后 `ConanException: Failed to parse patch`，构建止于 `build()` 入口；本轮改走不同路线——删除 0003 补丁文件及其 conandata 登记，改为 `generate()` 内 `tc.preprocessor_definitions["MDB_USE_ROBUST"]="0"`（Conan 原生机制，随工具链作用于 lmdb 目标，无行号依赖）；robust 代码全被 `#ifdef MDB_ROBUST_SUPPORTED` 守卫，锁退化为普通互斥锁；`patches/0003` 文件已删除且不再引用 |
| 11 | （同 #10 的后续）手写 CMakeLists 补丁因 hunk 行数不匹配无法被 conan 解析 | 同 #10；直接证据为预检 `WARN: .../0003-...patch: extra lines for hunk no.1 at 15` + `Failed to parse patch`，且失败点在 `build()` 第 110 行 `apply_conandata_patches`，早于任何编译 | 见 #10：弃用补丁路线，改用工具链预定义；`manifest.yaml` 的 `patches_applied` 已移除 0003 条目并在 `configure_options` 登记 `-DMDB_USE_ROBUST=0` 来源 |
| 12 | `cmake.build()` 在 `core/src/lib/address_conf.cc` 报十余处 `use of undeclared identifier 'gettext'`（经 `T_` 宏展开，`baconfig.h:84`），`bareos` 目标编译失败 | 默认 `ENABLE_NLS=1` 时 `baconfig.h` 取 `#ifdef ENABLE_NLS` 分支（`#include <libintl.h>` + `#define T_(s) gettext((s))`），但 OHOS 无 gettext/libintl，实现缺失导致 `-Werror` 下全军覆没 | 无补丁：`generate()` 内 `tc.variables["ENABLE_NLS"]="0"`（上游原生 `CACHE STRING "1"/"0"`，见 `cmake/BareosSetVariableDefaults.cmake`；`core/CMakeLists.txt` 对 AIX 有同款 `set(ENABLE_NLS 0)` 先例）。取 0 后 `baconfig.h` 走 `#else` 分支：`T_(s)` 恒等 + `textdomain/bindtextdomain/setlocale` 空桩；`manifest.yaml configure_options` 已同步 |
| 13 | `cmake.build()` 在 `core/src/lib/bnet_network_dump.cc` 报 `sysroot/usr/include/locale.h:58:36: error: expected unqualified-id`（`char *setlocale(int, const char *);`处，经 libcxx `__locale`→`locale.h`→sysroot `locale.h`链路引入），`bareos` 目标编译失败 | 前一轮 `ENABLE_NLS=0` 修复 gettext 未声明后，baconfig.h 走 `#else /* !ENABLE_NLS */` 分支，其中 `#define setlocale(p, d)` 空宏在预处理阶段把后续所有 `#include <locale.h>` 声明里的函数名替换掉，导致声明变成 `char * (int, const char *)`而语法错误；上一方案假设 NLS 棵头无害是错误的 | 保留 `ENABLE_NLS=0`（T_/textdomain/bindtextdomain 棵头仍需要），新增 `patches/0004-nls-no-setlocale-stub.patch`：仅删除 `#define setlocale(p, d)` 一行（保留 `#undef setlocale`），后续 `<locale.h>` 声明恢复为真实 libc `setlocale()`（OHOS sysroot 存在该函数，NLS 关闭时直接调用无害）；`conandata.yml`/`manifest.yaml` 已登记，patch hunk 头 `@@ -86,11 +86,14 @@` 与官方包内嬙符逐行校验 |
| 14 | `cmake.build()` 在 `core/src/lib/mntent_cache.cc:228-229` 报 `error: unused variable 'fp'/'st' [-Werror,-Wunused-variable]`, `bareos` 目标编译失败 (27% 处) | `refresh_mount_cache()` 内 `#if defined(HAVE_GETMNTENT)` 分支先声明 `FILE* fp; struct stat st;`, 但后续所有使用点均被内层 `#if defined(HAVE_LINUX_OS) || defined(HAVE_AIX_OS)` / `#elif defined(HAVE_SUN_OS)` 守卫. OHOS 下 `CMAKE_SYSTEM_NAME=HarmonyOS` 不符 `MATCHES Linux`, 且非 Sun/AIX, 而 `HAVE_GETMNTENT` 在 OHOS 仍被检测为真, 声明留下却无人使用, `-Werror` 直接报错. 这是 0004 修复生效后暴露的新问题, 与 setlocale 无关 | 新增 `patches/0005-mntent-cache-unused-vars.patch`: 在 `#if defined(HAVE_GETMNTENT)` 内对声明加同条件守卫 `#if defined(HAVE_LINUX_OS) || defined(HAVE_AIX_OS) || defined(HAVE_SUN_OS)` (恰为内层两分支的并集). OHOS 下声明直接消失, 函数变为空壳. 未改 `-Werror` 全局开关; `conandata.yml`/`manifest.yaml` 已登记, hunk `@@ -227,4 +227,6 @@` 与官方包逐行校验 |
| 15 | `cmake.build()` 在 `core/src/lib/mntent_cache.cc:205` 报 `error: unused function 'SkipFstype' [-Werror,-Wunused-function]`, `bareos` 目标编译失败 (27% 处, 紧随 #14 之后) | 0005 只守卫了 `fp`/`st` 变量声明, 但同文件的 `static inline bool SkipFstype()` 在 OHOS 下同样无调用点: 其全部 4 处调用分别被 `HAVE_LINUX_OS/HAVE_AIX_OS`, `HAVE_SUN_OS`, `HAVE_GETMNTINFO`, `HAVE_AIX_OS` 守卫, OHOS 仅有 `HAVE_GETMNTENT` 为真而四者皆假. 上一方案按"变量未使用"假设只修声明是片面的, 同一平台缺口必然连带函数未使用 | 新增 `patches/0006-mntent-cache-skipfstype-unused.patch` (不同路线): 不再加 `#if` 守卫 (需同步守卫 `skipped_fs_types`, 易发散), 而是给定义加 `[[maybe_unused]]` (上游同文件 `refresh_mount_cache` 参数已用此属性, C++20 可用). 保留函数体, 不改 `-Werror`; 同步修复 `conandata.yml` 中 0004/0005 条目重复键导致描述错位的问题并登记 0006 |
| 16 | 真机 `cmake.build()` 在 `core/src/lib/libbareos.so` 链接期报 `ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`（`libz.a(zutil.o)` 内 `z_errmsg`，48% 处），`bareos` 目标链接失败 | 上游 `core/src/lib`、`findlib`、`fastlz`、`lmdb` 四处 `add_library(... SHARED)` 写死类型，无视配方 `BUILD_SHARED_LIBS=OFF`；而本仓 `zlib/1.3.1` 是 `--static` 无 `-fPIC` 的静态包（R26 同名系统库约束），非 PIC 归档链进 shared lib 在 aarch64 上是硬错误；openssl 恰好带 PIC 才没爆 | 新增 `patches/0007-respect-build-shared-libs.patch`：四处去掉写死的 `SHARED`（无类型即服从 `BUILD_SHARED_LIBS`，默认 ON 时行为与上游一致）；`filed` 插件保持 `MODULE`（自带 `-fPIC` 且不链 `libz.a`，不受影响）；`bareoslmdb` 一并静态化，否则交付的 `bareos-fd` 会依赖未发布的 `.so`。四 hunk 头行号/行数已用 sha256 校验包（13,155,666 字节）逐行验签 |
| 17 | 真机 `cmake.build()` 在 `core/src/findlib/fstype.cc:138` 报 `error: unused parameter 'fname'/'fs'/'fslen' [-Werror,-Wunused-parameter]`，`bareosfind` 目标编译失败（54% 处，0007 链接修复之后） | OHOS 的 `CMAKE_SYSTEM_NAME=HarmonyOS` 不匹配 `HAVE_DARWIN_OS/HAVE_FREEBSD_OS/HAVE_LINUX_OS/HAVE_SUN_OS/HAVE_WIN32` 任一分支，落入 `#else /* No recognised OS */` 的 `fstype()` 空桩（仅 `Dmsg0 + return false`），三参数全未使用，`-Werror` 直接报错；与 #14/#15 同属“OHOS 平台宏缺口 + -Werror”家族，但文件不同 | 新增 `patches/0008-fstype-fallback-unused-params.patch`：仅在 fallback 分支函数体内加 `(void)fname/(void)fs/(void)fslen` 三行，其他 OS 分支不动；不改 `-Werror` 全局开关；`conandata.yml`/`manifest.yaml` 已登记 |
| 18 | 真机 `cmake.build()` 在 `core/src/findlib/xattr.cc:2731-2787` 报 9 个 `error: use of undeclared identifier 'os_build_xattr_streams'/'os_parse_xattr_streams'/'os_default_xattr_streams'`（另带 `-Wpointer-bool-conversion` 连带错），`bareosfind` 目标编译失败（56% 处，0008 修复之后） | OHOS sysroot 提供 `sys/xattr.h` 使 `HAVE_XATTR=1`（`core/CMakeLists.txt` 仅按头文件存在判定），但 `HAVE_AIX_OS/HAVE_DARWIN_OS/HAVE_LINUX_OS/HAVE_SUN_OS` 全假，`xattr.cc` 内 `#else` 分支的通用 `BuildXattrStreams/ParseXattrStreams` 入口引用了从未定义的 `os_*` 符号；与 #14/#15/#17 同属“OHOS 平台宏缺口”家族，但此处是缺符号而非 `-Wunused` | 两处改动：① 新增 `patches/0009-respect-xattr-option.patch`：上游虽声明 `option(xattr ...)`（`cmake/BareosSetVariableDefaults.cmake`）却在 `core/CMakeLists.txt` 中被忽略（对比 `acl` 有 `if(${acl})` 守卫），补丁给 `HAVE_XATTR` 判定加 `if(${xattr})` 守卫（`BUILD_UNIVERSAL_CLIENT` 未 force 该选项，`-D` 有效）；② 配方 `generate()` 加 `tc.variables["xattr"]=False`，使 `xattr.cc` 走 `#if !defined(HAVE_XATTR)` 的 `kErrorFatal` 桩路径；`conandata.yml`/`manifest.yaml` 已登记 |
| 18b | 0009 首版真机 `apply_conandata_patches` 报 `hunk no.1 doesn't match source file at line 280 ... source file is different`，`build()` 入口即失败（与历史 #6/#11 同类手写 hunk 行号错位） | 首版 hunk 头 `@@ -280,4` 为凭记忆估算；真机 conan 补丁器按行号严格匹配，280 行实际为空行 | 重写 0009：以 `Release/25.0.4` tag 原文逐行核验，真块位于 `core/CMakeLists.txt` 592-595 行（前有 `acl` 块 `endif()/endif()` + 空行，后接 `if(gfapi_FOUND)`），hunk 头修正为 `@@ -589,7 +589,9 @@`（旧 7=3 删+4 上下文，新 9=5 增+4 上下文），内容逐字节对齐 |
| 18c | 0009 第二版仍被真机拒收：`hunk no.1 doesn't match source file at line 589, expected '  endif()' actual '      set(HAVE_ACL 1)'`，`build()` 入口即失败；连续两次同一指纹失败，按守则必须换路线 | 第二版 hunk 上下文把 `acl` 块尾记成 `  endif()/ endif()`（第二行 1 空格），而源码实为 `  endif()/endif()`（第二行 0 空格），且 589 行落在 `acl` 块内部而非 `xattr` 块；逐字手写上下文遇到缩进/行号漂移即脆断 | 弃用补丁路线（删除 `patches/0009` 文件及其 `conandata.yml` 登记）：`conanfile.py` 新增 `_fix_xattr_option()`，在 `build()` 内 `apply_conandata_patches` 之后、主 `cmake.configure()` 之前，对 `core/CMakeLists.txt` 做子串级编辑——以 `set(have_xattr YES)` 为唯一锚点（无行号）追加 `if(NOT xattr)/unset(HAVE_XATTR)/set(have_xattr NO)/endif()`；`xattr=OFF` 时清掉 `HAVE_XATTR` 走 `!HAVE_XATTR` 桩，`ON` 时守卫为假行为不变；锚点缺失则抛 `ConanException` 明示；`manifest.yaml` 同步 |

| 19 | 真机 `ctest` 6 失败：`Backtrace.test_backtrace(Failed)` + 5×`fvec_fixture.*(SEGFAULT)`，且配方标记 `discovered=40/passed=40/failed=0` 与 `ctest` 尾部 `139 个测试、6 失败` 自相矛盾 | fvec：`SetUp()` 用 `std::tmpfile()` 硬编码 `/tmp`，而真机 `/tmp` 只读（`preflight.sh[306] can't create temporary file /tmp/... Read-only`），`tmpfile()` 返回 NULL 后 `fileno(NULL)` 直接 SEGFAULT；标记计数只认 `Passed/Failed/Timeout/Skipped`，漏掉 `***Exception: SegFault`，失败被吞掉；Backtrace 断言依赖 `dladdr()` 解析自身符号，无 `--export-dynamic` 时在 OHOS/lld 下回退为 `unknown` | ① `conanfile._fix_fvec_tmpfile()`：先试 `tmpfile()`，失败则 `mkstemp($TMPDIR/$TMP/$TEMP/fvecXXXXXX)`（只换临时根目录，不删测试），`ASSERT_TRUE(tmp)` 使后续失败报 Failed 而非崩溃；② `_fix_backtrace_export_dynamic()`：给 `test_backtrace` 加 `LINKER:--export-dynamic`（GNU 行为不变）；③ `_run_upstream_tests()`：`Exception/SegFault` 计为失败、未知状态计失败、自动定位 `CTestTestfile` 目录 |
| 19b | `cmake.build()` at `core/src/tests/fvec.cc:70` reports `error: null character(s) preserved in char literal [-Werror,-Wnull-character]` on `buf.push_back('\0')` (92%, `fvec` target) | The #19 TMPDIR fallback built its mkstemp template as `vector<char> buf(tmpl.begin(), tmpl.end()); buf.push_back('\0');`. Clang's `-Wnull-character` fires on the `'\0'` char literal itself, and upstream builds with `-Werror`, so the recipe-injected line fails before any test runs. Evidence: preflight `fvec.cc:70:22: error ... buf.push_back('<U+0000>')` | Different strategy from #19 (no `push_back` at all): construct `vector<char> buf(tmpl.c_str(), tmpl.c_str() + tmpl.size() + 1)` so the NUL terminator is copied via the `c_str()` range; add explicit `<vector>` include guard plus migration of stale `push_back` text when a patched source is reused. Test semantics unchanged, `-Werror` untouched |

## 验证结果（待真机预检回填）

- `conan create`：待回填
- 上游 ctest（`gtest:*`，审计约 409 例）：以预检日志
  `HMBS_UPSTREAM_TEST_RESULT` 标记为准，待回填
- test_package（4 项：存在/可执行/ELF/`--version` 运行）：
  以 `HMBS_TEST_PACKAGE_RESULT` 标记为准，待回填

## 注意事项

1. `bareos-fd` 运行时需连接 Bareos Director（OHOS 上无），测试止于
   `--version` 可执行验证；实际备份功能需对接远端 Director。
2. 本轮新增 2 个补丁（见上表 #6 #7），`manifest.yaml` 的 `patches_applied`
   已同步；后续预检若暴露新的 OHOS 特有编译/测试失败，再按规范追加补丁。
3. `./hmbs/pr-body.md` 草稿中测试数据待预检 evidence 轮回填，
   不得沿用本笔记的审计数作为通过率。
