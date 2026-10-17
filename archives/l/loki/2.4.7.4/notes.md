# loki 2.4.7.4 适配笔记

## 版本/来源

上游 = Simon Heath 的 Loki（MCMC 多元连锁分析，2003–2004 年代 C 程序）。
Debian orig tarball `loki_2.4.7.4.orig.tar.gz` 保持上游目录结构，sha256
`78bc51f4…` 与 `loki_2.4.7.4-12.dsc` 逐字符一致 → 用 HTTPS Debian pool URL。
上游自带**已生成**的 autotools 树（`configure` + `Makefile.in`）与**预生成**的
flex/bison 源（`param_lex.c`/`param_parse.c`）→ 真机无需 bison/flex。

## 构建（真机 `conan create` rc=0）

四个程序：`loki`、`prep`、`qavg`、`hist`。三处 bionic/clang 差异：

1. **`-fcommon`**：2003 年代 C 依赖 gcc 默认的 tentative definitions；clang 15 默认
   `-fno-common` 会导致 `loki`/`prep` 链接期 `duplicate symbol: MMsg/FMsg/strip_vars/…`。
   configure 时 `CFLAGS="-g -O2 -fcommon"`。（E491 / `DRAFT-clang-fno-common-header-globals`）
2. **`umask 077`**：`configure`/`config.status` 在 HMDFS 上无法建临时文件
   （`can't create ./confXXXX/…: Permission denied`）→ 用 `replace_in_file` 改 022。（E011/E528）
3. **`AR`/`RANLIB`**：configure 探测到 GNU 名，OHOS 只装 `llvm-ar`/`llvm-ranlib`
   → 显式传。（E012）

configure 的选项集（`--prefix` 等）默认即可；产物无外部依赖（仅 libm）。

## 上游测试（真实运行，7/7）

`test/` 提供 `make tests`，目标是 **7 个统计回归**：
`jvtst_1`、`jvtst_2`、`jvtst_cens`、`jvtst_lm`、`jvtst_mg`、`gaw9_tst`、`jvtst_3`。
每个测试用 `prep` 处理控制/参数文件、`loki` 跑 MCMC，再与 `test/standards/` 下的
记录标准 `diff`。真机 `make -j1 -B tests` 全部打印 `… OK`（各 < 3s）。

注意：`tests` 目标**不因失败返回非零**（规则只 echo）。配方在 `build()` 里捕获
make 输出，断言恰好 7 行 `... OK$` 且 0 行 `... Failed$`，否则构建失败。

## 消费者测试（鸿蒙特有，`test_package/test_loki.sh`，11/11）

1. 四个程序安装且可执行（4）
2. `loki -v` → `loki 2.4.7_4`，无参 → `No parameter file specified`（2）
3. `prep` 无参 → `No control file specified`（1）
4. `hist -h` usage，`hist <file>` 在合成数据上算直方图（2）
5. `qavg <file>` 在合成数据上算列均值（2）

## 路径判定

`-fcommon`/`-fno-common`（E491 + 草稿）、`umask 077`（E011/E528）、
`AR/RANLIB→llvm-*`（E012）均已覆盖 → **路径 A**，未做知识库扩展。
