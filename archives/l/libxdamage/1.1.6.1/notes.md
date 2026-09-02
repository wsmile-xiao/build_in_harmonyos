# libxdamage 1.1.6.1 适配笔记

## 编译环境
- 构建系统: autotools（X.Org 发布 tarball 自带 configure / Makefile.in，无需 autoreconf）
- 编译日期: 2026-08-31
- 编译器: clang/clang++ 15.0.4 (OHOS toolchain, /data/service/hnp/bin/clang)
- 目标平台: HarmonyOS PC aarch64 (os=OHOS, os.version=6.0, arch=armv8)
- 状态: built（`conan create` 通过，未 upload）

## 编译步骤（探索阶段，实测）

```bash
# 1. 下载 + 实测校验和
curl -fsSL -O https://www.x.org/releases/individual/lib/libXdamage-1.1.6.tar.xz
sha256sum libXdamage-1.1.6.tar.xz
# 52733c1f5262fca35f64e7d5060c6fcd81a880ba8e1e65c9621cf0727afb5d11

# 2. 依赖（制品仓已发布 xorgproto/libx11/libxext/libxfixes，对齐 cmd-pkgs 主线依赖链）
conan install --requires=libx11/6.4.0 --requires=libxext/6.4.0 \
  --requires=xorgproto/2025.1 --requires=libxfixes/6.1.0 -g PkgConfigDeps \
  -pr ci/conan/profiles/ohos-aarch64 --build=missing

# 3. autotools 平台适配（config.guess 2021-06-03 / config.sub 2021-08-14 / configure）
#    config.guess: 加 *:HarmonyOS:* 分支 → aarch64-unknown-linux-ohos
#    config.sub:   ohos-linux triplet + ohos* OS 列表 + linux-ohos* kernel-OS 校验
#    configure:    umask 077 -> 022（2 处）

# 4. 配置 / 编译 / 安装 / 上游测试
PKG_CONFIG_PATH=<conan generators>:<xorgproto share/pkgconfig> \
  ./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

产物（DESTDIR staging 实测）：
`lib/libXdamage.so.1.1.0`（SONAME `libXdamage.so.1`）、`lib/libXdamage.a`、
`lib/libXdamage.la`、`lib/pkgconfig/xdamage.pc`、`include/X11/extensions/Xdamage.h`
（`Xdamagewire.h` 由 xorgproto/damageproto 提供，libXdamage 不随附）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./config.guess: unable to guess system type` → `configure: error: cannot guess build type` | 上游 config.guess (2021-06-03) 没有 HarmonyOS 分支；且 config.guess 在 `$TMPDIR` 下建 dummy.c 时 `Permission denied` | E007：config.guess 加 `*:HarmonyOS:*` 分支直接 `echo aarch64-unknown-linux-ohos; exit`（**禁止**用 `--build/--host` 绕过，会误判为交叉编译） → `patches/0001-config.guess.patch` |
| 2 | `Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | config.sub (2021-08-14) 的 `case $kernel-$os` 校验表缺 `linux-ohos*` | config.sub 加 `ohos-linux` triplet、`ohos*` OS 列表、`linux-ohos*` kernel-OS 白名单 → `patches/0002-config.sub.patch` |
| 3 | `./config.status: can't create ./confXXXX/subs1.awk: Permission denied` | E002/HMDFS：`umask 077` 创建的临时目录在鸿蒙文件系统上不可写/不可执行内部脚本 | `umask 077` → `umask 022`（configure 内 2 处） → `patches/0003-configure.patch` |
| 4 | `libtool: error: '.../p/b/libx11<hash>/p/lib/libX11.la' is not a valid libtool archive` | 依赖包安装的 `.la` 文件里 `dependency_libs` 记录的是**依赖自身 build folder** 的 `.la` 绝对路径，该目录在依赖 `conan create` 结束后被清理 | 与 libxfixes/libx11 同策略：`build()` 内 `_fix_dep_la_files()` 只删除“指向不存在文件”的 `.la` 引用；`package()` 内 `_patch_libtool_libdir()` 把自身 `.la` 的 `libdir` 重写到最终 package 目录 |
| 5 | configure 打印 `Package xorg-macros was not found` | xorg-macros(.pc) 只被 `XORG_*` 宏在 **autoreconf 阶段**需要；发布 tarball 已展开，运行期只是提示 | 非阻塞，无需处理（configure 仍 rc=0） |

注：libXdamage 1.1.6 的 configure **没有** docs/xmlto/fop/xsltproc 选项
（libxfixes 6.0.1 有），因此配方 `generate()` 只传 `--enable-shared/--disable-static`。

## 源码修改（补丁清单）

| 补丁 | 文件 | 内容 | 类型 |
|------|------|------|------|
| 0001-config.guess.patch | config.guess | 新增 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` | portability |
| 0002-config.sub.patch | config.sub | `ohos-linux` triplet + OS 列表加 `ohos*` + kernel-OS 校验加 `linux-ohos*` | portability |
| 0003-configure.patch | configure | `umask 077` → `umask 022`（2 处，config.status 临时目录） | portability |

均为平台可移植性补丁，不改 libXdamage 自身 C 源码（`src/Xdamage.c` 零修改，鸿蒙下无需 `#ifdef __OHOS__` 守卫）。
补丁由 `refresh-patch --auto` 从 orig/work 目录按本版本 tarball 生成（config.guess 2021-06-03、
config.sub 2021-08-14 与 libxfixes 的 2023 版不同，hunk 是重新生成的，未照抄 libxfixes）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| xorgproto | 2025.1 | damageproto / xfixes / xextproto / xproto 头 + .pc（`Xdamage.h` include `damagewire.h`、`Xfuncproto.h`；`damagewire.h` 由 damageproto 提供） |
| libx11 | 6.4.0 | `x11 >= 1.6`，链接 `libX11`（间接带入 libxcb/libxau/libxdmcp） |
| libxext | 6.4.0 | `xext >= 1.3`，链接 `libXext` |
| libxfixes | 6.1.0 | `xfixes >= 4.0`，`XDamageSubtract/XDamageAdd` 的 `XserverRegion`(Region) 来自 `Xfixes.h`，必须链接 `libXfixes` |

W0 依赖发布检查：`conan download xorgproto/2025.1 -r=ohpcd`、
`conan download libx11/6.4.0 -r=ohpcd`、`conan download libxext/6.4.0 -r=ohpcd`、
`conan download libxfixes/6.1.0 -r=ohpcd` 均成功（已发布，对齐 main 已合并的 libxdamage/1.1.6 依赖链）。

## 验证结果

```bash
conan create archives/l/libxdamage/1.1.6.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -r ohpcd --build=missing
# libxdamage/1.1.6: Package '798b4354b28f0a450a399b87fb72cdd43bdb6cb6' built
# libxdamage/1.1.6: Exported: libxdamage/1.1.6#1351acf3e6c14acb40915505a7741e37（干净配方，无 .patch-backup）
# libxdamage/1.1.6 (test package): RUN: ./test_libxdamage
#   no X server reachable — server-dependent checks skipped
#   libxdamage api smoke ok (6 symbols, 5 assertion groups)
```

W3 本地 CI（finish step [3.5/9]，
`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`）**真实通过**，`finish` 写入
`.ci-result.json`（exit_code=0，含 integrity hash）。
CI 日志：`.ci_logs/conan_build_libxdamage_1.1.6.log`、
`archives/l/libxdamage/1.1.6/reports/conan-create.log`。

- 上游 `make check`：rc=0，但输出 `Nothing to be done for 'check'`
  —— **libXdamage 1.1.6 上游没有任何测试用例**（0 PASS / 0 FAIL / 0 SKIP）。
  配方仍保留 `autotools.make(target="check")` 入口，如实记录，不美化。
- 实测 SONAME：`libXdamage.so.1`（`-version-number 1:1:0` → `libXdamage.so.1.1.0`），
  任务侧预估值 2:0:0 与实际不符，以 readelf 实测为准。
- test_package：1 个用例 PASS（补齐上游测试空缺，见 `test_package/MANIFEST.yml`）。
  X server 相关分支在无 server 环境下按 Xlib 契约走 NULL 路径（如实标注为 skip 部分）。
- CI L4 报告 warn（"dangerous functions in patches"）：为 **CI 误报** ——
  `(strcpy|sprintf|gets|strcat)\b` 匹配到 config.guess 注释里的 "tar**gets**"（词尾
  gets+边界），非真实危险函数；与 libxfixes 的 L4 结果一致，非阻塞（L4_RESULT=warn）。
- 依赖链对齐 main 后：`libx11/6.4.0 + libxext/6.4.0 + xorgproto/2025.1 +
  libxfixes/6.1.0` 全部已发布 ohpcd（`conan download -r=ohpcd` 均成功），
  W3 本地 conan create 全通过（含 test_package 冒烟）。

## 注意事项

- `make check` 无用例是上游事实，不是本次跳过测试；测试覆盖完全依赖 test_package。
- 依赖 `.la` 修复函数会写入 **依赖包的 package folder**（只删除已失效引用），
  这是 X.Org 系列在本仓的既有做法（同 libx11/6.4.0、libxfixes/6.1.0），非本包引入。
- 未执行 `conan upload`（由 CI release 流水线负责），因此状态为 `built` 而非 `published`。
- **不要执行 submit**（PR 由主任务统一把关）。
---

**编译结束**: 2026-08-31 18:37
**最终状态**: built
