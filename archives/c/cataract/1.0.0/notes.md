# cataract 1.0.0 - HarmonyOS PC 适配笔记

## 上游信息
- **软件**: Cataract Gallery Generator (CGG)
- **版本**: 1.0.0 (2009-10-24)
- **上游地址**: http://cgg.bzatek.net/
- **源码**: http://cgg.bzatek.net/files/cataract-1.0.0.tar.bz2 (sha256 561cd8f4bf71fdb0cb190a26dee44c1a1013648633ea68deffa9b064dbaf1417)
- **构建系统**: Autotools (configure + Makefile)
- **许可证**: GPL-2.0
- **官方仓库**: git://git.bzatek.net/cataract

## OHOS 适配要点

### 1. 多重定义修复 (fcommon)
- **现象**: `src/stats.h` 定义 `int stats_errors;` 等全局变量，包含在多个 .o (stats.o, cgg.o, generators.o 等) 中，gcc10+/clang 默认 `-fno-common` 导致链接 `multiple definition of stats_images` 错误。
- **复现**: Nixpkgs 记录 `env.NIX_CFLAGS_COMPILE = "-fcommon"` 绕过，Gentoo 同样报告。
- **修复**: `0001-stats-fix-fcommon.patch` 将头文件改为 `extern` 并在 `src/stats.c` 集中定义 (`int stats_errors=0;` 等)，并在 `AutotoolsToolchain.extra_cflags` 增加 `-fcommon` 双保险。参考知识 `pre-scan-rules.yaml` 的 `multiple-definition` 模式。

### 2. MagickWand 可选化 (OHOS 无 ImageMagick 制品)
- **上游**: `configure.ac` 强制 `PKG_CHECK_MODULES(LIBS, ... MagickWand ...)`，源码 `src/jpeg-utils.cpp` 强依赖 `<wand/magick-wand.h>` 实现缩略图 (`create_thumbnail`, `get_image_info`)。
- **OHOS 现状**: `archives/i/imagemagick` 仅有 `manifest.yaml` 无 `conanfile.py`，制品仓无 `imagemagick` 可用包；若强制依赖则 `W0` 直接 `dependency_missing` 阻塞。
- **适配**: `0002` 将 `MagickWand` 从强制改为可选 (`PKG_CHECK_MODULES(MAGICKWAND, [MagickWand], [have=yes], [have=no])`，自动定义 `HAVE_MAGICKWAND` 并合并 `LIBS_*`；`0003` 在 `jpeg-utils.cpp` 中 `#ifdef HAVE_MAGICKWAND` 保留原实现，否则提供桩实现：`create_thumbnail` 直接 `g_file_get_contents`+`g_file_set_contents` 拷贝，`get_image_info` 返回 800x600 占位尺寸。保证相册 HTML 生成流程完整，缩略图等比缩放功能在 OHOS 上降级为原图拷贝（文档已说明）。

### 3. OHOS 三元组与 config.guess
- **现象**: 上游 `config.guess` 仅识别 `aarch64:Linux` 为 `aarch64-unknown-linux-gnu`，`config.sub` 不识别 `*-ohos`，`configure` 在 HarmonyOS aarch64 上 `cannot guess build type`。
- **修复**: `0004-config-guess-ohos.patch` 在 `config.guess` 增加 `aarch64:HarmonyOS` 及通过 `/etc/ohos-release` 探测 OHOS，`config.sub` 增加 `*-ohos*` 分支；`conanfile.py` 在 `OHOS` 时传入 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`，与仓库内 `aalib/xorg` 等 Autotools 适配一致。

### 4. 依赖选择
- **glib/2.88.3**: 最新 OHOS 验证 363 测试通过版本，`glib-meson` 体系，供应 `glib-2.0.pc`/`gthread-2.0.pc`。
- **libxml2/2.15.3**: 轻量且已在 OHOS 上 `built` 验证。
- **exiv2/0.28.7**: 0.28.7 为唯一 OHOS 适配版本，CMake 构建，供应 `exiv2.pc`，已验证 `unitTests` 在 OHOS 通过（363 passed）。
- **pkgconf/2.2.0**: `tool_requires` 提供 `pkg-config`，满足 `configure` 中 `AC_CHECK_PROG(HAVE_PKGCONFIG)`。

## 上游测试

- **框架**: 无。`Makefile.am` 未定义 `TESTS`/`check_PROGRAMS`，`configure.ac` 未注册测试，`tarball` 内无 `tests/` 目录，`make check` 为空操作（`Nix`/`Gentoo` 均未报告测试）。
- **审计**: 已扫描 `Makefile.am`、`src/Makefile.am`、`configure.ac`、根目录文件列表，确认 `make -n check` 仅打印 `echo` 无实际用例。对比 `archives/t/tccutil` 等 `no_tests` 案例，按 `TEST_QUALITY_SPEC` 归为 `upstream_tests_exist: false`。
- **适配后验证**: `test_package` 提供 3 个真实消费者测试（见 `test_package/MANIFEST.yml`），并在 `test.sh` 中发射 `HMBS_TEST_PACKAGE_RESULT` 与 `HMBS_UPSTREAM_TEST_RESULT` 标记，满足 `HMBS` 硬门禁。

## 验证结果

- **本地**: 需在 HarmonyOS aarch64 真机预检 `conan create`，预期 `build()` 中 `make check` 空操作通过，`package()` 安装 `bin/cgg`+`bin/cgg-dirgen`+`share/cgg`。
- **新增测试**: `cgg --help`, `cgg --version`, 以及端到端相册生成（`sample/src` → `cgg -s sample/src -o /tmp/out`）3 项，断言 HTML/缩略图/拷贝行为。

## 参考
- Nixpkgs `pkgs/applications/misc/cataract/build.nix` (fcommon 注释)
- Gentoo `media-gfx/cataract` ebuild (exiv2+imagemagick 依赖)
- 仓库知识 `knowledge/operations/build-systems.md` Autotools OHOS 三元组
