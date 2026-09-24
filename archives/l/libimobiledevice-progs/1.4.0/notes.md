# libimobiledevice-progs 1.4.0 适配笔记

## 编译环境
- 构建系统: autotools（上游官方 release tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（clang 15.0.4，经 profile `tools.build:compiler_executables` 注入）
- 状态: built
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, armv8, clang 15, libc++）

## 包定位

上游 libimobiledevice 项目在同一源码树同时构建库与命令行工具。本包
`package_type="application"` 只交付 21 个工具（bin/），打包时删除上游全量
install 带来的 lib/include/share（libcpuid-tool 0.8.0 同款模式）。工具以
`--disable-shared --enable-static` 静态链入 1.4.0 源码树的库代码，不与已发布的
共享库包 libimobiledevice/1.3.0 冲突。

## 编译步骤

```bash
cd archives/l/libimobiledevice-progs/1.4.0
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方要点（家族先例：libimobiledevice/1.3.0、libimobiledevice-glue/1.3.0、libtatsu/1.0.5）：
- `--build=aarch64-unknown-linux-gnu`（config.guess 不识别 OHOS）
- `--enable-openssl`（无 gnutls/libtasn1）；`--without-cython`
- mktemp wrapper 返回失败，迫使 autoconf AS_TMPDIR 走 mkdir fallback（HMDFS 上
  `mktemp -d` 生成 drwx--S--- 目录，config.status 写 subs*.awk 失败）
- build() 内 `replace_in_file` 把 configure 的 `umask 077` 改 `umask 022`
- 依赖包 lib/*.la 改名 .bak（.la 内 libdir='//lib' 无效，libtool 递归解析报
  "not a valid libtool archive"，改后直接链 .a）
- `AutotoolsDeps` + `PkgConfigDeps` 双生成器；CC/CXX 显式注入（设备无 `cc`）
- `make -j1`（并行 make 撞 HMDFS jobserver fifo EPERM）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | generate() 报 `TypeError: ... NoneType`（libdirs 循环） | 部分依赖包 cpp_info.libdirs 含 None 项 | 循环前过滤 `None`/空 libdir 与空 package_folder |
| 2 | 链接 `undefined symbol: plist_dict_get_uint/plist_dict_copy_uint`（afcclient/idevicebackup2/idevicecrashreport/ideviceimagemounter） | 两函数是 libplist 2.6.0 新增 API，生态锁定的 libplist/2.3.0 没有 | patch 0001：逐字 backport 上游实现为 static inline（tools/plist_dict_compat.h），conanfile 按依赖版本注入 `-DLIBPLIST_LT_2_6=1` 门控（libtatsu/1.0.5 同族先例，其用 configure patch 做同一探测） |
| 3 | 编译 `use of undeclared identifier 'PLIST_OPT_NONE'`（afcclient.c） | 该枚举值同为 2.6.0 新增（plain 0） | compat 头内 `#ifndef PLIST_OPT_NONE #define PLIST_OPT_NONE 0 #endif` |
| 4 | `AutotoolsToolchain` 无 `extra_cppflags` 属性 | Conan 2.29 该 API 只在 CMakeToolchain 等存在 | 改用 `Environment().append("CPPFLAGS", ...)` 随 hmos_env 脚本注入 |
| 5 | plist_new_unix_date/plist_set_unix_date_val（2.7.0 API）缺失 | —— | 无需处理：上游用 `#ifdef HAVE_PLIST_UNIX_DATE` 门控，configure 探测失败自动走 `plist_set_date_val` 老路径 |

## 源码修改

- `patches/0001-compat-libplist-2.3.0-backport-dict-uint-helpers.patch`（strip: 1）
  - 新增 `tools/plist_dict_compat.h`：plist_dict_get_uint/plist_dict_copy_uint 的
    逐字上游实现（libplist 2.6.0 src/plist.c）为 static inline + PLIST_OPT_NONE 兜底
  - `tools/{afcclient,idevicebackup2,idevicecrashreport,ideviceimagemounter}.c`：
    在 `#include <plist/plist.h>` 后插入 `#ifdef LIBPLIST_LT_2_6 #include "plist_dict_compat.h" #endif`
  - 调用点全集实核：`grep -rln plist_dict_get_uint|plist_dict_copy_uint tools/ common/ src/`
    仅上述 4 文件；其余 5 个 2.6.0 dict helper（get_bool/copy_bool/copy_string/copy_data/copy_item）
    在本源码树零调用（未 backport，最小面）

## 依赖版本

| 依赖 | 版本 | configure.ac 要求 | 说明 |
|---|---|---|---|
| libusbmuxd | 2.0.2 | >= 2.0.2 | LIBUSBMUXD_VERSION |
| libplist | 2.3.0 | >= 2.3.0 | LIBPLIST_VERSION；生态 4 包（含本包）统一锁 2.3.0，升 2.7.0 会与 glue/tatsu 的直接依赖冲突 |
| libimobiledevice-glue | 1.3.0 | >= 1.3.0 | LIMD_GLUE_VERSION |
| libtatsu | 1.0.5 | >= 1.0.3 | LIBTATSU_VERSION |
| openssl | 1.1.1w | >= 0.9.8 | 默认 SSL 后端，与 libimobiledevice/1.3.0 一致 |
| readline | 8.3 | >= 1.0（可选） | 仅 afcclient；探测失败自动降级 |

## 验证结果

```bash
# 产物：bin/ 21 个工具全部打包（W3 轮 conan-create-r6.log "Packaged 22 files" 含 1 个 license 文件）
# 自含性（readelf -d bin/ideviceinfo）：
#   NEEDED: libcurl.so, libc.so
#   其余（libplist/libusbmuxd/glue/tatsu/openssl/readline/imobiledevice）全部静态链入
#   无 RUNPATH/RPATH
# libcurl.so 为传递动态依赖（libtatsu→libcurl/8.5.0 shared 包），运行需 conanrun env
# 提供 LD_LIBRARY_PATH（CI test_package 与 L2 均经 conanrun env 执行）
# test_package smoke（conanrun env，无设备安全子命令）：
#   idevice_id --version  -> "idevice_id 1.4.0"   OK
#   ideviceinfo --version -> "ideviceinfo 1.4.0"  OK
#   idevicepair --version -> "idevicepair 1.4.0"  OK
#   ideviceinfo --help    -> Usage 输出            OK
# 上游测试：上游无测试套件（1.4.0 release tarball 顶层 SUBDIRS 无 tests、无 check
# 注册用例），N=0；本包验证 = test_package 鸿蒙特有 smoke（MANIFEST.yml 分栏）
```

## 注意事项

- idevice_id -l 在无 usbmuxd 守护进程时返回非 0（"ERROR: Unable to retrieve device
  list!"），不是构建缺陷；无设备冒烟一律用 --version/--help。
- 运行期需要 conanrun env（libcurl.so）；直接裸调 bin 下工具会报
  "Error loading shared library libcurl.so"。
- 上游 1.3.0 的 patch（remove-plist-format-enum）在 1.4.0 已不需要（上游已修，
  `grep -rn plist_format_t common/ src/ tools/` 为空）。
