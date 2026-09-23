# Motif 2.3.8 适配笔记

## 编译环境

- 构建系统: autotools (configure + make，scope = `lib/`)
- 编译日期: 2026-09-13
- 编译器: clang / clang++ (OHOS SDK 26.0.0.18, `aarch64-linux-ohos`)
- Conan profile: `ci/conan/profiles/ohos-aarch64`（host 与 build 同 profile）
- 目标产物: `lib/libXm.so.4.0.4`（SONAME `libXm.so.4`）+ `include/Xm/*.h`
- 状态: built

## 源码与来源核验

- 上游：SourceForge "Motif 2.3.8 Source Code" 官方发布
  `https://sourceforge.net/projects/motif/files/Motif%202.3.8%20Source%20Code/motif-2.3.8.tar.gz`
- sha256：`859b723666eeac7df018209d66045c9853b50b4218cecadb794e2359619ebce7`
- 本机副本 `$HOME/tmp/dino/motif_mirror.tgz` sha256 与此**一致**（实测，见下）。
- **SF 镜像核验（已完成）**：从 SourceForge 官方镜像以 HTTP range 分块并行下载
  `motif-2.3.8.tar.gz` 全部 **5,704,328 字节** → `$HOME/tmp/dino/motif-sf-complete.tgz`，
  sha256 = `859b723666eeac7df018209d66045c9853b50b4218cecadb794e2359619ebce7`；
  与 `$HOME/tmp/dino/motif_mirror.tgz` 用 `cmp` 比对结果为**逐字节完全一致**。
  即 conandata.yml 的 SourceForge 官方 URL 所服务的内容与官方 sha256 **完全一致**
  ⇒ L0g/CI 源码 checksum 不可能不匹配。（SF 镜像单连接极慢 ~10-20 KB/s，故采用分块
  并行下载；**未做 Debian 重打包核验**——本适配只使用官方 SF 源，不使用 Debian 重打包。）

```bash
$ sha256sum "$HOME/tmp/dino/motif_mirror.tgz"
859b723666eeac7df018209d66045c9853b50b4218cecadb794e2359619ebce7  .../motif_mirror.tgz
```

## R51 上游测试清点（census）

Motif 2.3.8 **不提供正式测试套件**——全树没有任何注册的 `make check` 目标。
清点命令与数字（在 `motif-2.3.8/` 源码根目录执行，实测）：

```bash
$ find . -name Makefile.am | wc -l
109
$ grep -rn "check_PROGRAMS\|^TESTS\|check-local" --include=Makefile.am .
# 无输出（0 个匹配）
$ find demos -name '*.c' | wc -l
119
$ find demos/programs -name '*.c' | wc -l
67          # 分布在 33 个 demo 程序子目录（ButtonBox/ColorSel/hellomotif/...）
$ find clients -name '*.c' | wc -l
66          # 示例客户端，非自动化测试
```

结论：上游**注册 0 个测试用例**（0 项 / N=0）。但 `lib/` 是 automake 树，标准
`check` / `check-recursive` 目标存在，故 build() 在 `make -C lib` 之后显式调用
`make -C lib check -j1`（层1 上游测试，留下日志痕迹供 CI L1c 核验）。因上游 0 例，
`check` 无任何可运行项，故**上游通过率 = 0/0 = N/A**。实际功能验证以
**test_package 消费者测试**（R34）承担——链接 `libXm.so.4` 调用 XmString API +
`dlopen("libXm.so.4")` 解析 dinotrace 需要的入口点。实测结果见下方"验证结果"
（上游 N=0 → N/A；test_package assertions=18/18）。

## 编译步骤

configure 需要显式 X 路径（`--x-includes`/`--x-libraries` 指向 libx11 包），并只构建 `lib/`：

```bash
./configure \
  --host=aarch64-unknown-linux-gnu --build=aarch64-unknown-linux-gnu \
  --x-includes=<libx11>/include --x-libraries=<libx11>/lib \
  --disable-printing --disable-xft --disable-jpeg --disable-png \
  --enable-shared --disable-static
make -C lib -j1          # 只编译 Xm 与 Mrm
make -C lib install DESTDIR=<package_folder> -j1
```

配方内部：`build()` 先 `autotools.make(args=["-C","lib","-j1"])`，再
`autotools.make(args=["-C","lib","check","-j1"])`（层1 上游测试）；`package()` 用
`make -C lib install DESTDIR=<pkg> -j1`（configure `--prefix=/` + DESTDIR staging）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 全树 `make` 在 `tools/wml` 失败 | OHOS `ld.lld` 无法链接 host-only 的 `wmluiltok`（`undefined symbol: main`），见下 | 只构建 `lib/`（`make -C lib`），配方 scope 限定 `lib/` |
| 2 | `lib/Xm/I18List.c:38`、`lib/Xm/IconButton.c:35` `#include <X11/bitmaps/gray>` 找不到 | 该文件由 X.Org `xbitmaps` 提供，OHOS 制品仓未发布 | 在配方内附带 87 字节 canonical 数据文件 `files/X11/bitmaps/gray`，`CPPFLAGS` 加 `-I<source>/files`（**数据文件 shim，非代码补丁**） |
| 3 | 链接期 `rindex` 未定义（musl/OHOS） | `lib/Xm/XpmI.h` 仅在 `SYSV/SVR4/VMS/WIN32/_SVID_SOURCE` 下映射 `rindex` | `CPPFLAGS` 追加 `-Drindex=strrchr`（外科式修复，无补丁） |
| 4 | configure 在 HMDFS 上因 `umask 077` 生成的目录不可写 | E011（HMDFS 忽略 chmod，默认 umask 077） | `_patch_configure_runtime_shell()` 将 `configure` 内 `umask 077`→`022`，并把 shebang 改指向 OHOS shell |
| 5 | graph 报 `Version conflict: libx11/1.8.13 vs 6.4.0` | libxt/1.3.1 已发布二进制绑定 libx11/1.8.13，libxext 配方声明 libx11/6.4.0 | `self.requires("libx11/1.8.13", force=True)` 统一版本；改用 libxext/6.4.0.1（与 libxmu 相同组合），其二进制未发布→ `--build=missing` 自动重建 libxext |

### 问题 1 原始错误（全树 make，`tools/wml/wmluiltok`）

```
ld.lld: error: undefined symbol: main
>>> referenced by crt1.c:18 (.../sysroot/usr/lib/aarch64-linux-ohos/Scrt1.o:(_start_c))
>>> referenced by crt1.c:18 (.../lib/aarch64-linux-ohos/Scrt1.o:(_start_c))
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
make[2]: *** [Makefile:495: wmluiltok] Error 1
make[1]: *** [Makefile:394: all-recursive] Error 1
make: *** [Makefile:451: all-recursive] Error 1
```

（`wmluiltok` 由 `lex`(`.l`) 生成，host 工具链在 OHOS 上未生成 `main`——上游只在
本地 host 构建该工具，交叉编译时不属于目标产物。故 scope 限定 `lib/`。）

## 源码修改

无源码补丁。两处源码级 blocker 均以**环境/数据文件 shim** 解决（见上表 #2/#3）：
`files/X11/bitmaps/gray`（4 逻辑行、87 字节，MIT/X11，X.Org `xbitmaps` canonical 内容，
sha256 `b4df654f97ba9474c0d2b2f762c4db3d8613559447828a27f0bcfa2a0fcfc2aa`）+ `-Drindex=strrchr`。

## 依赖版本

- libx11/1.8.13（Xlib；libXm 头文件与运行期）— **force pin**：libxt/1.3.1 的已发布
  二进制（package_id `40beeeb2…`）绑定 libx11/1.8.13，而 libxext 配方声明 libx11/6.4.0；
  用 `force=True` 统一到 1.8.13，否则 graph 报 `Version conflict: ... libx11/1.8.13 vs 6.4.0`。
- libxt/1.3.1（Xt Intrinsics；`libXm.so.4` 的 DT_NEEDED）— 直接用已发布二进制。
- libxext/6.4.0.1（`<X11/extensions/shape.h>` + Xext 运行期）— 选用与 libxmu/1.3.1
  相同的已发布组合（该 revision 与 libx11/1.8.13 配套）。
- libsm/1.2.6、libice/1.1.2（libXt 依赖的运行期；缺则 `libXm.so.4` 加载失败）
- xorgproto/2025.1（xproto / 扩展协议头）

说明：`libXp`（打印）与 `libXmu` 未发布，因此 `--disable-printing`；`libxmu`/`libXp`
不作为依赖。libxext 的 6.4.0(.1) 二进制**未**为 libx11/1.8.13 配置发布，因此首次
`conan create` 会**从源码重建 libxext**（`--build=missing` 自动完成）；libxt/1.3.1 用
已发布二进制，不改动。Motif 自身链接只需 `-lXt -lXext -lX11`，libtool 直接链接成功。

## 验证结果

```bash
cd <REPO>
conan create archives/m/motif/2.3.8 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# EXIT_CODE=0
# 本地缓存: motif/2.3.8#47507d6a91774330b3377f25e64299af
#           package 0e71331f1621ab921cce02020f8f64874c596b27
# 注: recipe revision 由配方内容决定——CI 侧预下载会临时改写 conandata.yml，
#     其改写态构建出的 revision 与仓库原文不同（本机实测 #847d607f…），属预期。
```

### 层1 上游官方测试：`make -C lib check -j1`（build() 内执行，OBSERVED 原始行）

`lib/` 是 automake 树（`lib/Makefile.am`: `SUBDIRS = Xm Mrm`），build() 在 `make -C lib`
之后显式调用上游 `check` 目标。conan create 日志原始行：

```
motif/2.3.8: RUN: make -C lib check -j1
make: Entering directory '.../b/build-release/lib'
Making check in Xm
make  check-am
Making check in Mrm
make  check-am
make[2]: Nothing to be done for 'check-am'.
make[1]: Nothing to be done for 'check-am'.
make: Leaving directory '.../b/build-release/lib'
```

上游注册 **N = 0** 个测试用例（全树 109 个 `Makefile.am`，0 个 `check_PROGRAMS`/`TESTS`/
`check-local`），故 `check` 递归进入 Xm/Mrm 后**无任何可运行项**（
`Nothing to be done for 'check-am'`）。因此**上游通过率 = 0/0 = N/A**（不是跳过、不是失败）：
`make check` 目标确实被调用并留下日志痕迹（CI L1c），只是上游未注册任何用例。

### 层2 test_package 消费者测试（OBSERVED）

```
assertions=18 failures=0
```

即 test_package 断言 **18/18 通过（100%）**——与上游 0 例（N/A）相区分。

打包物（`conan cache path motif/2.3.8:0e71331f…`）：
`lib/libXm.so.4.0.4`（SONAME `libXm.so.4`，NEEDED libXt/libXext/libX11/libc）、
`lib/libMrm.so.4.0.4`、`include/Xm/*.h`（222 个）、`licenses/COPYING`。

详见 `reports/validation-report.md`（含依赖解析/构建缺口的完整证据）与
`reports/test-report.md`。XmStringLength 实测：len("Hello")=14、len("World")=18、
len(concat)=31 → 断言采用稳健关系（非求和）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libXm.so.4.0.4（+ `libXm.so.4`/`libXm.so` 符号链接） | Motif 主库 |
| lib/libMrm.so.* | Motif Resource Manager（随 `lib/` scope 一并构建/安装） |
| include/Xm/*.h（222 个头文件） | Motif 公共头文件 |
| licenses/COPYING | LGPL-2.1 |

（实测：`libMrm.so.4.0.4` 随 `make -C lib install` 一并安装，见 reports/validation-report.md。）

## 注意事项

- 只构建 `lib/`：demos/clients/tools 都不产出，且在 OHOS 上不可用（`wml`/`wmluiltok` host 工具）。
- `--disable-printing/--disable-xft/--disable-jpeg/--disable-png`：对应依赖（libXp/Xft/
  libjpeg/libpng）在本制品仓未发布或未适配，按 R26/依赖可用性关闭。
- `X11/Xmu/Editres.h` 在 OHOS 缺失，仅关闭 EditRes 功能，不影响 libXm ABI。
---

**编译结束**: 2026-09-13 04:51
**最终状态**: built
