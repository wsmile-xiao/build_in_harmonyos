# rlog 1.4 适配笔记

## 编译环境
- 构建系统: autotools（上游 tarball 自带 2008 年生成的 configure/Makefile.in，无需 autoreconf）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，`--target` 由 conan profile 提供）
- 目标平台: OHOS armv8 / aarch64-linux-ohos
- 状态: built

## 编译步骤

```bash
# 设备私有 CONAN_HOME + 任务私有 TMPDIR；profile = ci/conan/profiles/ohos-aarch64
conan create <worktree>/archives/r/rlog/1.4 -pr:h=<profile> -pr:b=<profile> \
    -c tools.build:jobs=2 --build=missing
```

configure 实际参数（配方 generate() 产出）：

```
--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
--enable-shared --disable-static            # shared=True 默认
--prefix=/ --bindir=${prefix}/bin --libdir=${prefix}/lib --includedir=${prefix}/include
```

`make` 串行执行（`-j1`），随后 build() 运行上游 noinst 程序 test/testlog，
最后 `make install`（DESTDIR=package_folder，install 含 librlog、16 个头文件、
librlog.pc 与 docs 下的 html/refman.pdf）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 `./configure` 报 `cannot guess build type` / `config.guess: unable to guess system type`（设备实测 exit 1） | 2007 版 config.guess 早于 aarch64 与 HarmonyOS，探测失败 | 补丁 0001 在 UNAME 判定前对 `HarmonyOS:aarch64` 直接给出 `aarch64-unknown-linux-gnu` |
| 2 | `./config.status: ./confXXXXXX/config.h: Permission denied`，随后 `make: No targets specified and no makefile found` | config.status 用 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录；HMDFS 上该 0700 目录内无法写入，Makefile/config.h 生成全部失败 | 补丁 0002 改为 `(umask 022 && mkdir "$tmp")`（与归档 a52dec/libagg 同类处置） |
| 3 | 裸 configure 报 `C++ compiler cannot create executables`（`g++: inaccessible or not found`） | 2006 版 autoconf 的 C++ 编译器候选表不含 clang（设备上无 g++/c++），configure 退化为 g++ | 补丁 0002 在 configure 的两处候选表前加入 `clang++` |
| 4 | `make install` 在 docs 子目录失败：`/bin/sh: ../mkinstalldirs: No such file or directory` | docs/Makefile.am 的 install-data-local 硬编码相对路径 `../mkinstalldirs` 与 `html/*`，在 Conan 的 VPATH 构建目录中都不存在 | 补丁 0003 改为 `$(top_srcdir)/mkinstalldirs` 与 `$(INSTALL_DATA) $(srcdir)/html/*` |
| 5 | `make: jobserver mkfifo: ...: Operation not permitted` | 并行 make 需在 TMPDIR 建 jobserver fifo，HMDFS 上 mkfifo 不被允许 | 配方 `autotools.make(args=["-j1"])`（归档 450 处同类做法） |
| 6 | build() 运行上游 `./rlog/test` 时 libtool wrapper 报 `clang-15: error: no such file or directory: 'test.o'` | wrapper 记录的 relink 命令形如 `(cd ; ... -o $progdir/$file test.o ./.libs/librlog.so)`（cd 无参数），HMDFS 上 getcwd 失效时相对路径无法解析 | 配方直接执行 `.libs/test`、`.libs/testlog` 真实二进制并显式给出 `LD_LIBRARY_PATH`，不经过 wrapper |

> 说明：自带 `config/config.sub`（2008）经设备实测**接受**本配方使用的
> `aarch64-unknown-linux-gnu`（`sh config.sub aarch64-unknown-linux-gnu` exit 0，
> 仅 `*-ohos` 形式被拒），因此不产生补丁；配方显式给出 `--build/--host` 三元组。

## 源码修改

以 patches/ 下的补丁形式提供（均由 `refresh-patch --auto` 生成）：

| 补丁 | 目标 | 内容 |
|------|------|------|
| 0001-config-config.guess.patch | config/config.guess | `HarmonyOS:aarch64/arm64` 直接判定为 `aarch64-unknown-linux-gnu` |
| 0002-configure.patch | configure | config.status 临时目录改用 `umask 022 && mkdir`（HMDFS 权限适配）；C++ 编译器候选表加入 `clang++` |
| 0003-docs-Makefile.in.patch | docs/Makefile.in | install-data-local 改用 `$(top_srcdir)/mkinstalldirs`、`$(srcdir)/html/*`（VPATH 构建适配） |

未改动任何库源码（rlog/*.cpp、*.h 保持上游原样），也未改动 config.sub。

## 依赖版本

- 无 Conan 依赖（`requirements()` 为空）；libc/libc++/pthread 由 OHOS SDK 与 conan profile 提供
- 构建工具：autoconf 2.73 / automake 1.18.1 / libtool（仅 configure 脚本运行时需要，不重新自举）、GNU make 4.4.1

## 验证结果

```bash
# 1) 完整 conan create（含 test_package）PASS
conan create archives/r/rlog/1.4 -pr:h=<profile> -pr:b=<profile> --build=missing
# → 编译/链接/打包/消费者测试全部通过

# 2) 上游 noinst 程序（build() 内实际执行）
./rlog/test      # exit 0：订阅-发布、rDebug/rWarning/rError、rAssert→Error、计时 API
./rlog/testlog   # exit 0：日志调用开销基准（dormant/active 两路径）

# 3) 上游 make check：无测试注册（0/0 依据）
make -C rlog check
# → make: Nothing to be done for 'check'.（rlog/Makefile 与顶层 Makefile 均无 TESTS 赋值，
#    rlog/Makefile.am 只有 noinst_PROGRAMS = test testlog）

# 4) 消费者测试（test_package/test.cpp，11 项断言）
./test_rlog
# → rlog consumer test: checks=11 failures=0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/librlog.so.5.0.0 | 100800 B | 共享库（SONAME librlog.so.5） |
| lib/librlog.so, librlog.so.5 | 符号链接 | 开发用符号链接 |
| lib/pkgconfig/librlog.pc | — | pkg-config 元数据 |
| include/rlog/*.h | 16 个 | 公开头文件 |
| share/doc/rlog/ | — | 上游 html 文档与 refman.pdf（上游 Makefile.am 的文档安装） |

## 知识库对照（引擎实测命中）

| 本包问题 | 命中条目 | 与既有方案的差异 |
|---|---|---|
| HMDFS 下 config.status 的 0700 临时目录不可写 | E060（hmdfs, filesystem） | 条目建议在 tmpfs 中构建；本包改为补丁 `umask 022 && mkdir`——CI 与设备都需在普通目录直接构建，不能依赖 tmpfs |
| 裸 configure 无法在 HarmonyOS 上确定 build type | E160（platform，方案 `config-guess-harmonyos-patch`） | 与本包补丁 0001 做法一致 |
| 裸 configure 找不到 C++ 编译器（候选表无 clang） | E001（toolchain，方案 set-env-var） | 条目建议用环境变量指定编译器（conan 路径即如此）；本包另用补丁 0002 让裸 configure 也能找到 clang++ |
| docs 安装相对路径在 VPATH 构建下失效 | E443（ohos, autotools, conan, permissions, relocatable） | 本包补丁 0003 采用 `$(top_srcdir)`/`$(srcdir)` 形式 |
| 并行 make 的 jobserver fifo 不能 mkfifo | E292（testing） | 条目侧重 ctest 迁移；本包按归档主流做法用 `-j1` |

## 注意事项

1. **源码来源**：上游原站 `arg0.net`（现为 Google Sites 个人站）与 `rlog.sourceforge.net` 均已失效，
   tarball 取自 MacPorts distfiles；其字节与 Debian pool 的 `rlog_1.4.orig.tar.gz` 完全一致
   （sha256 `a938eeed…`，640641 B），属权威镜像上的原始上游源码。
2. **动态/静态**：librlog 不是 OHOS 系统同名库（系统与 sysroot 下均无 librlog），按非 system 库
   默认动态（`shared=True`）；`-o shared=False` 亦可构建（configure 显式给出两条开关）。
3. **测试口径**：上游只以 noinst_PROGRAMS 提供 test/testlog，没有 TESTS 注册，`make check` 为空；
   MANIFEST.yml 如实记录两个程序及其命令，build() 中实际运行。
4. `test` 程序会**故意**触发一次断言失败（`rAssertSilent` 测试断言机制），stderr 中的
   "Assert failed" 输出属预期行为，退出码 0。
