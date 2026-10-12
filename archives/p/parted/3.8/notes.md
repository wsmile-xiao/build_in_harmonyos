# parted 3.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-10-01
- 编译器: clang 15.0.4 / clang++ 15.0.4（hnp clang；profile: os=OHOS 6.0, arch=armv8, Release）
- 状态: built

## 编译步骤

1. `conan create archives/p/parted/3.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. `source()`: 下载 parted-3.8.tar.xz（sha256 校验），无补丁。
3. `generate()`: `_deps_view()` 把 libuuid/libblkid/readline(→ncurses)/libdevmapper 的
   实体库与头文件收进 `<build>/prefix` 私有视图（跳过 .la，补 libncurses.a 副本），
   `TMPDIR` 指向 build 目录（设备 /tmp 只读）。
4. `build()`: 覆盖 `CONFIG_SHELL/SHELL=/bin/sh`；`configure`/`config.status` 内
   `umask 077→022`；`configure` 参数：
   `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
   --disable-nls --disable-rpath`（路径布局不由 configure 传参，`sbin/→bin/`
   等迁移由 `package()` 兜底，与 manifest.yaml 口径一致）；configure 后、make 前清空构建树 `libtool`
   的 `hardcode_libdir_flag_spec`/`hardcode_libdir_separator`（真抑制 RUNPATH）；
   `make -j1`。
5. `package()`: `make install` 后实体化 `lib/` 软链（E316）、`sbin/→bin/`（R38）、
   删除 libtool `.la`（P3：内含 `libdir='//lib'` 与已失效的构建树绝对路径）、
   归档 COPYING 至 `licenses/`。
6. `package_info()`: `libs=["parted"]`、`bindirs=["bin"]`、`libdirs=["lib"]`、
   `pkg_config_name="libparted"`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | E011: config.status 生成失败 | HMDFS 上 `umask 077 && mkdir ./confXXXXXX` 建出的临时目录不可写 | recipe 内将 `umask 077` 替换为 `umask 022` |
| 2 | E074: make jobserver fifo EPERM | HMDFS 不支持 make jobserver fifo | `autotools.make(args=["-j1"])` 固定单并发 |
| 3 | `configure: error: working directory cannot be determined` | profile buildenv 的 `CONFIG_SHELL=hnp bash` 在 HMDFS 上 getcwd 失败；autoconf 2.72 在 CONFIG_SHELL 非空时无条件 `exec $CONFIG_SHELL` | `build()` 末尾向 `conanbuild.sh` 追加 `export CONFIG_SHELL=/bin/sh; SHELL=/bin/sh` |
| 4 | config.guess 无法运行 | HMDFS（getcwd/临时文件权限） | 显式 `--build/--host=aarch64-unknown-linux-ohos`（config.sub 原生支持 ohos*，实测通过） |
| 5 | `make install` 触发 makeinfo（Error 127） | tarball 缺 version.texi/stamp-vti，parted.info 被判定过期 | `_prep_doc_info()` 预置 version.texi/stamp-vti 并按 mtime 顺序安装上游自带 parted.info |
| 6 | E316: 运行时不识别 libparted.so.2 | OHOS musl 不能加载「SONAME 名为软链」的库 | `package()` 将 `lib/` 下软链实体化（follow_symlinks 复制后替换） |
| 7 | RUNPATH=//lib 违规（R26/R53） | libtool 2.5.4 默认 `hardcode_libdir_flag_spec="\$wl-rpath \$wl\$libdir"`；automake 以 `-rpath $(libdir)` 链接 libparted.la → `-Wl,-rpath //lib`（prefix=/ 时 libdir=//lib，POSIX 上 ≡ 系统 /lib），并传导到链接 libparted.la 的 parted/partprobe。configure 的 `--disable-rpath` 实为 gnulib `m4/lib-link.m4` 的选项（gettext 链接探测），不影响该变量（W4 审计实测 libtool 变量未变） | `build()` 在 configure 后、make 前清空构建树 libtool 的 `hardcode_libdir_flag_spec`/`hardcode_libdir_separator`（若有旧对象则 `make clean` 强制重链）→ readelf 实测 bin/parted、bin/partprobe、libparted.so.2、libparted-fs-resize.so.0 均无 DT_RUNPATH/DT_RPATH；**不用 patchelf**：改写 ELF 会破坏 `.codesign` 段（本机实测 rc=126） |
| 8 | R38: 命令不在 bindirs | 上游安装 parted/partprobe 到 `sbin/` | configure `--sbindir=$prefix/bin` + `package()` 兜底迁移 `sbin→bin`；附软件级 commands.json |
| 9 | R49: 依赖探测不到 | parted 用 `AC_CHECK_LIB/AC_SEARCH_LIBS` 裸探测，AutotoolsToolchain 只注入 PKG_CONFIG_PATH | `_deps_view()` 私有 prefix：收集实体 `.a/.so` 与 include；跳过 `.la`（其 libdir=//lib 失效）；补 `libncurses.a` 副本（parted 探测 `-lncurses`，ncurses 包只装 libncursesw.a） |

## 源码修改

无源码补丁（`patches/` 为空）；全部适配通过 conanfile.py 内的构建脚本/参数完成。

> 提交前清理说明：探索期 `refresh-patch` 曾捕获 8 个中间态 diff（生成文件 sed / 文档 stamp / 测试辅助脚本），经核查均未接入 conandata、无构建必要性（等价修复已固化于 recipe），按 ARCHIVE-SPEC「有则保留，无则不创建」于提交前移除；本包不携带补丁。

## 依赖版本

- libuuid/2.42.2（必需，`AC_CHECK_LIB uuid`）
- libblkid/2.42.2（探测式，显式提供以保留块设备签名识别）
- readline/8.3（默认开启；传递依赖 ncurses/6.6，静态）
- libdevmapper/1.02.198（device-mapper 默认开启）

## 验证结果

```bash
# conan-verify（修复 DT_RUNPATH 后重跑，PASS；见文末更新）
OHC_PROJECT_DIR=... python3 .../ohc-run.py conan-verify parted 3.8
# G0/G1/G2/G3/G4 PASS；报告: archives/p/parted/3.8/reports/conan-verify-report.md

# test_package（conan create 内真实执行包内二进制，R34）
#   test.sh      : 10/10 断言 PASS（--version、mklabel gpt、mkpart、print、unit、rm、
#                  --json、msdos+fat32 类型路径）
#   test_ohos.sh : 13/13 断言 PASS（R53：平台身份、ELF64/AArch64/PIE、musl 解释器、
#                  无 glibc NEEDED、.note.ohos.ident、.codesign、RUNPATH/RPATH 无
#                  系统目录（断言 9 先归一化重复斜杠，//lib ≡ /lib 可拦）、
#                  libparted.so.2、任意 cwd、载荷完整）

# R51 上游测试套件（受控辅助环境：TEMP=~/tmp、bash harness、truncate/id 垫片、
#   python3/perl shebang 修正、NDEBUG-free 测试程序；不改产品代码）
#   tests/          : 101 total = 59 PASS / 37 SKIP / 5 FAIL
#                     （环境修正前原始直跑: 42 PASS / 37 SKIP / 22 FAIL）
#   libparted/tests :   6 total =  4 PASS /  2 SKIP / 0 FAIL（2 SKIP 均因无 root/id）
#   5 FAIL 均为环境限制：交互 pty 回显差异 ×2、缺 mke2fs/mkswap/locale ×3，
#   逐项根因见 reports/test-report.md
```

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/parted`、`bin/partprobe` | CLI 工具（上游 sbin 合并至 bin） |
| `lib/libparted.so.2`、`lib/libparted-fs-resize.so.0` 等 | 实体化共享库（E316），SONAME=libparted.so.2 |
| `lib/libparted.a`、`lib/libparted-fs-resize.a` | 静态库 |
| `include/parted/*.h` | 头文件（11 个） |
| `lib/pkgconfig/libparted.pc` 等 | pkg-config 元数据 |
| `share/man/man8/*.8`、`share/info/parted.info` | 手册 |

## 注意事项

- 设备无 root 且 /tmp 只读：上游 `make check` 的 root/loop/dm 类测试 SKIP；
  `---pretend-input-tty` 交互测试存在 pty 回显差异（非功能缺陷）。
- RUNPATH 抑制靠 configure 后清空构建树 libtool 的 `hardcode_libdir_flag_spec`
  （R26/R53）；上游 libtool 升级时需复核该行格式与 `_suppress_libtool_rpath()`
  正则。禁止用 patchelf 等后处理 ELF（会破坏 `.codesign` 段，产物 rc=126 无法执行）。
- E316 实体化后 `libparted.so` 与 `libparted.so.2` 均为真实文件（同内容），
  运行时由 conanrun `LD_LIBRARY_PATH` 解析；升级版本时保持该策略一致。
- 静态链接 libparted 时需自行补依赖（uuid/blkid/readline/devmapper）：
  upstream `libparted.pc` 无 `Requires.private`，仅提供 `-lparted`。
---

**编译结束**: 2026-10-01 16:41
**最终状态**: built
