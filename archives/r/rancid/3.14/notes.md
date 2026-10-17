# rancid 3.14 适配笔记

## 编译环境
- 构建系统: autotools（release tarball 自带生成的 `configure` + 各 `Makefile.in`，无需 autoreconf）
- 编译日期: 2026-10-09
- 编译器: clang/clang++ 15（OHOS aarch64，经 AutotoolsToolchain 注入 CC/CONFIG_SHELL）
- 状态: built

## 上游测试申报表（R26 清点）

**结论：上游无任何自动化测试**（`upstream_tests_exist: false`）。

- 源码审计逐项记录见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`：
  - 顶层及各子目录 `Makefile.am`：只有 `bin_PROGRAMS/bin_SCRIPTS/my_pkglib_DATA/dist_doc_DATA` 等安装目标，
    无 `TESTS / check_PROGRAMS / check-local / check_SCRIPTS` 目标；
  - `configure.ac`：仅 AC_PATH_PROG/AC_CHECK_HEADERS/AC_CHECK_FUNCS 探测，无任何测试宏或 AC_CONFIG_TESTDIR；
  - 发布包无 `t/`、`tests/`、`test/` 目录，无 `*.t` Perl 测试，`share/` 下的 `.exp` 是 expect/tcl 登录
    脚本模板（运行时工具，非测试）。
- 全包 grep 确认：`grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|check-local|check_SCRIPTS' */Makefile.am configure.ac` 无命中。
- 口经：upstream_test_total = 0；框架: none；`upstream_test_in_build: false`。
- 由 test_package 执行消费者视角验证（C 二进制执行 + perl 模块/脚本语法与加载）。

## 编译步骤

```bash
# 就地构建（rancid 自带 Makefile.in/configure，生成脚本用 $(srcdir)）
./configure --prefix=/          # AutotoolsToolchain 注入 CC/CONFIG_SHELL; 应用 expect/mktemp/ping 补丁
make -j1
make install DESTDIR=<package_folder>   # → {bin,etc,lib/rancid,share/rancid,share/man,var}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: can't locate expect.`（配置直接中止） | rancid 的 configure 对 `expect`、`mktemp`、`ping` 三个**纯运行时辅助工具**做硬性 `AC_PATH_PROG` + `as_fn_error` 探测；任一缺失即整体中止。三者都不是编译所需：expect 仅被 clogin/*login 登录脚本运行时使用，mktemp 仅用于生成 etc/rancid.conf 里的 PATH，ping 仅用于 lg 网路状态 CGI。 | 补丁 `0001-configure-expect-mktemp-ping-nonfatal.patch`：把三处 "not found" 分支改为 WARNING + 变量置空，并对 ping 语法探测加空值守卫；语义与上游本就对 sendmail 用的 WARNING 一致。工具存在时 configure 行为与上游完全一致（补丁只改 "not found" 分支）。 |
| 2 | 真机 HMFS：`configure: error: working directory cannot be determined`（compile 阶段失败） | rancid configure 顶部用 `ac_pwd=\`pwd\``（getcwd(3)）计算工作目录并做 `ls -di` 一致性校验；HMFS 部分挂载点不实现 getcwd(3)（报 "getcwd: cannot access parent directories"），`pwd` 输出为空 → 整链 `|| as_fn_error` 中止。目录本身可正常 cd/访问，仅 getcwd 不可用（同 adms 2.3.7 / nspr 4.37 / aribb24 1.0.4 已过门禁的同款问题）。 | 补丁 `0002-configure-hmfs-getcwd-fallback.patch`：把 `ac_pwd` 判定改为 `ac_pwd=\`pwd\` 2>/dev/null || ac_pwd="$PWD"`，随后保留原有 `test -n "$ac_pwd"` + `ls -di` 一致性校验；同时配方在运行 configure 前 `os.environ["PWD"]=self.source_folder` 预置。`$PWD` 也为空时仍按上游报错退出，等价于上游行为。 |
| 2b | 真机 HMFS：`./config.status: line 683: ./confijjiec/subs1.awk: Permission denied` → `could not setup config files machinery`（compile 阶段失败，config.status 临时目录不可写） | configure 末尾 config.status 生成 Makefile 时，autoconf 在 cwd 创建临时目录写 subs1.awk，模板 `tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\``，回退 `(umask 077 && mkdir "$tmp")`。HMFS 部分挂载点对 mktemp 以 0700 建出的目录（setgid 父目录上 0770）不可写（unsafe_local_mktemp），回退的 mkdir 继承 umask 077 同样建出不可写目录（cln/1.3.7、libapreq2 2.17 同指纹同解）。 | 补丁 `0003-configure-config.status-tmpdir-hmfs.patch`：在 configure 模板上把 `mktemp -d "./confXXXXXX"` 改为 `false`（恒走 autoconf mkdir 回退），并仅把该回退的 `(umask 077 && mkdir` 放宽为 `(umask 000 && mkdir`（0777），使 config.status 落地临时目录可写；其余安全临时用法不受影响。已在本机跑通 configure（含 config.status 全量生成）+ make -j1，无 conf 残留目录。 |
| 2b2 | 真机 compile 在第一轮 0003 后失败于 `WARN: 0003 patch: hunk no.1 doesn't match source file at line 7879 / actual: b'{'`（compile 阶段，补丁应用失败） | 0003 是**顺序应用**（conan 按 conandata 顺序 0001→0002→0003）的，但首版 0003 的 hunk 偏移是按**原始 configure**（tmpdir 区在 7879 行）生成的；0001 在 tmpdir 区之前加了几行 WARNING 块，使该区整体下移 8 行到 7887，导致 hunk 偏移失配、上下文对不上（expected 空行 vs actual `{`），conan/fuzz-0 严格匹配失败。 | 把 0003 重新生成：先对原始 configure 套用 0001+0002，再对"补丁后 configure"做 tmpdir 修改并 diff（hunk 偏移更新为 `@@ -7887,12 +7887,12 @@`），使它在顺序应用 0001/0002 之后能严格匹配。验证：全新树依次 fuzz-0 应用 0001/0002/0003 全部 APPLIES_OK；`sh -n configure` 通过；`./configure`+`make -j1` 退出码 0。 |
| 3 | 真机 `make[2]: *** [Makefile:418: install-pkgdataDATA] Error 64`（package 阶段失败，`install -c -m 644 COPYING CHANGES FAQ ... '.../p//share/rancid'`） | configure 找到的 INSTALL 程序是 HMBS 运行时 install shim，只支持 GNU 参数面的子集：单文件 `-c -m 755 src dst` 探针可过，但 automake 的 install-pkgdataDATA 等多文件 `-m 644 <f1..fn> <dir>`（及 -d/-t）调用以 Error 64 (EX_USAGE) 拒绝（libapreq2 2.17 同指纹同解）。 | `package()` 改为探测可用的 install，并写一个只依赖 cp/mkdir/chmod 的确定性 POSIX 安装包装器（覆盖 -c/-m/-d/-t/-D、单/多文件拷贝），经命令行 `INSTALL=<wrapper> -c` + `MKDIR_P=mkdir -p` 传给 `make install`，替代 configure 烘焙的 INSTALL。注意包装器脚本内 `${1#-m}`/`${1#-t}` 在 Python `str.format` 里须写成 `${{1#-m}}` 转义（初版漏转义会 `KeyError: '1#-m'`）。验证：本机 `make install` 用包装器退出码 0，176 个文件全安装且无 0 字节（bin/lib/etc/share/man 就绪）。 |
| 3 | 运行时焙入的绝对 prefix 路径（自包含 prefix 设计） | rancid 脚本把 `@prefix@`（= `/`）焙进 `@INC`/路径（如 `push(@INC, "/lib/rancid")`），conan 安装到自身缓存目录后脚本直接运行会在系统根路径找模块。 | 这是 rancid 的原生自包含 prefix 设计，非本次引入缺陷；conan 侧按 `--prefix=/` 归一到 package_folder，consumer 测试用 `PERL5LIB`/`-I` 指向包内 `lib/rancid` 校验模块可加载，C 二进制可直接执行。 |

## 源码修改

- `0001-configure-expect-mktemp-ping-nonfatal.patch`：
  修改生成的 `configure` 三处硬错误（expect/mktemp/ping "not found" 分支）为 WARNING + 置空，并为 ping 语法探测加 `if test "x$PING_PATH" != "x"` 守卫，避免空变量执行。
- `0002-configure-hmfs-getcwd-fallback.patch`：
  修改生成的 `configure` 顶部 `ac_pwd` 计算，`pwd` 失败（HMFS getcwd 不可用）时回退 `$PWD`；配方 `build()` 运行 configure 前预置 `os.environ["PWD"]=self.source_folder`（对齐 aribb24 1.0.4 已过门禁的三重兜底做法）。
- `0003-configure-config.status-tmpdir-hmfs.patch`：
  修改生成的 `configure` 中 config.status 临时目录逻辑（cln/1.3.7、libapreq2 2.17 同指纹）：把 `mktemp -d "./confXXXXXX"` 改为 `false` 恒走 autoconf `mkdir` 回退，并把该回退 `(umask 077 && mkdir` 放宽为 `(umask 000 && mkdir`（0777），避免 HMFS 对 mktemp-created/umask-077 临时目录不可写导致的 `can't create ./confXXX/subs1.awk: Permission denied`。

## 依赖版本

- perl（>=5，Socket.pm >= 2.006）：每支 rancid 脚本/模块的真正硬依赖，OHOS 发行版自带。
- 零编译期外部库依赖；两个 C 助手只依赖 libc。

## 验证结果

（本机非 conan 探索性验证；最终以 hmbs 真机 conan create 为准）
- 三补丁（0001/0002/0003）顺序套用到原版 `configure` 后 `sh -n configure` 通过；`./configure --prefix=/tmp/rancid-prefix` 退出码 0，config.status 全量生成各 Makefile/config.h/bin scripts，无 `conf*` 临时目录残留。
- `make -j1` 退出码 0：`bin/par`、`bin/hpuifilter` 与全部 perl 脚本/模块生成。
- `make install DESTDIR=... INSTALL=<wrap> -c MKDIR_P=mkdir -p` 退出码 0：176 个文件全安装且无 0 字节（bin/lib/rancid/etc/share/rancid/man/var 就绪），覆盖此前 Error 64 的多文件 `-m 644` DATA/脚本/man 安装路径。
- `make install DESTDIR=/tmp/stage2` 退出码 0：`bin/`、`etc/`、`lib/rancid/`、`share/rancid/`、`share/man/`、`var/` 就绪。
- `bin/hpuifilter`（无参数）打印用法并退出码 64（EX_USAGE）；`bin/par -h` 退出码 64 —— 稳定的消费者断言。
- `perl -Ilib -c lib/rancid.pm` → "syntax OK"；`perl -Ilib -c bin/rancid` → "syntax OK" —— perl 模块/脚本语法有效。

## 上游测试声明格式修正（R26 no_tests）
- 首次预检以 incomplete 拒绝：`no_tests 必须显式设置 upstream_tests_exist: false 并提供审计`，根因是 `test_package/MANIFEST.yml` 缺失（conanfile.py 的 HMBS_UPSTREAM_TEST_RESULT 已引用它，但文件未落地）。
- 修正：新建 `test_package/MANIFEST.yml`，结构化为 `upstream_test_audit` 列表（多组 source+findind 证据项 + conclusion 结论项），`upstream_tests_exist: false`、`upstream_test_total: 0`、`upstream_test_count_method: manual_audit`、顶层 `assertion_count: 5` 与 test_package 5 项断言/真机 discovered=5 对齐；同步版本级 `manifest.yaml` 补 `upstream_tests_exist/upstream_test_total/upstream_test_count_method/upstream_test_audit/reason/test_package_test_count/assertion_count`。
- 保持 conanfile.py `HMBS_UPSTREAM_TEST_RESULT`（status=no_tests, framework=none, discovered=0, executed=0）与 reason 一致。

## 2026-10-11 CI #81465 复检：系统级 fork EAGAIN（worker 基础设施，非配方）
- 当前 head 6721fa8fb 真机预检已 passed；CI（CI-032，build #81465 / logid 495050）在 conan-build-test 阶段失败。
- 决定性证据（全新从 Buildbot REST 拉取完整日志逐字核对）：
  - KC1（knowledge_check.sh，rancid 之前完全无关）报 `fork: retry: Resource temporarily unavailable`；
  - JC1（junk_check.sh，同样与 rancid 无关）报同一 `fork: retry: Resource temporarily unavailable`；
  - rancid 的 `./configure --prefix=/` 连续约 25 次 `fork: retry/Resource temporarily unavailable` 后硬 EAGAIN，`pwd/ls/test` 全无法执行，ac_pwd/srcdir 为空 → 连锁报 `cannot find sources (CHANGES) in  or ..`。
- 结论：这是 CI-032 worker 的**系统级进程/task 容量耗尽（EAGAIN）**，作用于整台 worker 所有子进程，KC1/JC1 早于 rancid 构建即同报即证明与 rancid 配方无关；真机预检 passed 亦证明配方正确。守则规定 worker/基础设施故障不得改代码、空提交或重触发。工作树保持干净，等待后端在健康 worker 重试。
