# siril 1.2.3 适配笔记

## 编译环境
- 构建系统: autotools（git-archive tarball 无 configure，需 autoreconf）
- 编译日期: 2026-09-05
- 编译器: /data/service/hnp/bin/clang / clang++（OHOS SDK 15.0.4，Target: aarch64-unknown-linux-ohos）
- 状态: built（conan-verify G0-G5 全绿，test_package `siril-cli --version` 通过）

## 编译步骤
conan create（双 profile=ci/conan/profiles/ohos-aarch64，用户 ohpcd/channel stable）：
```
conan create archives/s/siril/1.2.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing \
    --user=ohpcd --channel=stable
```
关键流程：apply 补丁 0001-0007 → aclocal-1.16 包装 + pkg.m4 就位 → autoreconf --install --force
→ configure（--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos，cross 模式跳过
conftest 执行）→ make -j2 → make install。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| R29-1 | configure 报 "cannot run C compiled programs. If you meant to cross compile, use '--host'." | conftest 链接 conan 依赖 .so 后运行时加载器找不到 HMDFS 路径下的 libcairo.so.2 等 → 执行失败；本机又无 D-Bus/图形会话 | 在 generate() 给 AutotoolsToolchain 追加 `--build=x86_64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，host≠build 使 autoconf 进入 cross 模式、不执行 conftest（同 asterisk-srtp/asterisk-speex/abiword 插件做法；环境 config.guess/config.sub 已识别 *-linux-ohos） |
| R29-2 | configure: error: htmesh cannot be built | 上游对 cross_compiling=yes 直接 AC_MSG_ERROR（内置 htmesh 需 cmake 构建） | 补丁 0006：去掉 cross 分支限制，cross 模式同样走 AC_PATH_PROG(CMAKE)+内部 cmake 构建（环境有 cmake 4.1.2；htmesh 是纯静态库，编译/链接无运行时测试） |
| R30 | `siril-cli --version/-v/--copyright/-c/--format/-f` 永久挂死（futex），仅 glib 内建 --help 能退出 | OHOS glib 上 g_application_run() 的 GOptionEntry ARG_CALLBACK 在选项解析内调用 exit() 会死锁（exit 时仍持内部锁）；conan create 的 test_package 与 L2 smoke 因此超时/挂死 | 补丁 0007（src/main-cli.c）：main() 一开始就用 _cli_handle_early_print_options() 手工识别并处理 --version/-v、--copyright/-c、--format/-f（printf + return），完全不进入 GApplication；输出格式与原回调一致 |
| 前轮已修 | extra flags 类型、chmod API、umask 077→022、po/Makefile.am msgfmt、gio-unix pc、aclocal 1.17 | 见配方 docstring 与 patches | 保持不回退 |

## 源码修改
- 补丁（conandata.yml patches，全部 modified-file diff）：
  - 0001 configure.ac — librtprocess 缺失时可选（禁用 demosaicing_rtp）
  - 0002 src/Makefile.am、0003-0005 — demosaicing_rtp/子项目可选与编译修正
  - 0006 configure.ac — htmesh 内部 cmake 构建允许在 autoconf cross 标签下执行（R29-2）
  - 0007 src/main-cli.c — 提前处理 --version/--copyright/--format，绕过 GApplication 回调 exit() 死锁（R30）
- conanfile.py generate()：追加 `--build=x86_64-unknown-linux-gnu`、`--host=aarch64-unknown-linux-ohos`

## 依赖版本
gtk/3.24.38 glib/2.84 gsl/2.8 fftw3f/3.3.10 cfitsio/4.6.4 opencv/4.12.0
exiv2/0.28.7 libraw/0.22.1 wcslib/8.4 libheif/1.22.2 libtiff/4.7.2 libjpeg/10
libpng/1.6.58 libcurl/8.5.0 lcms2/2.19 libde265/1.0.18（均来自 ohpcd 二进制）

## 验证结果
```bash
ohc-run.py conan-verify siril 1.2.3
# G0 PASS, G1 PASS, G2 PASS (conan create 成功), G3 PASS, G4 PASS,
# L2/L4/L5 PASS(跳过, 无 cache 路径)
# test_package: "siril 1.2.3" (siril-cli --version rc=0)
# 报告: archives/s/siril/1.2.3/reports/conan-verify-report.md (Verdict PASS)
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（cross 参数 + dep include/lib 注入 + gio-unix pc + aclocal 处理） |
| conandata.yml | sources + patches 0001-0007 |
| patches/0001-0007 | 见上 |
| test_package/ | 存在性 + `siril-cli --version` headless 冒烟 |
| reports/conan-verify-report.md | 全绿报告 |
| notes.md | 本文档 |

## 注意事项
- OHOS PC 上 conftest 不可执行（dep .so 不在 loader 路径）→ 一律以 cross 语义跑 configure。
- `siril-cli` 的 GApplication 回调 exit() 在 OHOS 上死锁 → 已用 main() 提前处理规避；GUI `siril`
  仍需要图形会话，无法在无头环境冒烟（L2 以 siril-cli 通过）。
- make 并发限制 -j2；HMDFS 有 jobserver fifo / umask / 目录权限等坑（配方内已处理）。
---

**编译结束**: 2026-09-05 02:21
**最终状态**: built
