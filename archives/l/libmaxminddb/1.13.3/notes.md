# libmaxminddb 1.13.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，LT_INIT libtool；另有 CMakeLists.txt 副构建，未采用）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS 工具链，aarch64-linux-ohos）
- 状态: published（conan-verify G0–G4 全 PASS，2026-09-24）
- 目标平台: HarmonyOS PC (OHOS armv8/aarch64)，profile `ci/conan/profiles/ohos-aarch64`

## 编译步骤（conan create 实际执行路径）
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
配方内构建序列（out-of-tree，basic_layout build-release 目录）：
```bash
./configure --host=aarch64-linux-ohos --enable-shared --disable-static --prefix=<pkg>
make -j1
make install DESTDIR=<pkg>
```
产物：`lib/libmaxminddb.so*`（+ `lib/libmaxminddb.a`，若共享关闭）、`bin/mmdblookup`、
`include/maxminddb.h`、`include/maxminddb_config.h`、`lib/pkgconfig/libmaxminddb.pc`、man 页。

`make check` **不在 CI 中执行**：check_PROGRAMS 为 aarch64 OHOS 二进制，x86_64 构建机上
无法执行（exec format error），须在 OHOS 真机/模拟器上运行（见下文测试清点，R51）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make all` 报 `cd libtap: No such file or directory`（整树中止） | t/Makefile.am 的 all-local/clean-local 写死 `cd libtap && $(MAKE)`（内嵌测试框架 t/libtap）；conan basic_layout 将构建放到独立 build-release 目录（out-of-tree），无 libtap 子目录 | E547 推荐方案：补丁 `0001-t-makefile-libtap-out-of-tree.patch` 将两处改为 `cd $(top_srcdir)/t/libtap`（同时修 t/Makefile.am 与 t/Makefile.in，后者是 configure 实际消费的生成物） |
| 2 | lang-preflight 报 `detected=mixed(go)` | t/maxmind-db/ 为官方附带的 vendored Go 测试数据生成工具（9 个 .go + go.mod），被全树扩展名统计误计为主体语言 | E550 判定为假阳性：库主体（src/include）纯 C，autotools，属 c↔cpp 兼容族，正常适配。**严禁删除/改名 t/maxmind-db 夹具、严禁修改 scripts/ohc/lang_detect.py** |
| 3 | configure 端序检测风险 | 若不带 --host，CI 同 profile（host==build）时 AutotoolsToolchain 不注入三元组，configure 视作 native，AC_C_BIGENDIAN 可能尝试运行 aarch64 二进制 | generate() 显式追加 `--host=aarch64-linux-ohos`（上游 config.sub 原生支持 linux-ohos，已实测 `aarch64-linux-ohos` → `aarch64-unknown-linux-ohos` 合法），使 cross_compiling=yes，端序走编译期 BYTE_ORDER 路径 |
| 4 | `conan create` 时 config.status 报 `./confXXXXXX/subs1.awk: Permission denied`（configure 其余检查全部通过） | configure/config.status 以 `umask 077 && mktemp -d "./confXXXXXX"` 在 cwd 建临时目录写 subs1.awk；conan 构建目录位于 HMDFS setgid 文件系统，umask 077 建出的 700 目录在 setgid 语义下不可写 | E046 族方案：补丁 `0002-configure-umask-tmpdir.patch` 将 umask 077→007，并把临时目录改到 `${TMPDIR:-$HOME/tmp}`（规避 HMDFS setgid 目录） |

## 源码修改（补丁说明）

`patches/0001-t-makefile-libtap-out-of-tree.patch`（E547，必需）：
- `t/Makefile.am` all-local/clean-local：`cd libtap && $(MAKE)` → `cd $(top_srcdir)/t/libtap && $(MAKE)`
- `t/Makefile.in` 对应两行（configure 实际使用），与 .am 同步修改
- 纯 VPATH 友好改动，无平台宏，无 `__OHOS__`

`patches/0002-configure-umask-tmpdir.patch`（E046 族，必需）：
- configure 中 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` → `tmp=\`(umask 007 && mktemp -d "${TMPDIR:-$HOME/tmp}/confXXXXXX")\``
- fallback 分支 `(umask 077 && mkdir "$tmp")` → `(umask 007 && mkdir "$tmp")`
- 背景：conan 构建目录位于 HMDFS setgid 文件系统，umask 077 建出的临时目录在 setgid 语义下
  不可写，config.status 写 subs1.awk 报 `Permission denied`（见问题表 #4）

**已移除的陈旧补丁**（2026-05-06 原生构建尝试遗留，本任务以新方案取代）：
- `0001-config.guess.patch` / `0002-config.sub.patch`：将 config.guess/config.sub 升级到 2025 版
  以支持 HarmonyOS 原生识别。conan 交叉构建显式传 `--host`，config.guess 只在 x86_64 构建机
  上求 --build，原生支持，无需升级；且 0001 补丁新增 `__OHOS__` 宏行，会被 preflight PF5
  （patches 禁平台宏）拦截，必须移除。
- `0003-configure.patch`：旧 umask/临时目录修复，与本任务 `0002-configure-umask-tmpdir.patch`
  方案一致（umask 077→007 + `${TMPDIR:-$HOME/tmp}`），已由 0002 补丁重新实现并随 conan 配方应用。

## 依赖版本

无第三方运行时/构建依赖：仅标准 POSIX 头 + `clock_gettime`/`open_memstream`（OHOS musl 均有）。
`AC_SEARCH_LIBS` 可能引入 `-lm`（fabs/fabsf），已在 cpp_info.system_libs 声明。

## 上游测试清点（R51，供 OHOS 真机执行）

- `src/`：`make check` 单测 `test-data-pool`（data-pool.c 测试驱动，1 个）
- `t/`：automake check_PROGRAMS 26 个 C 测试 + 3 个辅助脚本（compile_c++_t.pl /
  external_symbols_t.pl / mmdblookup_t.pl，依赖 Perl 模块 IPC::Run3、Test::Output）
  → `TESTS = $(check_PROGRAMS) + 3 个 .pl` = 29 项；全树（含 src/ test-data-pool）共 27 个
  C 测试程序
- 测试数据：`t/maxmind-db/test-data/` 预生成 .mmdb 文件已随发布物提交，无需 Go 工具现场生成
- 历史原生构建实测（2026-05-06）：28/29 通过（按 t/ 的 29 项 TESTS 计），唯一失败
  `dump_t`（debug 输出格式差异 + SIGTRAP 信号，低影响，属已知平台差异，详见 README）
- 结论：测试套件可在 OHOS 真机执行验证；CI（交叉编译环境）只编译不执行

## 验证结果

conanfile.py 静态自查：settings 四件套齐全、AutotoolsToolchain 注入 CC/CFLAGS 均来自
Toolchain（无裸 `${CC}`/`${CFLAGS}`，R33）、无系统同名库（libmaxminddb 非 OHOS 系统库，
动态默认，R26 不适用）。

`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
已实跑通过（2026-09-24）：configure 全项通过（补丁 0001/0002 应用成功）、make 构建完成、
conan package 打包成功；`conan-verify`（G0-G4）全部 PASS，可发布。

## 注意事项
- **R38**：包安装 `bin/mmdblookup`（CLI 工具），须在软件级 `archives/l/libmaxminddb/commands.json`
  声明（本版本目录外，由主流程创建）。
- **E550**：t/maxmind-db/ 是上游发布物一部分，不得删除/改名；lang-preflight mixed(go) 为假阳性。
- `t/Makefile.in` 是 configure 实际使用的生成物，E547 修复必须同时落到 .am 与 .in。
