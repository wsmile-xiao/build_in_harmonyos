# rgxg 0.1.2 适配笔记

## 编译环境
- 构建系统: autotools（发布包内含已生成的 configure，无需 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang（OHOS SDK，profile `ohos-aarch64`，host == build）
- 依赖: 无（测试依赖 check/0.15.2，用 `test_requires` 注入，不进安装接口）
- 状态: built

## 软件说明
rgxg（ReGular eXpression Generator）是一个纯 C 的小库 + 同名命令行工具：把
CIDR 网段和整数区间直接编译成等效的正则表达式，常用于日志匹配、IDS/WAF 规则
生成。发布包同时产出 `librgxg.a`、头文件 `include/rgxg/*.h`、`lib/pkgconfig/rgxg.pc`、
命令行 `bin/rgxg` 与 5 个 man 页。上游 0.1.2 只有一个基于 Check 的测试程序
`tests/check_rgxg.c`，由 `make check` 驱动。

## 版本坐标
tag `v0.1.2`。取的是 GitHub Release 附件 `rgxg-0.1.2.tar.gz`（`make dist` 产物，
内含生成的 configure / Makefile.in），**不是** GitHub 自动生成的 tag 归档
（后者不含生成文件，sha256 也不同：附件
`554741f95dcc…` vs tag 归档 `273057c098b9…`）。

## 编译步骤
```bash
sh configure --build=aarch64-unknown-linux-gnu \
             --prefix=<pkg> --enable-static --disable-shared \
             --disable-dependency-tracking \
             CC=<sdk clang> \
             CHECK_CFLAGS=-I<check>/include \
             CHECK_LIBS='-L<check>/lib -lcheck -lm -lrt -lpthread'
make -j1
TEMP=$PWD/check-tmp TMP=$PWD/check-tmp TMPDIR=$PWD/check-tmp \
LD_LIBRARY_PATH=<check>/lib CK_FORK=no make -j1 check
make install -j1
```
配方在 `build()` 内真的执行 `make -j1 check`（上游官方套件），`test_package` 只是
额外的鸿蒙特有消费者测试，不替代上游测试。

## 遇到的问题与解决方案

| # | 现象 | 根因 | 处理 |
|---|------|------|------|
| 1 | `configure: error: /bin/sh build-aux/config.sub aarch64-unknown-linux-ohos failed`（`machine 'aarch64-unknown-linux' not recognized`） | 2020 版 config.sub 表里没有 OHOS；而 autoconf 只把**用户传入的 `--host`** 送进 config.sub 校验，`--build` 走 config.guess 的机器可读输出、不校验 | 只钉 `--build=aarch64-unknown-linux-gnu`、不给 `--host`：config.guess 的结论被显式值覆盖、config.sub 全程不参与；目标三元组由 profile 里的 OHOS SDK clang 决定，产物仍是 aarch64/musl（与 pexec/1.0 同法）。不把 ~1800 行生成文件差异带进 PR（避免 rule6 ③ 的「PR 过大跳过检视」） |
| 2 | config.status 报 `confXXXXXX/subs-1.sed: Permission denied` | autoconf 2.69 的 `(umask 077 && mktemp -d ...)`：HMDFS 对新目录强制 setgid，0700 临时目录连属主都写不进去（E114） | 打包前把 configure 里的 `(umask 077 && ` 替换成 `(`，不改任何源码逻辑 |
| 3 | 编译通过、`make check` 退出码 0，但一个上游用例都没跑 | 上游 `PKG_CHECK_MODULES(CHECK, [check >= 0.9.4], , [AC_MSG_RESULT([Check not found (testing via 'make check' disabled)])])` 是**优雅降级**：探测不到就把 HAVE_CHECK 置假、测试目标整个消失。真机没有 pkg-config 二进制（CI worker 才有 `/data/service/hnp/pkg-config.org`），探测必然失败 | 从 conan 的 check 依赖算出 `CHECK_CFLAGS`/`CHECK_LIBS`，作为 configure 命令行变量直接喂进去（pkg.m4 的 `if test -n "$CHECK_CFLAGS"` 分支会跳过探测）；并在 configure 之后断言生成的 `Makefile` 里出现 `check_rgxg`，否则 `raise ConanException`。机制与既有草稿 `DRAFT-10251-libnfc-tools-1.8.0-autotools-test-framework-guard` 同族 |
| 4 | `make check` 卡住/报无法创建 IPC 文件 | Check 0.15.2 的 fork runner 要创建再 unlink 一个临时文件，HMDFS 归一化权限；真机 `/tmp` 还是只读的 | 仅在该命令作用域内设 `TEMP/TMP/TMPDIR=<build>/check-tmp` 与 `CK_FORK=no`（进程内执行，注册的用例数与断言数不变） |
| 5 | 测试二进制 `error while loading shared libraries: libcheck.so` | 制品仓的 check 提供动态库 | `LD_LIBRARY_PATH=<check>/lib` 只注入到 `make check`，不进编译/链接探测 |
| 6 | `make install` 的 install-data-hook 用 `$(LN_S)` 造 man 页别名 | 与 HMDFS 无关，但 conan 包目录需要真实文件 | 实测直接通过（见验证结果）；如某台 worker 上失败，可用 `make install LN_S="cp"` 等价替换 |
| 7 | make -j8 报 fifo EPERM | HMDFS jobserver（E074） | 固定 `-j1` |

## 测试情况

### 上游官方测试
`make check` 执行 `tests/check_rgxg.c`：2 个 Check 循环用例
（`tcase_add_loop_test`）分别遍历 `cidr_regex[]` 的 600 条与
`range_tests[]` 的 450 条向量，逐条把生成的正则与期望串 `strcmp`。

| 口径 | 数量 | 取数命令 |
|------|------|----------|
| 数据向量（声明用，最大口径） | 1050 | `awk '/^static (cidr_test_t cidr_regex\|range_test_t range_tests)\[\] = \{/,/^\};/' tests/*.c \| grep -cE '^    \{ '` |
| Check 注册用例 | 2 | `grep -c tcase_add_loop_test tests/*.c` |
| 源码内断言调用点 | 4 | `grep -c 'ck_assert' tests/*.c` |

实跑结果（真机 OHOS PC aarch64，独立 `CONAN_HOME=~/work/psj/ch-rgxg`，2026-09-20 22:13）：

```text
checking for CHECK... yes
RUN: ... make -j1 check
100%: Checks: 1050, Failures: 0, Errors: 0
CREATE_EXIT:0
TOTAL=42 PASS=42 FAIL=0     (test_rgxg.c)
TOTAL=17 PASS=17 FAIL=0     (test_cli.sh)
```

即 Check 框架自己上报的 `Checks:` 就是 **1050**（它把循环用例的每次迭代计为一个
check），声明数与实测数完全相等，不存在少报。

**破坏性反向验证（R34/L1e）**，对同一个已构建包目录做三组破坏再 `conan test`：

| 破坏 | 结果 | 归因 |
|------|------|------|
| 移走 `lib/` | 退出码 1 | `ld.lld: error: unable to find library -lrgxg` |
| 移走 `include/` | 退出码 1 | `fatal error: 'rgxg/net.h' file not found` |
| 只移走 `bin/`（库完好） | 退出码 1 | 测试自身报 `[FAIL] bin/rgxg is installed and executable`，其余 36 条仍 PASS |
| 全部还原 | 退出码 0 | `TOTAL=42 PASS=42 FAIL=0` + `TOTAL=17 PASS=17 FAIL=0` |

产物：`bin/rgxg` `e_machine=b700`（EM_AARCH64）、`NEEDED` 只有 `libc.so`，
sha256 `5329900a75c10c31c38b8004892b006cab466aea9fba67cbcf4b4404f8a4ddb1`；
`lib/librgxg.a` sha256 `b738d16d27e3c95371337f7f283f842ffbca1549819896d79b3bcd297cb9d45e`。

### 鸿蒙特有（消费者）测试
`test_package/test_rgxg.c` 与 `test_package/test_cli.sh`：
- 先按上游表格里的期望串做已知答案比对（CIDR /32 /24 /0、IPv6、十进制与二进制区间、
  `RGXG_NOOUTERPARENS`/`RGXG_LEADINGZERO`/`RGXG_NOMIXEDNOTATION` 选项语义、
  转义与择一生成）；
- 再把生成的正则交给**真机 libc 的 POSIX regex 引擎**实际 `regexec`，断言
  「0.0.0.177 命中 /24、1.0.0.177 不命中」「7/31 命中 0..31、32 不命中」，
  这样即使上游期望串与本机正则语义有偏差也不会假绿；
- 校验包内 `bin/rgxg` 的 ELF 头（ELFCLASS64、小端、`e_machine==0xB7`），
  证明产物是真为 AArch64 生成、不是宿主机二进制冒充；
- 校验 `__OHOS__` 编译期宏、静态库/头文件/pkg-config/许可证齐备、错误路径返回码
  （`RGXG_ERROR_RANGE`/`RGXG_ERROR_BASE`、前缀越界）；
- 命令行侧比对 `rgxg cidr/range/escape/alternation` 的输出与上游答案表一致，
  并确认未知命令/缺参数/非法前缀都以非零退出码失败。

断言总数见 `test_package/MANIFEST.yml`（以真机实跑的 `TOTAL=` 为准）。
