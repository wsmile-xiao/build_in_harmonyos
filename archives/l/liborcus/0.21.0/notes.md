# liborcus 0.21.0 适配笔记

## 源码信息

- 上游：https://gitlab.com/orcus/orcus（tag 0.21.0）
- 包：liborcus-0.21.0.tar.xz（1857 个成员），sha256
  `1c6e473d6b8a63d61d0e6874a1762d6f0e0e78338d763e48ac93126ecde19b37`
- 许可证：MPL-2.0（LICENSE 文件）
- 构建系统：autotools（configure 由 GNU Autoconf 2.71 生成，dist 自带；config.sub 时间戳 2022-01-03）
- C++17（configure.ac: AX_CXX_COMPILE_STDCXX_17 mandatory；profile compiler.cppstd=17 一致）

## 源码可信度核验（下载链）

| 来源 | 结果 |
|------|------|
| GitLab Release 页面列出的 sha256（tar.xz） | `1c6e47…de19b37` |
| GitLab Generic Packages 下载实测 | 大小 2267752，sha256 一致 |
| Debian .dsc（0.21.0-1）记录的 .orig.tar.xz | sha256 完全相同（字节一致） |
| kohei.us/files/orcus/src/liborcus-0.21.0.tar.xz | 实测是 0.12.0 旧包，内容与路径名不符，已弃用 |

结论：conandata.yml 用有序列表，Debian pool（字节一致）放前面，GitLab 官方放最后回退，
全程 sha256 锁定。

## 范围（Scope）：关掉什么、为什么

| 开关 | 上游默认 | 本适配 | 原因 |
|------|----------|--------|------|
| spreadsheet-model | on | `--disable-spreadsheet-model` | 需 libixion-0.20>=0.20.0；制品仓没有 ixion 的 Conan 包（只有 0.19.0 的前 Conan 归档，不可用） |
| tools（orcus-csv/ods/xlsx 等 CLI） | on | `--without-tools` | 工具链 spreadsheet-model（见上）；且要 boost program_options（boost/1.90.0 未编译该库） |
| python 绑定 | on | `--disable-python` | 需 Python 开发环境，超出基础适配范围 |
| benchmark | on | `--without-benchmark` | 非验证内容 |
| parquet filter | off | 保持 off | 需 Apache Arrow |
| ods/xlsx/xls-xml filter | on | 保持 on | 仅需 zlib + boost 头文件 |
| gnumeric filter | on | `--without-gnumeric-filter` | 其 BOOST_IOSTREAMS 检查要链接 libboost_iostreams，而制品仓的 boost（1.90.0 仅头文件+Boost.Test；1.90.0.4.1 也无 iostreams 组件）都不提供该库 |

产物：liborcus-0.21（core import filter）+ liborcus-parser-0.21（parser），默认静态。
头文件安装到 `include/liborcus-0.21/orcus/`，`make install` 同时安装
`lib/liborcus-0.21.pc`（Name: liborcus-0.21）。

## 依赖版本

- mdds/3.2.1（满足 mdds-3.0>=3.0.0；header-only）
- boost/1.90.0（与 mdds 所需版本完全一致，图中只有一个 boost；本构建仅用其头文件）
- zlib/1.3.1（libwpd 0.10.3 已验证已发布的版本）

## 上游测试清点（tarball 审计，make check 口径）

本适配 flags 下 `make check` 运行 39 个 automake TESTS：

- src/（3，无条件）：enum-stream-test、orcus-xml-test、orcus-env-dump
- src/parser/（22，无条件）：base64-test、css-parser-test、csv-parser-test、
  json-parser-test、json-validation-test、numeric-parser-test、parser-base-test、
  parser-global-test、sax-ns-parser-test、sax-parser-test、sax-token-parser-test、
  stream-test、string-pool-test、threaded-json-parser-test、
  threaded-sax-token-parser-test、types-test、utf8-test、xml-namespace-test、
  xml-validation-test、xml-writer-test、yaml-parser-test、zip-archive-test
- src/liborcus/（14，受 filter 开关控制）：xlsx-sheet-context-test、
  odf-helper-test、css/json/yaml/xml/json-structure/json-map-tree-test、
  json-path-test、common-test、dom-tree-test、xpath-parser-test、
  xls-filter-utils-test

被特性开关排除的 16 个（上游总数 55）：src/ 的 9 个 filter 回归测试
（orcus-csv/detect/xml-mapped/json-mapped/ods/ods-import/xlsx/xls-xml/gnumeric-test，
需 tools+spreadsheet-model）、src/liborcus/ 的 2 个 gnumeric context 测试（需
gnumeric filter，即 libboost_iostreams）、src/spreadsheet/ 的 auto-filter-test（需
spreadsheet-model）、src/python/ 的 4 个 .py 测试（需 python+spreadsheet-model）。
配方把这 16 个记为 excluded（附原因），不计为通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.sub 不认 ohos 三元组 | dist 自带 config.sub 是 2022-01-03 版，无 ohos 项 | 沿用 libwpd 0.10.3 的验证做法：`--build=arm-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，四段名原样通过且保持交叉模式 |
| 2 | 设备无 pkg-config，ZLIB/MDDS 检查怎么做 | PKG_CHECK_MODULES 默认调 pkg-config | 直接导出 `ZLIB_CFLAGS/ZLIB_LIBS`、`MDDS_CFLAGS/MDDS_LIBS`（configure --help 明确这是 overriding pkg-config 的官方机制；变量非空时短路） |
| 3 | MDDS_LIBS 该填什么（header-only，无链接库） | pkg.m4 对空变量会回退到 pkg-config | 上游 misc/mdds.pc.in 本就没有 `Libs:` 行，故填空白值（语义为空，与上游元数据一致），附注释说明 |
| 4 | boost/1.90.0 无编译库，BOOST_SYSTEM 检查会失败吗 | 旧 boost.m4 会做链接测试 | 本包的 m4/boost.m4 在 boost>=1.70 时只做头文件检查（header only since 1.70 注释），无链接测试 |
| 5 | gnumeric filter 的 BOOST_IOSTREAMS 检查 | 该宏实测要链接 `boost::iostreams::file_descriptor`（编译型），制品仓的 boost 均未提供 libboost_iostreams | 关掉 gnumeric filter（`--without-gnumeric-filter`），其 2 个 liborcus 单元测试记入 excluded；ODS/XLSX/XLS-XML filter 不受影响 |
| 6 | kohei.us 镜像内容不符 | 作者站点的 0.21.0 路径实际是 0.12.0 包 | 弃用；改用 Debian pool（字节一致，已三源交叉验证） |
| 7 | 真机 `configure: error: C++ compiler cannot create executables`（2026-09-17 预检，`./configure` 实际跑在 `/usr/bin/zsh` 下） | 配方把 profile 的 `tools.build:compiler_executables` 绝对路径（`/data/service/hnp/bin/clang++`）原样导出，不校验文件是否存在；执行 worker 上该路径缺失（shell 解析同样回退到了 zsh）时，configure 连编译器都 exec 不起来；且旧 `_resolve_shell` 只认 `X_OK` 位，在 hmdfs（权限固定 660、`chmod` 无效）下会误判可用的 bash 不可用 | 新增 `_compiler_environment_items()`：解析 dict/str/scope 三种 conf 形态，逐项 `isfile` 校验，缺失时按同名回退到 `PATH` 查找（hmbs 会把真实工具目录前置到 `PATH`，与 test_package 的解析原则一致），导出前打 `CC/CXX` 取值与 `-print-target-triple` 探针日志；`_resolve_shell` 改用 `isfile + "-c exit 0"` 真实探针代替 `X_OK` 位判断；`_run` 在 configure 失败时自动转储 `config.log` 尾部 80 行，下一轮可直接定位 |

## 编译步骤（真机实际执行，由 HMBS 预检完成）

```bash
conan create archives/l/liborcus/0.21.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# 内部流程：源码拷贝到构建目录 → 辅助脚本 chmod +x → configure 的
# umask 077→022 → bash ./configure <flags> → make -j1 → make check
# （解析 automake 汇总并输出 HMBS_UPSTREAM_TEST_RESULT）→ make install
```

## 验证结果

- `make check`（上游 39 TESTS）：待真机预检回填
- test_package（消费者 15 断言，见 test_package/MANIFEST.yml）：待真机预检回填
- HMBS 机器证据标记：由真机测试命令输出，见预检日志
| 8 | `Making all in src include` + `zsh:cd:21: no such file or directory: src include`，`make -j1` 在 all-recursive 断裂（2026-09-17 预检） | make 的配方 shell 回退到 zsh；zsh 默认不做 POSIX 词分割，`for subdir in $$list` 把整个 `src include ...` 当成一个词传给 `cd` | 新增 `_resolve_make_shell()`（bash > /system/bin/sh > /bin/sh，拒绝裸 zsh，附 POSIX 分词探针；仅剩 zsh 时用 `-o shwordsplit` wrapper 兜底），`_prepare_run_environment(command)` 按命令分流：configure 用 bash/zsh，make/make check/make install 用 POSIX shell；`SHELL` 指向 make shell、`CONFIG_SHELL` 指向 configure shell |
| 9 | 同一指纹第 2 次：环境 SHELL 分流已部署（报错行号 607→759 证明新代码已跑）但 `zsh:cd: src include` 复现 | automake 生成的 Makefile 硬编码 `SHELL = /bin/sh`，优先级高于环境变量，故内层 recipe shell 仍是 zsh，环境导出覆盖无效 | 改用不同策略：`_make_shell_assignment()` 在 make 命令行追加 `SHELL=<posix>`（命令行变量优先级高于 Makefile 赋值），覆盖 `make -j1`、`make check`、`make install` 三处并打 effective command 日志；保留上一轮的 shell 探测与分流逻辑 |
| 10 | `make install` dies at `install-libLTLIBRARIES` with `chmod: cannot access '.../p//lib/liborcus-parser-0.21.a'` (2026-09-17 preflight, 39 upstream TESTS already passed) | `--prefix=/` expands libdir to `${exec_prefix}/lib` = `//lib`, so every DESTDIR path carries a double slash (`.../p//lib/...` in the log) and the libtool chmod step reports ENOENT on the device filesystem | Pin `--libdir=/lib --includedir=/include` (single-slash absolute paths) so DESTDIR installs are `.../p/lib/...`; pre-create `lib include lib/pkgconfig` under package_folder from Python before `make install` so the dest dirs exist regardless of shell mkdir -p normalization |
| 11 | Same chmod ENOENT on .../p/lib/liborcus-parser-0.21.a AFTER the round-2 --libdir=/lib normalization deployed (single-slash path, shifted line numbers prove new code ran), so the //lib double slash was not the cause | DESTDIR-side path fixed but libtool still reports the dest .a missing: either .libs/*.a was never built/kept at install time or the copy line (truncated away) failed first | New strategy (no repeat of round 2): package() verifies src/parser/.libs/liborcus-parser-0.21.a + src/liborcus/.libs/liborcus-0.21.a with sizes, lists both .libs dirs, rebuilds once via make -j1 when absent, then runs make V=1 install so the next log shows the real libtool copy line; download left untouched (conandata already ordered Debian-first + GitLab fallback + sha256, transient timeout recovered) |
| 12 | Same chmod ENOENT AGAIN after round-3 deployed (source .a proven present at 6933404 bytes, V=1 still truncated away the real libtool copy line), so neither the //lib path nor a missing build artifact is the cause | Copy of an existing .libs/*.a into an existing DESTDIR dir fails: prime suspect is the AC_PROG_INSTALL-baked absolute INSTALL program pointing under a prefix absent from this worker (same pattern as the CC/CXX /data/service/hnp fallback), with only the trailing chmod ENOENT surviving summarization | Different strategy, no repeat: package() now runs install captured (V=1) and re-emits the tail as [install] lines plus baked INSTALL value, PATH install lookup, parser .la fields and dest-lib listing; only when the baked INSTALL program is absent AND no PATH install exists it retries once with the dist install-sh -c; capture uses utf-8/errors=replace |
| 13 | Same chmod ENOENT a 4th time after round-4 deployed; round-4 log proves plain INSTALL works (dest lib already holds pkgconfig) while only the libtool-wrapped copy fails, and source .a exists at 6933404 bytes — so //lib path, missing artifact, and baked-INSTALL hypotheses are all falsified | Libtool-specific failure in install-libLTLIBRARIES on the device: source archive exists, DESTDIR dir exists, plain `install -c` succeeds, but the libtool `install -c .libs/*.a dest` + `chmod 644 dest` sequence never materializes the dest .a | New route, no repeat of rounds 2-4: package() tries normal install once, then on failure runs `make -j1 -k V=1 install` (headers/pc still land) plus Python `shutil.copy2` of the two verified .libs archives (plus .so companions when present) into package lib with size logging and non-empty hard verification |
| 14 | test_package compile fails at orcus/base64.hpp file not found while lib archives exist (2026-09-18 preflight) | make -k install truncated by failing libtool target so headers never landed, plus package_info only exposed include/liborcus-0.21 | New route, no repeat of lib-copy rounds: package() unconditionally verifies headers/pc via _ensure_headers_and_pkgconfig (Python copy of staged include/orcus to include/liborcus-0.21/orcus plus built pc files, hard-gated on base64/csv/json/sax/string_pool headers); package_info now exposes both include/liborcus-0.21 and include so either layout satisfies the consumer include |
| 15 | CI #50593 configure dies at `shell-init: getcwd: cannot access parent directories` + `configure: error: working directory cannot be determined` under `/data/service/hnp/bin/bash ./configure` while the same commit passed HMBS preflight | OHOS system bash getcwd() returns ENOTSUP on HMDFS deep dir `p/b/<hash>/b/build-release` (DRAFT-6487-classads-configshell-hmdfs-getcwd); recipe pinned hnp bash first with only an `exit 0` probe (passes anywhere) and used the deep default layout, so CI-032 always picked the broken shell in the broken dir | New route, no repeat of install rounds: layout() now shallow (`src_folder="."`, `build="."`, cyrus-sasl-login precedent); `_shell_passes_getcwd()` runs live `pwd` probe in build/source dir and both `_resolve_shell`/`_resolve_make_shell` skip candidates failing it, so hnp bash is kept only where its getcwd works, otherwise PATH bash wins; configure capability preserved (configure shell still bash-only, never toybox sh) |
| 16 | 真机 `source()` 在 `deb.debian.org` 上 `Read timed out`（2026-09-18 预检，首选 Debian URL 超时后 SSH 断开，未走到 GitLab 回退） | 首选单点直连官方 Debian CDN，超时即失败；conandata 已是有序列表但前两位都是境外直连（deb.debian.org / gitlab.com），国内真机网络下无近端回退 | 新路由（不碰 sha256、不改构建逻辑）：conandata 改为五源有序列表——国内 Debian 镜像（aliyun/tuna/ustc，同 ci/conan/build_and_test.sh 的 GNU/GNOME 镜像集）放前面，同路径 `/debian/pool/...` 字节一致，官方 deb.debian.org 居中，GitLab 官方最后回退；manifest 主 URL 同步为 aliyun 首选 |
| 17 | CI #50803 configure 报 `C++ compiler cannot create executables`（exit 77），同一次构建里 `clang++ -print-target-triple` 探针 rc=0、源码下载成功 | 候选根因是 TMPDIR 指向存在但不可写的目录：`_writable_tmpdir` 只做 `isdir + makedirs`，无真实写入探测；clang 建临时文件失败时 autoconf 把它报成编译器损坏（coinor-vol 1.5.4 同征已验证：只读/不存在 TMPDIR 必现 Error 77）。叠加诊断盲区：`_dump_config_log` 只转储最后 80 行，而那正是 autoconf 变量转储区，真正的 conftest 错误在中间被截掉 | 新路由（不碰三元组/编译器/下载逻辑）：`_writable_tmpdir` 改为逐候选真实写入探测（makedirs + 1 字节写 + unlink），失败落到下一候选并打日志，`build_folder/.tmp` 恒为候选；`_dump_config_log` 改为先吐 failure marker 上下文（cannot create executables / unable to make temporary file / failed program was 等 ±12 行，最多 3 处）再吐尾部 40 行，双通道输出 |
