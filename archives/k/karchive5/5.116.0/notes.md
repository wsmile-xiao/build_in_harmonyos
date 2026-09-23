# karchive5 5.116.0 适配笔记

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-20
- 编译器: clang/clang++ 15.0.4 (`aarch64-linux-ohos`)
- profile: `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 上游测试清点（R51 第一步）

| 测试入口 | 注册方式 | 用例数 | 说明 |
|---|---|---|---|
| `autotests/CMakeLists.txt` | `ecm_add_tests` / `ecm_add_test` | **5** | karchivetest / kfiltertest / deprecatedtest / klimitediodevicetest / kcompressiondevicetest |
| `tests/CMakeLists.txt` | `ecm_mark_as_test`（**无 `add_test()`**） | 5 个可执行文件 | kartest / ktartest / krcctest / kziptest /(k7ziptest) —— 上游未接入 CTest，属手工工具 |

> `tests/` 目录的 `CMakeLists.txt` 只调用 `ecm_mark_as_test(${_testname})`，
> **没有任何 `add_test()`**，所以上游自己的 `ctest` 也只跑 autotests 的 5 项。
> 实测这些可执行文件无参数运行时只打印 `Usage:` 并退出 1，确认是手工工具。

## 编译步骤

```bash
# 1. 源码（5.116 已归档至 KDE Attic；取 bfsu 镜像，官方 Attic 源兜底）
curl -fsSL -o karchive5-5.116.0.tar.xz \
  "https://mirrors.bfsu.edu.cn/kde/Attic/frameworks/5.116/karchive-5.116.0.tar.xz"
sha256sum karchive5-5.116.0.tar.xz
# 1663e3c970b84063ece7f28548a87c97bc7592e79da0a0afaa4f6354f8dea30a
# （与官方归档 download.kde.org/Attic/... 逐字节一致）

# 2. 依赖预检（W0）
bash ci/scripts/preflight_check.sh karchive5/5.116.0

# 3. 归档初始化 + 语言预检
python3 scripts/ohc-run.py init-build karchive5 5.116.0 \
  --url=https://mirrors.bfsu.edu.cn/kde/Attic/frameworks/5.116/karchive-5.116.0.tar.xz
python3 scripts/ohc-run.py lang-preflight karchive5 5.116.0 --src "$BUILD_SRC_DIR"
# → 语言匹配: task=cpp, detected=cpp

# 4. 完整构建 + 上游测试 + test_package
conan create archives/k/karchive5/5.116.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 图求解失败：`Version conflict: Conflict between zlib/1.3.1 and zlib/1.3.1.1` | `qt5-qtbase/5.15.2.2` 精确 pin `zlib/1.3.1`；配方直接 `requires("zlib/1.3.1.1")` 与之冲突 | 改用 `self.requires("zlib/1.3.1.1", force=True)` |
| 2 | `ERROR: Package 'zlib/1.3.1' not resolved: Cannot load recipe ... conanfile.py not found!` | Conan 本地缓存里 `zlib/1.3.1` 的 recipe 目录残留但 `conanfile.py` 缺失（早前下载中断） | `conan remove "zlib/1.3.1" -c` 后重新 `conan download`；缓存自愈 |
| 3 | 链接 `libKF5Archive.so` 报 `relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC` | 制品仓 `zlib/1.3.1` 的 `libz.a` 未以 `-fPIC` 编译（`zutil.o` 里是 `R_AARCH64_ADR_PREL_PG_HI21`/`ADD_ABS_LO12_NC`），无法并入共享库 | 换 `zlib/1.3.1.1`（同版本 `-fPIC` 重建，`zutil.o` 改用 GOT 相对 `R_AARCH64_ADR_GOT_PAGE`/`LD64_GOT_LO12_NC`）（方式与已有条目 E541 / E533 所记同源） |
| 4 | `ERROR: Duplicated requirement: zlib/1.3.1.1` | Conan 2 不允许同一 ref 声明两次（`force=True` + 普通 requires 并存） | 只保留一条 `force=True` 声明 |
| 5 | 编译 `karchive.cpp` / `kzip.cpp` 报 `fatal error: '../common/posix/qplatformdefs.h' file not found` | `_prepare_qt_mkspec_compat` 只复制了 `mkspecs/linux-clang/`，而该目录的 `qplatformdefs.h` 首行 `#include "../common/posix/qplatformdefs.h"`（兄弟目录） | 改为镜像**整个 `mkspecs/` 树**（ki18n5/kimageformats5 的 helper 只复制单目录，对不含 Qt 私有头的库够用，karchive 不够） |
| 6 | `CMake Error: Target "KF5Archive" links to: ZLIB::ZLIB but the target was not found` | 制品仓 zlib/bzip2/xz 配方未声明 `cmake_file_name`/`cmake_target_name`，CMakeDeps 只生成小写 `zlib::zlib`；且 `conan_toolchain.cmake` 强制 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，令 `find_package(ZLIB)` 命中 config 而非 CMake 自带 Find 模块 | 注入 `CMAKE_PROJECT_INCLUDE`（`project()` 之后、`find_package` 之前执行）把 `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 翻回 `OFF`，让 `FindZLIB`/`FindBZip2`/`FindLibLZMA` 生效（同款做法见 getdns 1.7.3） |
| 7 | `Imported target "PkgConfig::LibZstd" includes non-existent path "/usr/local/include"`；或 `-- Checking for module 'libzstd' -- No package 'libzstd' found` | 制品仓 `zstd/1.5.7` 的 `libzstd.pc` 硬编码 `prefix=/usr/local`（不可重定位），宿主 pkg-config 又不在包目录里找 | 在 `conan_cmakedeps_paths.cmake` 里预先定义 `PkgConfig::LibZstd` IMPORTED 目标 + `LibZstd_FOUND`，指向 Conan 包；`pkg_check_modules` 见到目标已存在便不再覆盖（同款做法见 akonadi 25.12.3） |
| 8 | `config-compression.h` 中 `HAVE_BZIP2_SUPPORT 0` / `HAVE_ZSTD_SUPPORT 0`：bzip2 与 zstd 后端被静默编译掉 | `src/CMakeLists.txt` 读 `${BZIP2_FOUND}` / `${LIBLZMA_FOUND}`，而 config 模式只设 `BZip2_FOUND` / `LibLZMA_FOUND`（大小写不符）；zstd 的 `pkg_check_modules` 又因 `.pc` 不可用而失败 | 同 #6：翻 `PREFER_CONFIG=OFF` 让 Find 模块运行时设置**大写**变量与 canonical target；zstd 由 #7 的 IMPORTED 目标兜底 |
| 9 | `karchivetest` 2 项 `FAIL`：`testUncompress(.tar.zst)` 报 `ZSTD_decompressStream returned ... Unknown frame descriptor`、`'totalSize > 26000' returned FALSE`；`testTarReadWrite(.tar.zst)` 报 `'f' returned FALSE` | `KTar::createDevice()` 用 `QMimeDatabase` 按文件名推断压缩类型。OHOS **不带系统 shared-mime-info 数据库**（`/usr/share/mime` 不存在），`QMimeDatabase` 只能看到 Qt 内建类型集（实测 779 条），该集合含 `application/x-compressed-tar` / `x-bzip-compressed-tar` / `x-xz-compressed-tar`，**唯独没有 zstd 条目** → `.tar.zst` 落回 `application/octet-stream` → `KTar` 不加压缩直接写普通 tar（实测文件头是 `mediumfile` 而非 zstd magic `28 B5 2F FD`），解压自然失败 | 生成**测试专用** shared-mime-info 数据库（含 `application/zstd`、`application/x-zstd-compressed-tar`、`x-gzdvi` 等），经 `XDG_DATA_DIRS` 仅对测试运行暴露（仓库内 `karchive` 6.26.0 / `kcontacts` / `kfilemetadata` / `gtksourceview3` 已有同款做法） |
| 10 | `kfiltertest` 新增 `test_findFilterByMimeType(application/x-gzdvi)` FAIL | 自建 MIME 库第一版漏了 `application/x-gzdvi` 条目，`compressionTypeForMimeType` 的继承分支（`inherits("application/x-gzip")`）无法命中 | MIME 库里补 `application/x-gzdvi`（`sub-class-of application/x-gzip`） |
| 11 | test_package 编译报 `no matching constructor for initialization of 'KCompressionDevice'` | `KCompressionDevice(QIODevice*, CompressionType)` 在 KF5 只有 3 参形式 `(QIODevice*, bool autoDeleteInputDevice, CompressionType)` | 测试源改用 3 参构造 |
| 12 | test_package 运行报 `Error loading shared library libzstd.so.1 (needed by libKF5Archive.so)` | `libKF5Archive.so` 的 `DT_NEEDED` 含 `libzstd.so.1`，但 `test()` 只加了 qtbase 与被测包的 lib 目录 | `test()` 遍历 `self.dependencies.values()`，把所有依赖的 `lib/` 都前置进 `LD_LIBRARY_PATH` |
| 13 | **CI 红：源码下载超时**（类别「网络问题」，Worker 网络受限） | 两个叠加原因：①`download.kde.org` **不在 CI mirror-fallback 白名单内**（`ci/conan/build_and_test.sh` 只覆盖 github/gnu/gnome/kernel.org/sourceforge 等域名），CI 不会为其自动追加镜像；②5.116 已归档，`stable/frameworks/5.116/...` 会经 `stable/` → `Attic/` → 境外镜像（ftp.kaist.ac.kr）**两跳 302**，受限 Worker 无法完成该重定向链 | `conandata.yml` 改用 **url 列表**（Conan 2 `get()`/`download()` 原生支持：优先第一条，失败按序回退）：`mirrors.bfsu.edu.cn` / `mirrors.ustc.edu.cn` / `mirror.nju.edu.cn` 三个国内镜像在前 + `download.kde.org/Attic/...` 官方源兜底。四条目均实测 HTTP 200，镜像 SHA256 与官方归档**逐字节一致**（`1663e3c9…`）。官方源保留满足 R39。本地实测构建日志确认：`Sources correctly downloaded from https://mirrors.bfsu.edu.cn/...`。同款做法见 `archives/l/libkdepim/25.12.3`（同为 KDE Attic + bfsu 镜像）与 `archives/a/accel-config/4.1.9`（`url:` 列表 + 标准 `get()`） |

## 源码修改

**无补丁**（`patches_applied: []`）。全部问题均在 `conanfile.py` / `test_package/`
层面解决，未修改上游源码，`conandata.yml` 的 `patches` 为空。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|---|---|---|---|
| qt5-qtbase | 5.15.2.2 | 强制（编译+链接，`Qt5::Core`） | KF5 链统一 Qt5 基座 |
| zlib | **1.3.1.1** | 强制（`force=True` 覆盖 qt5-qtbase 的 1.3.1 pin） | `-fPIC` 重建版，`ZLIB::ZLIB` |
| bzip2 | 1.0.8 | 推荐（`TYPE RECOMMENDED`） | `BZip2::BZip2` |
| xz | 5.6.2 | 可选（`find_package(LibLZMA)`） | `LibLZMA::LibLZMA` |
| zstd | 1.5.7 | 可选（`pkg_check_modules`） | `PkgConfig::LibZstd` |
| ecm | 6.26.0 | 构建工具（`tool_requires`） | 满足 `find_package(ECM 5.116.0)` 的最低版本语义 |

## 验证结果

```bash
$ conan create archives/k/karchive5/5.116.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
!!!EXIT=0
```

**上游 autotests（ctest，实际执行）**

| # | 用例名 | 结果 | 耗时 |
|---|---|---|---|
| 1 | `karchivetest` | **Passed** | 3.86 s |
| 2 | `kfiltertest` | **Passed** | 0.07 s |
| 3 | `deprecatedtest` | **Passed** | 0.03 s |
| 4 | `klimitediodevicetest` | **Passed** | 0.03 s |
| 5 | `kcompressiondevicetest` | **Passed** | 0.10 s |

```
100% tests passed, 0 tests failed out of 5
Total Test time (real) =   4.10 sec
```

用例总数 **5**、通过 **5**、失败 **0**、跳过 **0**。

**压缩后端完整性（R40）**

```c
#define HAVE_BZIP2_SUPPORT 1
#define HAVE_XZ_SUPPORT 1
#define HAVE_ZSTD_SUPPORT 1
```

四个后端（gzip / bzip2 / xz / zstd）全部编入，未做任何功能裁剪。

**`tests/` 手工工具实测（上游未接入 CTest，另行执行）**

| 工具 | 命令 | 退出码 | 结果 |
|---|---|---|---|
| `kartest` | `./kartest t.a` | 0 | 正确列出 `a.txt` / `b.txt` 及大小 |
| `ktartest` | `./ktartest t.tar.gz` | 0 | 正确列出目录树与大小 |
| `kziptest` | `./kziptest list t.zip` | 0 | 正确列出条目 |
| `kziptest` | `./kziptest create new.zip a.txt` → `list` | 0 | ZIP 创建→回读往返成功 |
| `krcctest` | 用法提示（需 .tar.gz 参数） | — | 手工工具，无自动化断言 |

**test_package（conan create 内实际执行）**

```
1/1 Test #1: test_karchive5 ...................   Passed
100% tests passed, 0 tests failed out of 1
```

26 项断言全过，覆盖 KZip 写入 / 重开 / 目录树遍历 / 载荷逐字节往返，
以及 GZip 往返与 BZip2 / Xz / Zstd 三个后端的实际压缩输出。

日志路径：

- `.ci_logs/karchive5-adapt/create-20-final.log`（干净重跑，exit 0）
- `.ci_logs/karchive5-adapt/test-package-assertions.log`（26 项断言明细）
- `.ci_logs/karchive5-adapt/upstream-tests-tests-dir.log`（`tests/` 手工工具）
- `.ci_logs/karchive5-adapt/w0-dep-check.log`（W0 依赖可消费性）

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libKF5Archive.so` | 归档库共享对象（含 4 个压缩后端） |
| `include/KF5/KArchive/*.h` | 14 个公开头文件 + `karchive_version.h` |
| `include/KF5/KArchive/karchive_export.h` | ECM 生成的导出宏 |
| `lib/cmake/KF5Archive/*.cmake` | `KF5ArchiveConfig.cmake` / `ConfigVersion` / `Targets`（导出 `KF5::Archive`） |
| `share/qlogging-categories5/karchive.categories` | 日志分类 |
| `mkspecs/modules/qt_KArchive.pri` | qmake 模块声明 |

## 注意事项

1. **`force=True` 而非 `override=True`**：`override=True` 会让 `zlib` 变成
   非消费型依赖，`self.dependencies.get("zlib").package_folder` 返回 `None`，
   导致 `conan_cmakedeps_paths.cmake` 里发不出 Find 模块的搜索根（现象是
   `list(PREPEND CMAKE_PREFIX_PATH "None")`），ZLIB 永远找不到。
   `force=True` 既解决版本冲突又保留消费语义。
2. **`CMAKE_PROJECT_INCLUDE` 注入时机**：`conan_toolchain.cmake` 在
   find_paths block 里**无条件** `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`，
   比 `-D` cache 注入晚，所以只能用 `CMAKE_PROJECT_INCLUDE`（在 `project()`
   之后、`find_package` 之前）覆盖。
3. **MIME 数据库仅用于测试**：`test-mime/` 目录位于 build folder 内，通过
   `XDG_DATA_DIRS` 只影响测试进程；不会进入 Conan 包，也不影响下游消费者。
4. **HMDFS jobserver fifo**：`make -j20` 报
   `jobserver mkfifo: ... Operation not permitted`，属平台已知限制，
   构建仍正常完成（Conan 回退到串行 jobserver 语义）。
5. **`tests/` 不是自动化测试**：上游 `tests/CMakeLists.txt` 不含
   `add_test()`，勿把其可执行文件误报为 CTest 用例。

## 本版本无补丁

`patches/` 为空目录，`conandata.yml` 的 `patches: "5.116.0": []`。
所有适配均在配方与测试工程层面完成。
---

**编译结束**: 2026-09-21 16:36
**最终状态**: built
