# myman 0.7.1 适配笔记

## 编译环境
- 构建系统: autotools（自研 hand-written configure + GNU make Makefile）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS SDK，target aarch64-unknown-linux-ohos）
- 状态: built

## 版本来源
- 派发版本号 "40116"/"4.0.116" 上游不存在，改用上游源码快照
  myman-wip-2009-10-30（内部 VERSION=0.7.1），首次适配。
- 官方源（R39）:
  https://sourceforge.net/projects/myman/files/myman-cvs/myman-cvs-2009-10-30/myman-wip-2009-10-30.tar.gz/download
- sha256: bf69607eabe4c373862c81bf56756f2a96eecb8eaa8c911bb2abda78b40c6d73

## 编译步骤（手工探索验证，与 conanfile.py 一致）
源码复制到非 HMDFS 工作目录（E011）：
```bash
WORK=/data/storage/el2/base/.conan-build-myman-0.7.1-<hash>
cp -r <src> $WORK
# conf/ 下生成 install/rmdir/sed 三个 wrapper（应答 GNU 自检，委托 toybox）
export PATH=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:/usr/bin:/bin
P=<ncurses package_folder>
cd $WORK
env -u LD -u CPPFLAGS -u LDFLAGS \
  /data/service/hnp/bin/bash configure --with-ncursesw \
  CC=clang CFLAGS=-O2 LDFLAGS=-L$P/lib SHELL=/data/service/hnp/bin/bash
env -u LD -u CPPFLAGS -u LDFLAGS make -j1 \
  NCURSESW_CONFIG=$P/bin/ncursesw6-config CC=clang CFLAGS=-O2 \
  LDFLAGS=-L$P/lib INSTALL=$WORK/conf/install RMDIR=$WORK/conf/rmdir SED=$WORK/conf/sed
env -u LD -u CPPFLAGS -u LDFLAGS make -j1 <同上> install DESTDIR=$WORK/stage   # make install
```
> ⚠️ 必须显式传 `install` 目标：本 makefile 的默认目标为 `all`，`make DESTDIR=...`
> 只会重建游戏本体、**不会**装进 DESTDIR stage（曾致 W3 空包 → test_package 127）。
```
验证：`./myman --version` → `myman 0.7.1`；`TERMINFO=$P/share/terminfo
TERM=xterm-256color script -q -c "./myman"` 可进入游戏（LEGAL 屏）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ld.lld: cannot find entry symbol _start` + sanity0 段错误 | 环境导出 `LD=ld.lld`，myman Makefile 检测到 LD 后改用裸链接器 `LINK=${LD}...`，不带 CRT | `env -u LD make ...`，让 Makefile 走 `LINK=${CC}` 分支（R33：不依赖未定义 shell 变量，显式控制） |
| 2 | `coreutils.ok: coreutils check failed`（cp/install: Unknown option 'strip'） | myman Makefile 的 coreutils.ok/sed.ok 自检要求 GNU `install --strip`、`rmdir --ignore-fail-on-non-empty`、`sed --silent` 在 **stdout** 打印选项名；HarmonyOS 仅 toybox（错误走 stderr/不支持长选项） | conanfile 在 build 目录生成 conf/install、conf/rmdir、conf/sed 三个小 wrapper：遇 `--help` 打印含标志字的帮助文本（stdout），真实操作委托 `/bin/toybox install/rmdir/sed`；make 经 INSTALL/RMDIR/SED 变量注入 |
| 3 | 在 ~/tmp/builds（HMDFS）configure/make 风险高（E011 执行位/umask 语义） | HMDFS 剥离执行位、mktemp/umask 目录权限异常 | 复制源码到 /data/storage/el2/base/.conan-build-myman-*（非 HMDFS，calcurse/ncurses 同款实证）再 configure/make |
| 4 | 编译警告 `logical not is only applied to the left hand side of bitwise operator`（myman.c:3166） | 上游 C 代码 `!pen[...] & A_REVERSE` 写法 | 上游既有无害告警，不加补丁（不动源码） |
| 5 | make 末尾 `col: command not found`（myman.txt 生成） | 上游用 groff `col` 生成纯文本 man，OHOS 无 groff/col | 该规则带 `(ignored)`，不阻断构建；man6 由 myman.6 直接交付 |
| 6 | W3 test_package 报 `/bin/sh: .../bin/myman: inaccessible or not found` (Error 127) | 双层根因：①conanfile 第二次 make 未显式给 `install` 目标 → 默认目标 `all` → DESTDIR stage 为空 → package() 打包空目录；②OHOS 内核要求 ELF 含有效 `.codesign` 才能执行（E077），裸拷出的 myman 未签名 | ①`make ... install DESTDIR=<stage>` 显式目标；②package() 内对 bin/myman 执行四步签名：copy→llvm-objcopy --remove-section .codesign(可失败)→binary-sign-tool sign -selfSign 1 -inFile tmp -outFile tmp.signed -signAlg SHA256withECDSA→move 回原路径→chmod 755 |

## 依赖版本
- ncurses/6.6（ohpcd，static wide-char `--enable-widec`，库 formw/menuw/panelw/ncursesw，
  头文件在顶层 include/，bin/ncursesw6-config relocated）

## 上游测试（R51 清点）
myman 上游**无任何测试套件**：源码无 tests/ 目录；Makefile 无 check/test
目标；仅有编译期自检 gnumake.ok/configure.ok/compiler.ok/coreutils.ok/sed.ok
（工具链可用性探测，非功能测试）。make check 不存在 → 如实回填 MANIFEST.yml。
test_package 提供消费者视角实质测试（myman --version/--help 执行断言，R34）。

## 验证结果
```bash
$ ./myman --version
myman 0.7.1
Copyright 1997-2009, Benjamin C. Wiley Sittler <bsittler@gmail.com>
$ ./myman --help   # 退出 0，列出全部 variant/size
$ readelf -d myman | grep NEEDED  → 仅 libc.so（ncurses 静态链入）
```
W3 conan create（2026-09-06 复验通过）：
```bash
$ conan create ... # 签名后 test_package 实跑通过
myman/0.7.1 (test package): RUN: .../p/bin/myman --version
myman 0.7.1            # ← 签名生效，真实执行成功
[ok] myman/0.7.1 — conan create passed
```

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | requirements=ncurses/6.6；非 HMDFS 工作目录构建；wrapper 注入；DESTDIR staging 打包 |
| conandata.yml | 官方 SourceForge URL + sha256 |
| test_package/ | myman --version/--help 执行断言（R34） |
| commands.json | CLI 工具声明（R38，软件级） |
| patches/ | 无（未改源码） |

## 注意事项
- 禁止在 Makefile 环境中保留 `LD`/`CPPFLAGS`/`CFLAGS`/`LDFLAGS` 外壳变量
  （R33）；NCURSESW_CONFIG 必须指向 conan ncurses 包的 ncursesw6-config。
- myman 产物是**游戏可执行文件**（非库），产物打包仅需 bin/myman + man6 + doc；
  全部 variant/size 数据已编译内建，无需携带 share 数据文件。
---

**编译结束**: 2026-09-06 10:37
**最终状态**: built
