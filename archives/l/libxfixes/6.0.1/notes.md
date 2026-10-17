# libxfixes 6.0.1 适配笔记

## 编译环境
- 构建系统: autotools（X.Org 发布 tarball 自带 configure / Makefile.in，无需 autoreconf）
- 编译日期: 2026-08-31
- 编译器: clang/clang++ 15.0.4 (OHOS toolchain, /data/service/hnp/bin/clang)
- 目标平台: HarmonyOS PC aarch64 (os=OHOS, os.version=6.0, arch=armv8)
- 状态: built（`conan create` 通过，未 upload）

## 编译步骤（探索阶段，实测）

```bash
# 1. 下载 + 实测校验和
curl -fsSL -O https://www.x.org/releases/individual/lib/libXfixes-6.0.1.tar.xz
sha256sum libXfixes-6.0.1.tar.xz
# b695f93cd2499421ab02d22744458e650ccc88c1d4c8130d60200213abc02d58

# 2. 依赖（制品仓已发布，直接 install）
conan install --requires=libx11/1.8.13 --requires=xorgproto/2025.1 \
  -g PkgConfigDeps -pr ci/conan/profiles/ohos-aarch64 -r ohpcd --build=never

# 3. autotools 平台适配（见下表）
perl scripts/patch-autotools-ohos.pl config.guess config.sub
#   + 手工补 config.sub 的 kernel-OS 校验分支 linux-ohos*
#   + configure: umask 077 -> 022

# 4. 配置 / 编译 / 安装 / 上游测试
PKG_CONFIG_PATH=<conan generators>:<xorgproto share/pkgconfig> \
  ./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

产物（DESTDIR staging 实测）：
`lib/libXfixes.so.3.1.0`、`lib/libXfixes.a`、`lib/libXfixes.la`、
`lib/pkgconfig/xfixes.pc`、`include/X11/extensions/Xfixes.h`、`share/man/man3/Xfixes.3`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.guess: unable to guess system type` → `configure: error: cannot guess build type` | 上游 config.guess (2023-01-01) 没有 HarmonyOS 分支；且 config.guess 在 `$TMPDIR` 下建 dummy.c 时 `Permission denied` | E007：用 `scripts/patch-autotools-ohos.pl` 加 `*:HarmonyOS:*` 分支，输出 `aarch64-unknown-linux-ohos`（**禁止**用 `--build/--host` 绕过，会误判为交叉编译） → `patches/0001-config.guess.patch` |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub 的 `case $kernel-$os` 校验表缺 `linux-ohos*`；本 tarball 的 config.sub (2023-01-21) 用 `$kernel-$os` 形式，脚本内置正则只匹配 `$kernel-$os-$obj`（带 `-` 后缀）变体，因此 §3.3 只 patch 了一半 | 手工把 `linux-ohos*` 补进 `case $kernel-$os` 白名单（同时保留脚本已加的 `ohos-linux` triplet 与 `ohos*` OS 列表） → `patches/0002-config.sub.patch`。已用 `graph add --draft` 记录该脚本覆盖缺口 |
| 3 | `./config.status: can't create ./confXXXX/subs1.awk: Permission denied` | E002/HMDFS：`umask 077` 创建的临时目录在鸿蒙文件系统上不可写/不可执行内部脚本 | `umask 077` → `umask 022`（configure 内 2 处） → `patches/0003-configure.patch` |
| 4 | `libtool: error: '.../p/b/libxcb<hash>/p/lib/libxcb.la' is not a valid libtool archive` | 依赖包安装的 `.la` 文件里 `dependency_libs` 记录的是**依赖自身 build folder** 的 `.la` 绝对路径，该目录在依赖 `conan create` 结束后被清理 | 与 libx11/1.8.13 同策略：`build()` 内 `_fix_dep_la_files()` 只删除“指向不存在文件”的 `.la` 引用；`package()` 内 `_patch_libtool_libdir()` 把自身 `.la` 的 `libdir` 重写到最终 package 目录 |
| 5 | `make -j2` 报 `jobserver mkfifo: ... Operation not permitted` | 鸿蒙沙箱不允许创建 FIFO，GNU make 的 jobserver 不可用 | 平台限制，用 `-j1`；`conan create` 内 Conan 自行传 `-j`，实际未阻塞构建（仅打印告警） |
| 6 | configure 打印 `Package xorg-macros was not found` | xorg-macros(.pc) 只被 `XORG_*` 宏在 **autoreconf 阶段**需要；发布 tarball 已展开，运行期只是提示 | 非阻塞，无需处理（configure 仍 rc=0） |

注：libx11 recipe 里针对 RAWCPP `unix` 宏与 `< conftest` 重定向的补丁，libXfixes 的 configure **不需要**（它没有 `XORG_PROG_RAWCPP` 检查），实测未触发。

## 源码修改（补丁清单）

| 补丁 | 文件 | 内容 | 类型 |
|------|------|------|------|
| 0001-config.guess.patch | config.guess | 新增 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` | portability |
| 0002-config.sub.patch | config.sub | `ohos-linux` triplet + OS 列表加 `ohos*` + kernel-OS 校验加 `linux-ohos*` | portability |
| 0003-configure.patch | configure | `umask 077` → `umask 022`（2 处，config.status 临时目录） | portability |

均为平台可移植性补丁，不改 libXfixes 自身 C 源码（`src/*.c` 零修改，鸿蒙下无需 `#ifdef __OHOS__` 守卫）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| xorgproto | 2025.1 | xproto / fixesproto / xextproto 头 + .pc（`Xfixes.h` 依赖 `xfixeswire.h`、`Xfuncproto.h`） |
| libx11 | 1.8.13 | `x11 >= 1.6`，链接 `libX11`（间接带入 libxcb/libxau/libxdmcp） |

W0 依赖发布检查：`conan download xorgproto/2025.1 -r=ohpcd --only-recipe`、
`conan download libx11/1.8.13 -r=ohpcd --only-recipe` 均成功（已发布）。

## 验证结果

```bash
conan create archives/l/libxfixes/6.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r ohpcd --build=missing
# libxfixes/6.0.1: Package 'eab79208a9437a856077cc57885309d75bdb4a31' built
# libxfixes/6.0.1: Created package revision 57cf780c2de5ca4531bfe1e5e50136db
# libxfixes/6.0.1 (test package): RUN: ./test_libxfixes
#   no X server reachable — server-dependent checks skipped
#   libxfixes api smoke ok (33 symbols, 5 assertion groups)
```

- 上游 `make check`：rc=0，但输出 `Nothing to be done for 'check'`
  —— **libXfixes 6.0.1 上游没有任何测试用例**（0 PASS / 0 FAIL / 0 SKIP）。
  配方仍保留 `autotools.make(target="check")` 入口，如实记录，不美化。
- test_package：1 个用例 PASS（补齐上游测试空缺，见 `test_package/MANIFEST.yml`）。
  X server 相关分支在无 server 环境下按 Xlib 契约走 NULL 路径（如实标注为 skip 部分）。

## 注意事项

- `make check` 无用例是上游事实，不是本次跳过测试；测试覆盖完全依赖 test_package。
- 依赖 `.la` 修复函数会写入 **依赖包的 package folder**（只删除已失效引用），
  这是 X.Org 系列在本仓的既有做法（同 libx11/1.8.13），非本包引入。
- 未执行 `conan upload`（由 CI release 流水线负责），因此状态为 `built` 而非 `published`。
---

**编译结束**: 2026-08-31 12:27
**最终状态**: built
