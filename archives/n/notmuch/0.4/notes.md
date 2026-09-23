# notmuch 0.4 — HarmonyOS PC (aarch64 OHOS) 适配笔记

## 概述
notmuch 0.4（2010-11）为邮件索引/搜索/标签工具：C 库 libnotmuch.so + CLI `notmuch`。
构建系统为**自定义 configure 脚本 + 手写 Makefile**（非 autotools、无 configure.ac）。
configure 硬性要求：`xapian-config`（XAPIAN_CONFIG）、`pkg-config gmime-2.6|gmime-2.4`、
`pkg-config talloc`、可选 valgrind/emacs。

0.4 与仓库已有 0.38.3 差异巨大：0.38.3 是 autotools + 新版 C API；0.4 用旧版 Xapian
C++ API 与 GMime 2.x MIME API。经实测 0.4 代码对 **xapian-core 1.4.26 二进制兼容**
（所用 API：WritableDatabase/QueryParser(FLAG_*)/TermGenerator/Enquire/MSet/
NumberValueRangeProcessor/sortable_serialise 等在 1.4.x 均存在），无需大改代码；
gmime 必须 2.x（0.4 不用 3.x API）。

## 依赖与 W0 预检结论
- 制品仓（ohpcd，conan download 实测）：
  - xapian-core/1.4.26 ✅（含 bin/xapian-config）
  - talloc/2.4.4 ✅（制品**无 .pc**，需合成）
  - glib/2.84.0 ✅（组件 .pc 的 prefix=/ 损坏，需修正）
  - zlib/1.3.1.1 ✅
  - gmime（2.x 与 3.x）❌ **无任何制品** → 配方内自包含构建 gmime 2.6.23（官方源）

## 关键编译步骤（手动验证，配方固化）
1. **gmime 2.6.23 自包含构建**：
   `./configure --build=aarch64-unknown-linux-gnu --prefix=<gmime-install>
    --disable-cryptography --disable-smime --disable-mono --disable-gtk-doc
    --disable-introspection`
   - PKG_CONFIG_PATH=<pc-stage>（glib 组件 .pc 修正 prefix 后 + 合成
     libffi/libpcre2-8/zlib/talloc.pc）
   - `-L/lib` 注入 **CFLAGS**（gmime 的 GLIB conftest 链接只用 CFLAGS；glib Libs 含
     `-l:ld-musl-aarch64.so.1`）
   - E011：config.status `umask 077 && mktemp` 建 0700 目录在 HMDFS 不可写 →
     `umask 022` 后重跑 `sh config.status`
2. **notmuch 0.4**：
   `XAPIAN_CONFIG=<xapian>/bin/xapian-config`
   `PKG_CONFIG_PATH=<gmime-install>/lib/pkgconfig:<pc-stage>`
   `CFLAGS/CXXFLAGS="-O2 -fPIC -I<xapian>/include -L/lib"`
   `LDFLAGS="-L<xapian>/lib -L/lib"`
   `./configure --prefix=<install>` → `make -jN` → `make install`
   - xapian-config 输出 `-I//include -L//lib`（prefix=/ 损坏）→ 真实路径经 CFLAGS/
     LDFLAGS 注入（0.38.3 同款处理）
   - `install` 命令在 /system/bin 不在默认 PATH → make install 时 PATH 前置 /system/bin
   - uname=HarmonyOS → 平台检测 "Unknown"，Makefile 仅 MACOSX 特殊分支，无碍
3. **补丁（patches/，refresh-patch --auto 生成）**：
   - 0001 gzip `--stdout`→`-c`（toybox 无长选项，构建必需）
   - 0002/0003 测试框架 bash 调用 + smtp-dummy `return;`→`return 1`（clang）

## 产物
- lib/libnotmuch.so.1.2.0（SONAME .so.1）+ include/notmuch.h
- bin/notmuch（CLI，动态链 libnotmuch）
- 随包分发 libgmime-2.6.so（libnotmuch 运行时 NEEDED，gmime 非 conan 依赖）

## 上游测试实测
notmuch 0.4 自带 TAP 框架（112 断言，13 组）。OHOS 环境限制：无 emacs、无 /bin/bash、
toybox touch 不支持 `-d '+N seconds'`。以 touch shim（+N seconds→绝对时间）+ 完整
LD_LIBRARY_PATH + TZ=UTC 手动运行：
- 非 emacs 12 组：**97/97 PASS**（basic10 new17 search14 json5 thread-naming9
  reply7 dump-restore4 uuencode3 thread-order6 author-order7 from-guessing10
  long-id4 encoding1）+ basic 组 1 个 broken-expected
- emacs 组 14 个：无 emacs 不可运行（系统级阻塞）
测试未嵌入 conan build()（依赖 bash/emacs/GNU coreutils 环境）；核心功能语义由
test_package C API 消费测试（create/version/index/query count+search）覆盖，
另加 CLI `notmuch --version` 冒烟。

## 知识要点（L3）
- glib 制品 pkg-config 组件 prefix=/ 损坏 → pc-stage 修正（0.38.3 同坑）
- gmime 2.6 autotools 老版本：config.status umask 077（E011）、--build 显式指定
  绕过 config.guess（uname=HarmonyOS 无法 guess）
- xapian-config 输出坏 prefix → 环境 CFLAGS/LDFLAGS 注入真实路径
- OHOS musl：-l:ld-musl-aarch64.so.1 需 -L/lib；工具差异（toybox gzip/install/bash）

## 问题与解决方案

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| notmuch.1.gz 生成失败 | OHOS toybox gzip 不支持 GNU 长选项 --stdout | 补丁 0001：gzip --stdout → gzip -c（POSIX） |
| 上游 TAP 测试无法执行 | OHOS 无 /bin/bash（bash 在 /data/service/hnp/bin） | 补丁 0002：notmuch-test 显式 `bash ./$test`（PATH 解析） |
| smtp-dummy 编译报错 | clang 将非 void 函数裸 `return;` 视为 -Wreturn-type 错误 | 补丁 0003：`return;` → `return 1` |
| gmime config.status 失败 | E011：umask 077 + HMDFS 0700 目录不可写 | config.status 改 umask 022 后重跑 |
| glib 制品 .pc prefix=/ 损坏 | ohpcd glib 包 pkg-config prefix=/ | 复制到 pc-stage 修正 prefix；libffi/pcre2/zlib/talloc .pc 合成 |
| xapian-config 输出坏路径 | xapian-config 输出 -I//include -L//lib | CFLAGS/CXXFLAGS/LDFLAGS 显式注入真实 xapian 路径 |

## 依赖

- xapian-core/1.4.26（bin/xapian-config）
- talloc/2.4.4（制品无 .pc，配方合成 talloc.pc）
- glib/2.84.0（组件 .pc prefix 修正）
- zlib/1.3.1.1
- libffi/3.4.4、pcre2/10.40（glib .pc Requires 链路）
- gmime-2.6.23（remote 无制品，配方内自包含构建，官方源）

## 验证结果

```bash
# conan create（含 test_package 消费测试 + W3 本地 CI 模拟）多次复跑 EXIT=0
conan create archives/n/notmuch/0.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → .ci-result.json exit_code=0；L0/L1 pass；L1e 破坏性反证确认非空壳
# 上游 TAP（手动实测，touch shim + LD_LIBRARY_PATH + TZ=UTC）：
#   非 emacs 12 组 97/97 PASS + basic 1 broken-expected（98 runnable）
#   emacs 组 14 断言因无 emacs 不可运行（如实申报，见 manifest runnable_note）
```

## 源码修改

- 0001-Makefile.local.patch：gzip `--stdout` → `-c`（构建必需，notmuch.1.gz 生成）
- 0002-test-notmuch-test.patch：测试脚本改用 PATH 中 bash 显式执行
- 0003-test-smtp-dummy.c.patch：`return;` → `return 1`（clang -Wreturn-type）
  三补丁均为 POSIX 兼容修复（无 __OHOS__ 平台宏），由 refresh-patch --auto 生成
---

**编译结束**: 2026-09-05 10:59
**最终状态**: built
