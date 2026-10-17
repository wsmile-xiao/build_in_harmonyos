# ogg 1.1.1 适配笔记

> 包名线说明：本目录是 `ogg` 包名线（xiph/ogg tag v1.1.1，2004 年老版本）。
> 与 `archives/l/libogg/`（1.3.5-1.3.6.1，CMake，新版本线）是**不同包名**的
> 并存关系，不冲突：同一上游项目在制品仓可以有多条包名线（多包名并存）。

## 编译环境

- 构建系统: autotools（2004 老式：configure.in + Makefile.am，无预生成 configure）
- 编译日期: 2026-09-15
- 编译器: clang（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built（本地 conan create + W3 本地 CI 模拟全绿）

## 上游形态（v1.1.1 tag 实测）

| 项 | 值 |
|---|---|
| 源码 | https://codeload.github.com/xiph/ogg/tar.gz/refs/tags/v1.1.1 |
| sha256 | 9edf7e7922c4f922d972e2e8f2b769dc437ce7f2dbdf3f33444b536dbfd16931 |
| 语言 | 纯 C（src/framing.c + src/bitwise.c，共 2 个源文件） |
| 依赖 | 零第三方依赖（仅 libc） |
| 测试 | src/Makefile.am `check:` 规则直接跑 ./test_bitwise + ./test_framing |
| 库版本 | libogg.so.0.5.1（-version-info 5:1:5 → SONAME=libogg.so.0） |

## 编译步骤

1. conan `get()` 下载源码（显式 `filename=ogg-1.1.1.tar.gz`，避免 codeload
   gzip 被误判为 zip）
2. `configure.in` 复制为 `configure.ac`（autoreconf ≥ 2.70 只读 .ac）
3. `tool_requires`：automake/1.18 + libtool/2.5.4（E178，worker 只有 autoconf）
4. `autoreconf -fi`：生成 configure，并从 conan 包装入 2024 新式
   config.guess/config.sub/ltmain.sh/install-sh/missing/depcomp
5. E007：对装好的新式 config.guess/config.sub 打 HarmonyOS 识别补丁
   （官方 perl 工具新式脚本自检通过；CI 走 Python fallback）
6. E114：生成 configure 中 `umask 077` → `umask 022`（HMDFS 可写性）
7. `./configure --enable-shared --disable-static`（不传 --build/--host，R15）
8. `make -j1`（E074：并行 make 撞 HMDFS jobserver fifo EPERM）
9. `make check -j1`：**上游测试在此执行**
10. `make install DESTDIR=...`，清理 .la 文件

## 上游测试计数（rule4 口径：上游构建系统注册的测试目标数）

上游注册 2 个测试程序（src/Makefile.am noinst_PROGRAMS + check: 规则）：

| 程序 | 源 | 断言数（输出 ": ok." 行数） |
|---|---|---|
| test_bitwise | src/bitwise.c -D_V_SELFTEST | 16（LSb 8 + MSb 8） |
| test_framing | src/framing.c -D_V_SELFTEST | 14 |

- 上游测试：30 断言 / 30 通过（conan create 日志实测，见下）
- 消费者测试（test_package/）：1 断言 / 1 通过（安装包 API 回环）
- 合计申报：31 断言，全部通过（100%）

conan create 日志证据（~/.conan2 缓存构建日志，本地 W3 留档）：

```
ogg/1.1.1: RUN: make check -j1
./test_bitwise
Small preclipped packing (LSb): ok. ... （共 16 项 ok）
./test_framing
testing single page encoding... ok. ... （共 14 项 ok）
ogg/1.1.1 (test package): RUN: "./ogg_consumer"
ogg 1.1.1 installed-package round trip passed
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan get() 报 BadZipFile | codeload 链接无扩展名，gzip 被字节嗅探误判为 zip | source() 显式 `filename="ogg-1.1.1.tar.gz"`（bwm-ng 同款） |
| 2 | autoreconf 只警告 configure.in 不处理 | autoreconf ≥ 2.70 只读 configure.ac | 复制 configure.in → configure.ac |
| 3 | aclocal/libtoolize 不存在（裸机试验时） | worker 只有 autoconf | 配方内 tool_requires automake/1.18 + libtool/2.5.4，conan 自动注入 PATH |
| 4 | AM_PROG_LIBTOOL 宏未定义（裸机试验时） | aclocal 缺 libtool.m4 搜索路径 | conan 环境下 tool_requires 自动配好 ACLOCAL_PATH；裸机需手动 ACLOCAL_PATH=<libtool>/share/aclocal |
| 5 | config.guess 无法识别 HarmonyOS | GNU 官方脚本无 HarmonyOS 分支（E007） | autoreconf 装入新式脚本后打 E007 补丁（perl 工具/Python fallback） |
| 6 | config.status 写临时目录 Permission denied | umask 077 + HMDFS（E114） | configure 内 umask 077 → 022 |
| 7 | E564 风险预判（任务卡提示老式 config.guess 重锚） | 任务卡提醒 2005 前老式构建 | 实测不适用：tarball 根本不含 config.guess，autoreconf 装的是 2024 新式脚本，官方 perl 工具直接可用 |

## 源码修改

无静态补丁文件（`patches: []`）。config.guess/config.sub/configure 的修改
全部在 autoreconf 之后由配方运行时施加（源码包不含这些生成物）。

## 与 libogg 线的关系（多包名并存）

| | ogg 1.1.1（本包） | libogg 1.3.6（已有） |
|---|---|---|
| 包名 | ogg | libogg |
| 上游 tag | v1.1.1（2004） | v1.3.6（2023） |
| 构建系统 | autotools（configure.in） | CMake |
| 产物 | libogg.so.0.5.1 | libogg.so |
| pkg-config 名 | ogg | ogg |
| cmake target | Ogg::ogg | Ogg::ogg |

两条包名线独立目录、独立版本线，制品仓并存（R37 无冲突：不同 name）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libogg.so.0.5.1 (+ .so.0/.so 符号链接) | 动态库，SONAME=libogg.so.0，NEEDED 仅 libc.so |
| include/ogg/{ogg.h,os_types.h,config_types.h} | 公共头 |
| lib/pkgconfig/ogg.pc | pkg-config 元数据 |
| share/aclocal/ogg.m4 | autoconf 宏（上游安装） |
---

**编译结束**: 2026-09-15 01:50
**最终状态**: built（本地 conan create + W3 全绿；制品仓 upload 由 release 流水线在 PR 合并后执行）
