# bas55 2.0 适配笔记

## 构建

- 构建系统：GNU Autotools（configure.ac + Makefile.am，tarball 内含 autoconf 2.69 生成的 configure，无需 autoreconf）
- configure.ac 无 AC_CANONICAL_HOST/BUILD 调用，configure 不依赖 config.guess/config.sub（tarball config/ 目录亦无这两个文件），无需三元组补丁
- 依赖：无第三方依赖；仅 libm（AC_SEARCH_LIBS pow m）。readline/libedit 为可选编辑增强（--with-readline/--with-libedit），默认不启用，getlin.c 以 HAVE_LIBREADLINE/HAVE_LIBEDIT 宏保护，缺省编译正常
- 需要 bison/yacc（AC_PROG_YACC，grammar.y）；设备 /data/service/hnp/bin/bison 可用
- 产物：单一二进制 src/bas55（bin_PROGRAMS），安装 bin/bas55 + share/bas55/*.BAS（SIEVE/HAMURABI/BAGELS）+ man/info/doc

## 补丁说明

`patches/0001-fix-configure-tmpdir.patch`（portability）：

- autoconf 2.69 生成的 configure 创建临时目录的片段为 `umask 077 && mktemp -d "./confXXXXXX"`（与 autoconf 2.72 同款，E081/E011）
- HarmonyOS HMDFS 上该写法与 E081（HMDFS tmpdir umask）冲突
- 改为 `${TMPDIR:-.}/confXXXXXX` + umask 022（与基线 dnsperf 0002 / tintin 0001 同一模式）
- 补丁由本机对官方 configure 精确 diff 生成，patch --dry-run 验证可应用

## HMDFS 适配

- 不使用 Conan Autotools helper：profile CONFIG_SHELL（bash）在 HMDFS 深路径下 getcwd 失败
- build() 将源码复制到 tempfile.mkdtemp（优先 TMPDIR）下的独立构建目录，用 /bin/sh 脚本完成 configure + make -j1 + make check + make install DESTDIR
- CC 取自 conan conf tools.build:compiler_executables（profile 注入），未设置时抛 ConanException，无硬编码路径
- configure.ac 无 AC_CANONICAL_*，无需 --build/--host 三元组

## 上游测试

- 上游 tests/ 目录：205 个 .test 脚本（automake TESTS，dist_check_SCRIPTS：p001-p106、p113-p130、p132-p202、p204-p208、printab/printspc/table/truend/pow）+ 213 个 .BAS 程序 + 205 个 .ok + 205 个 .eok（NBS Minimal BASIC 标准测试程序）
- 每个 .test 通过 chkout.inc（或等价逻辑）运行 `bas55 prog.BAS`，对 stdout 与 .ok、stderr 与 .eok 各做一次 diff 断言；p117.test 为 INFORMATIVE 特例（grep 通过标记）
- 断言口径：205 个测试脚本 × 2 个 diff 断言点 = 410 个断言点，由 make check 在 build() 中全量执行，全 PASS 才继续（set -e）
- 测试为纯批处理运行，无 TTY/GUI/网络需求，205/205 全部可在设备实测
- master 与 release tarball 的 tests 结构一致（p001-p208 + 5 个附加脚本），以 release tarball 为准

## 编译细节

- 无依赖头文件/库路径，CFLAGS 仅 build_type 优化 + NDEBUG
- make -j1（HMDFS 无 jobserver）
- make check 使用 TESTS_ENVIRONMENT 注入的 bas55=$(top_builddir)/src/bas55、srcdir、builddir
