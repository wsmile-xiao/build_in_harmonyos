# sfic 0.1.7 适配笔记（OpenHarmony PC / armv8）

## 项目概述

sfic（Simple File Integrity Checker）是 2006 年的 GPL-2.0 C 命令行工具：为文件树建立
tdb（Samba trivial database）元数据库（类型/权限/uid/gid/大小/mtime/sha256），
支持列表（-l）与跨库比对（-n NEW -o OLD），用于检测文件系统变更。

- 源码结构：单 C 文件 `src/sfic.c`（约 1858 行）+ 自带 `sha256.c`/`sha256.h`，autotools 构建
- 唯一硬运行时依赖：tdb（`#include <tdb.h>` + `AC_CHECK_LIB(tdb, tdb_store)`）
- 上游无任何测试用例（详见下方"测试"）

## 依赖决策：tdb/1.4.15（requires，共享动态链接）

- tdb/1.4.15 已发布到 ohpcd 制品仓（armv8/OHOS 共享库 `libtdb.so.1.4.15`，SONAME `libtdb.so.1`）
- 其 recipe 构建时运行 tdb 完整上游测试套件 `make test`（37 个测试程序全部通过），
  满足"上游测试用例全部测试"对依赖侧的覆盖要求
- 不采用 vendored tdb 源码内联构建：CI JC3 门禁拦截非 prebuilt 命名的 `.tar.gz` 入 `archives/`
- 链接方式：`--with-tdb-lib=<tdb 包>/lib`（configure 追加 -L）+ `-ltdb`；
  头文件经 `--with-tdb-headers=<tdb 包>/include` 注入 CPPFLAGS
- **注意**：configure.ac 的 `--with-tdb-headers` 是半死参数（`[TDB_HDR_DIR=...]`/
  `[CPPFLAGS="$CPPFLAGS -I$withval"]` 双分支结构，默认分支写入空 -I 值），必须显式指定

## RPATH 与 L2 冒烟门禁

CI L2 冒烟门禁在 CI worker 上**无 LD_LIBRARY_PATH** 直接执行 `bin/sfic --version`。
sfic 动态链接 libtdb.so.1，故 conanfile build() 在 configure 前注入
`LDFLAGS="-Wl,-rpath,<tdb 包>/lib"`（musl 支持 RPATH，已验证）。
test_package 的 conanrun 环境则自动带 LD_LIBRARY_PATH（VirtualRunEnv）。

## OHOS 关键坑（对应 4 个补丁）

1. **config.sub（2006 版）不认识 aarch64-linux-ohos**：补丁 0001 增加 linux-ohos
   内核-OS 组合与 aarch64 机器名。AutotoolsToolchain 在该 conan 构建中不自动注入
   triplet，conanfile 显式传 `--build/--host=aarch64-linux-ohos`。
2. **/tmp 只读 + mksh 临时文件 + umask 077**：OHOS（HMDFS）/tmp 为只读文件系统；
   且 configure 的 `#! /bin/sh` 在 OHOS 上是 mksh，mksh 的 `$(...)` 命令替换**硬编码**
   使用 `/tmp` 存放临时文件（**忽略 TMPDIR**）→ autoconf 2.61 所有 conftest 检查
   报 "C compiler cannot create executables"。解法（conanfile build() 内联，参照
   4ti2 的 configure 内联修复先例）：
   a) 将 configure 首行 shebang 从 `#! /bin/sh` 改为指向 bash（bash 尊重 TMPDIR）——
      路径是环境相关的，故用内联改写而不做 patch 文件；
   b) `TMPDIR` 指向构建工作区内可写目录（`build/tmp`）；
   c) 补丁 0002 去掉 configure 临时目录创建处的硬编码 `umask 077` 加固
      （setgid 临时目录下不可写）。
3. **install-strip recipe 缩进**：`src/Makefile.in`（及 `src/Makefile.am`）的
   `install-strip:` recipe 续行用 8 空格而非 TAB，make 报 overriding recipe 警告并跳过。
   补丁 0003 恢复 TAB。
4. **无 --version**：sfic 0.1.7 只有 -h，L2 冒烟门禁先试 `--version`。
   补丁 0004 在 `src/sfic.c` 新增 `--version/-V` 选项（打印 `sfic 0.1.7`），
   并补 `#include <limits.h>`（musl 下 PATH_MAX）。

## 测试

- **上游**：sfic 0.1.7 无测试用例。`make check` 目标存在但 `src/Makefile.am` 未定义
  TESTS/TESTS_SCRIPTS，执行结果为 "Nothing to be done for 'check'"（rc=0）。
  build() 中照常执行 `make check` 留痕。
- **适配后**：test_package/test.sh 消费者用例 7 项断言（CLI 建库/列表/无变更比对/
  变更检测/落盘校验），本地 aarch64 真机 7/7 通过。
- **依赖侧**：tdb/1.4.15 自身上游套件 37/37 通过（其 recipe 构建期执行）。

## 已知行为/限制

- `-n NEW -o OLD` 检测到变更时退出码为 255（非 1），且逐行打印 `U <path>` 等变更
- tdb 既有 quirk：同一 db 文件同一进程双开异常 → 测试用两个独立 db 文件
- 许可：GPL-2.0（无 "or any later version" 条款，COPYING 为标准 GPL v2 文本）

## 本地 CI 模拟记录

- 环境：aarch64 OpenHarmony 真机，OHOS 适配版 conan 2.29.1，profile `ohos-aarch64`
  （与 CI 的 `ci/conan/profiles/ohos-aarch64` 内容一致）
- 命令：`conan create archives/s/sfic/0.1.7 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build="sfic/*" -r=ohpcd`
- 结果：见 `reports/test-report.md` 与 `reports/quality-report.md`
