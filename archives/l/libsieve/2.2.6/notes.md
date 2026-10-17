# libsieve 2.2.6 适配笔记

## 编译环境
- 构建系统: autotools (configure + make，入口在 `src/` 子目录)
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built (待 HarmonyOS aarch64 真机预检回填实测证据)

## 编译步骤

上游是经典 autotools 包，但真正的构建入口不在顶层：
顶层 `Makefile` 只处理 release/snapshot 打包，实际的 `configure`、
`Makefile.in` 都在 `src/` 下（`src/configure.in`，`AC_INIT(sv_parser/sieve.y)`）。
配方因此用 `autotools.configure(build_script_folder="src")`
（与 berkeley-db 的 `dist` 子目录模式相同），然后 `make -j1`。

```python
autotools.configure(build_script_folder="src")
autotools.make(args=["-j1"])
```

OHOS 下显式传递 `--build=aarch64-unknown-linux-gnu`
`--host=aarch64-unknown-linux-gnu`（两者相等，仍为原生构建），
避免 2007 版 config.guess 在新平台上猜测失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2007 版 `config.sub` (timestamp 2007-01-18) 不认识 `aarch64` triple，`config.sub aarch64-unknown-linux-gnu` 直接报 Invalid configuration | aarch64 支持 2013 年才进入 config.sub | `patches/0001-src-config.sub.patch`：在裸 CPU 表和 `CPU-*` 公司名表各加一行 `aarch64[_be]`（POSIX 兼容改法，不引入平台宏） |
| 2 | 上游 `Makefile.am` 未注册任何 `TESTS`，`make check` 为空操作 | 上游测试是手写的 shell harness，不是 automake TESTS | 配方在 `build()` 里如实运行真实套件：`sv_test/testcomp` (1) + `testvalid.sh` 等价循环 (12) + `testmessage.sh` 等价循环 (24)，共 37 项，动态计数后打印 `HMBS_UPSTREAM_TEST_RESULT` |
| 3 | `testmessage.sh` 覆盖的 script5.sv/script7.sv 含 vacation 动作，示例回调里 `my_vacation` 会调 `getchar()` 问一句话 | 上游示例为交互式设计 | 无人值守运行时 stdin 重定向自 `/dev/null`（EOF 即答“否”），不跳过用例 |
| 4 | `src/` 下 `configure` 由老 autoconf 生成，`missing` 包裹的 flex/bison/gperf 仅在重新生成词法/语法文件时才需要 | 发布包已带预生成的 `sieve-lex.c`/`sieve.c` 等 | 本地 flex/bison/lex/yacc shims + 刷新预生成产物时间戳，不声明 tool_requires |
| 5 | 真机 `config.status` 报 `can't create ./confgXXXXXX/out: Permission denied`，无 Makefile（E011） | 老 autoconf 在 `mktemp -d ./confgXXXXXX` 前 `umask 077`，HMDFS 上 0700（drwx--S---）目录同进程不可写；失败的是 `./confg*` 而非 $TMPDIR，故 TMPDIR 重定向无效 | `build()` 内 `_patch_configure_umask()` 把 `src/configure` 中全部 `umask 077` 改为 `umask 022`（含内嵌 config.status 模板，E011 标准修法；buildtorrent 同模型复用） |

## 源码修改

- `patches/0001-src-config.sub.patch`：两处各加一行 aarch64 识别（裸 CPU 表 + `aarch64-*` 公司名表），`patch_type: portability`。

## 依赖版本

- 无运行时依赖（纯 C 库，仅依赖 libc）。
- 构建期：autotools 工具链（configure/make/libtool 均由发布包自带脚本 + 系统工具提供）。

## 上游测试盘点（审计）

- `src/sv_test/testcomp.c`：比较器单元测试，`tc[]` 表 134 行断言，单二进制退出码判定。
- `src/sv_test/testvalid.sh`：`script1.sv`-`script12.sv` 纯语法校验（12 项）。
- `src/sv_test/testmessage.sh`：12 个脚本 × `messagea.mbox`/`messageb.mbox` 执行（24 项）。
- 合计 37 项，可全部无人值守执行（vacation 用 stdin `/dev/null` 解决）。
- `script13.sv`-`script17.sv` 存在但未被上游 shell harness 接入，本轮不计入、不改动。
- 夹具非空已核实：messagea.mbox 635B、messageb.mbox 627B；md5 与 Ubuntu 官方记录一致。

## 验证结果

待 HarmonyOS aarch64 真机预检（conan create 全链路：编译 + 37 项上游测试 + test_package 2 项 ctest）回填。

## 注意事项

- 源码 URL 用 SourceForge 官方直链；sha256 `dce45d73...e7f0f0` 已用多方交叉验证（包大小 564722B 与官方页 564.7kB 一致，md5 `c97050a3...` 与 Ubuntu 归档记录一致）。
- test_package 用 CMake + CMakeDeps（`libsieve::libsieve`），两个用例：正向全链路 + 破损脚本反向验证。

## Round-6（2026-09-18 真机 make Error 2 聚焦修复）

- 现象：configure 已 exit 0（CFGTAIL 为证），`make -j1` 报 Error 2；聚焦摘要省略了 stdout 中段，真正的失败行不可见。
- 改动（仅配方诊断硬化，未改上游语义/测试口径）：`build()` 在 configure 后校验 `_work/Makefile` 存在（缺失则列目录并 fail fast）；`make -j1 V=1` 重定向到 `make.log` 后 `tail -n 60` 保持在输出尾部；失败时新增 `_dump_make_log()` 以 ERROR 级重发 `MAKEERR/MAKETAIL`（与 CFGLOG 同通道，摘要会保留），下一轮预检即可看到真实失败命令。
- 待下一轮真机预检根据 MAKEERR/MAKETAIL 做针对性修复。

## Round-7（2026-09-18 真机 make Error 2 根因修复）

- 根因：`src/sv_parser/addr.c:147` 与 `src/sv_parser/sieve.c:259` 对 `libsieve_parse_context` 各有一处 tentative 定义（无 extern、无初值），同进 `libparser.la` 再参与顶层 `libsieve.la` 与 `sv_test` 链接。真机 clang-15（与 gcc≥10 同理）默认 `-fno-common`，链接期报 `multiple definition`。证据链：① 子目录编译全部成功（libparser/libregex/libutil 均 ar 归档），失败恰在 `sv_empty.lo` 编译之后、即顶层链接阶段；② Debian 官方 `2.2.6-9` 补丁 `fix_gcc10.patch` 为同一 tarball（md5 `c97050a3…` 一致）的同一 FTBFS；③ 本地审计确认其余 TU 均为 extern 声明，仅此两处重复定义。
- 改动：新增 `patches/0002-fno-common-libsieve_parse_context.patch`（addr.c 改 tentative 为 extern，定义唯一留在 sieve.c；addr.y 同改保持生成源一致；与 Debian 同语义），conandata.yml 注册；`_ensure_lex_yacc_shims` 时间戳名单补齐 `addr.c/addr-lex.c/header.c/header-lex.c` 防 yacc 再生；make 失败时新增 `_first_make_error()` 把首个错误行嵌进抛出的 ConanException（摘要必留末尾 ERROR 块，不再依赖中段）。
- 上游语义/测试口径未动；待真机预检验证链接通过与 37 项上游测试。

## Round-8（2026-09-18 真机 Failed to apply patch 根因修复）

- 现象：0002 补丁可解析但打不上，真机报 `source file is different - src/sv_parser/addr.y`（actual 为空）。
  上轮手调 hunk 头/空行前缀只解决了“流截断”，没解决“上下文与真实字节不符”——addr.y 周围行与 addr.c
  并不相同，在没拿到原包字节前凭猜测写 diff 必然脆弱。
- 改动（与上轮不同策略）：删除 `patches/0002` 并从 conandata.yml 摘除注册；新增配方内
  `_patch_fno_common()` 字节级幂等文本替换（与已验证的 `_patch_configure_umask` 同模式）——逐行比对
  `struct sieve2_context *libsieve_parse_context;` 整行转为 extern，sieve.c 的唯一定义不动；已是 extern
  则跳过，两文件都无锚点且无 extern 时抛错并以 ERROR 级打出真实含 `libsieve_parse_context` 的行供下轮取证。
  调用点在 `build()` 的 apply_conandata_patches 之后、时间戳刷新之前，保证 bison 不再生覆盖。
- 上游语义/测试口径未动；待真机预检验证补丁应用通过、链接通过与 37 项上游测试。

## Round-9（2026-09-18 真机 conflicting types for libsieve_headererror 根因修复）

- 现象：sv_parser/header.lo 编译失败，clang-15 报 `conflicting types for 'libsieve_headererror'`：
  headerinc.h 声明 `void libsieve_headererror(char *str)`，而随包预生成的 header.c 定义
  `void libsieve_headererror(const char *s)`（经 `#line 77 "header.y"` 回映射到 header.y:80）。
  .y 源码仍是 `char *s`，说明 .c 曾用新版 bison 骨架（const yyerror）再生过，但 .y 与 headerinc.h
  未同步。旧 gcc 下未暴露，真机 clang-15 按 C 标准判为类型冲突。
- 改动（仅配方内字节级文本替换，与 _patch_fno_common 同模式，未改上游语义/测试口径）：
  新增 `_patch_headererror_const()`，把 headerinc.h 声明与 header.y 定义统一为
  `const char *`，与已是 const 的 header.c 对齐；header.y/header.c 内
  `libsieve_do_error_header(..., s)` 调用加 `(char *)` 显式转换，避免 const 传给
  `char *msg` 回调的 discards-qualifiers 警告。调用点在 build() 的 _patch_fno_common
  之后、时间戳刷新之前，保证 bison shims 不会覆盖。幂等，锚点缺失时抛错并打 ERROR 行。
- 待真机预检验证 header.lo 编译通过、链接通过与 37 项上游测试。

## Round-12（2026-09-18 test_package CMake 编译器失败修复）

- 现象：主包编译 + 37 项上游测试 + 手工安装已全过（Package built），test_package 的
  cmake.configure() 失败：CMake Error at CMakeLists.txt:2 (project)，CMAKE_C_COMPILER
  指向 /data/service/hnp/bin/clang，被报 missing / unable to compile。
- 改动（仅 test_package/conanfile.py，未动主包语义与测试口径）：generate() 在
  TMPDIR/SHELL/CONFIG_SHELL 之外双注入 CC/CXX（实测可运行者）；build() 内对
  conf、CC/CXX 环境、hnp 绝对路径、PATH 候选逐个做 --version 实测，取可运行的
  C/CXX 路径，按整行替换 conan_toolchain.cmake 的 CMAKE_C/CXX_COMPILER
  FORCE 行并同步 CC/CXX 环境变量，之后无参 configure；C 无可用驱动而 CXX
  可用时复用已验证的 CXX 驱动作为 C。行前缀匹配实现，无正则。
- 待真机预检验证 test_package 配置通过与 2 项 ctest。

## Round-11（2026-09-18 真机 make install install-libLTLIBRARIES 根因修复）

- 现象：编译与 37 项上游测试已全过（37/37 passed），`package()` 的 `make install DESTDIR`
  在 `install-libLTLIBRARIES` 失败：`.../bin/install -c .libs/libsieve.a .../p//lib/libsieve.a`
  之后紧跟 `chmod 644 .../p//lib/libsieve.a: No such file or directory`，`make[2] Error 1`。
  平台能力 `HMBS_PLATFORM_CAPABILITIES={..., "install_shim":true, "hardlink":0, "symlink":1, "chmod":0, ...}`，
  老 libtool 安装链（install(1) + 显式 chmod 644 + ranlib）在 HMDFS（chmod/hardlink 不支持）上脆弱。
- 改动：`package()` 不再调用 `make install`，改为 HMDFS 安全的纯 Python 手工安装——
  从浅工作目录 `_hmbs_workdir()` 下的 `.libs/libsieve.a`（已 ranlib）经 `conan.tools.files.copy`
  拷入 `package_folder/lib`，从源码树发现的 `sieve2*.h` 拷入 `package_folder/include`（shared 时对应拷 `.so*`，
  遇 symlink 则拷目标内容、不留 symlink）；缺 `libsieve.a`/`sieve2.h` 时打 ERROR（WORKLS/SRCLS）并抛错，
  绝不静默跳过。无 shell、无 install-sh、无 chmod/hardlink。
- 上游语义/测试口径未动；待真机预检验证 package() 通过与 test_package 2 项。

## Round-10 (2026-09-18 upstream 36/37 failed)
- Phenomenon: testcomp passed, all 12 valid + 24 message runs failed with SCRIPT PARSE unexpected \$undefined on trailing empty line (script10 line25, script11 line9, script12 line6).
- Root cause: sv_test/example.c read_file stores fgetc EOF (-1) as 0xFF byte (while(!feof) loop); lexer fallback return yytext[0] promotes to -1 on x86-signed-char (treated as EOF by bison <=YYEOF) but to 255 on ARM-unsigned-char (AArch64 default) -> \$undefined. Genuine harness bug exposed by char-signedness difference, not a library bug.
- Fix: new _patch_example_eof() byte-level edit, f_buf[f_pos]=fgetc(f) -> {int _c=fgetc(f); if(_c==EOF) break; f_buf[f_pos]=(char)_c;} test-harness only, assertions unchanged. Called in build() after _patch_headererror_const.
- Expect: 37/37 upstream pass on next preflight.
