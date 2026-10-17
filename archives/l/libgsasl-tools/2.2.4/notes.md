# libgsasl-tools 2.2.4 适配笔记

## 结论

`conan-verify` 全绿，`status` 可用 `built`：

```
✅ G1: PASS   配方完整性检查
✅ G0: PASS   预构建风险评估
✅ G2: PASS   conan create (干净构建)
✅ G3: PASS   系统同名库隔离验证 (R26)
G4 / L2 / L4 / L5 全部执行无失败项
✅ 配方验证通过: libgsasl-tools 2.2.4
```

- 设备：OHOS 6.0 / armv8 / clang 15 / libc++ / Release，Conan 2.30.0
- 工具链 profile：`ci/conan/profiles/ohos-aarch64`

## 交付内容

只有一个可执行文件 `bin/gsasl`。上游 `src/Makefile.am` 就一行
`bin_PROGRAMS = gsasl`；`examples/` 里的 `client` / `client-serverfirst` /
`client-mech` / `smtp-server` 是 `noinst_PROGRAMS`，**不安装**。所以这个
二进制就是整个 tools 面，不需要在包里挑挑拣拣。

## 与库包的分工

| 归档 | 负责 |
|------|------|
| `archives/l/libgsasl` | `libgsasl.a`、`gsasl.h` / `gsasl-mech.h`、`libgsasl.pc` |
| 本包 | `bin/gsasl` |

上游把库、程序、示例、文档、po 全塞进同一个 `./configure && make`
（顶层 `SUBDIRS = lib po gl src examples tests doc`），库/程序的边界只在
Makefile 层：`lib/src/Makefile.am` 声明 `lib_LTLIBRARIES = libgsasl.la` +
`include_HEADERS`，`src/Makefile.am` 声明 `bin_PROGRAMS`。

因此本包照样全量构建，但只安装 `src/`：

```python
autotools.make(args=["-C", "src", f"DESTDIR={self.package_folder}"],
               target="install-exec")
```

这与 ldns-tools 的 `install-drill install-examples` 是同一个模式
（聚合 `make install` 会把 `lib/`、`include/`、`share/` 一起装上）。
`package()` 之后仍然防御性删掉 `include/ lib/ share/`，保证同一个文件
只有一个属主。

## 补丁与平台处理

| 项 | 说明 |
|----|------|
| `patches/0001-build-aux-config.guess.patch` | 按知识库 **E007** 用 `scripts/patch-autotools-ohos.pl` 注入 `__OHOS__` LIBC 探测 + `*:HarmonyOS:*:*` 分支。gsasl 2.2.4 自带的 config.guess 时间戳是 **2025-07-10**，仍然只认 `aarch64:Linux:*` |
| `patches/0002-build-aux-config.sub.patch` | 同一份脚本注入 `ohos-linux` → `basic_os=linux-ohos`；config.guess 猜出的三元组必须再被 config.sub 接受，否则 `Invalid configuration` |
| `configure` 的 `umask 077 && mktemp -d ./confXXXXXX` | HMDFS 忽略 chmod，`config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied`；`build()` 里把两处改成 `umask 000 && mkdir -p $TMPDIR/conf$$`（与 ldns-tools / libdv-tools 同一补丁模式） |

补丁生成后在本地核对过：应用补丁后，用假 `uname`
（`uname -s` = `HarmonyOS`、`-m` = `aarch64`）跑
`build-aux/config.guess` 输出 `aarch64-unknown-linux-ohos`，
`config.sub` 同样接受该三元组。

## configure 选项与理由

| 选项 | 理由 |
|------|------|
| `--disable-shared --enable-static` | libgsasl 静态链进 `gsasl`。产物自包含，既不会在 `lib/` 被删掉后出现 `DT_NEEDED libgsasl.so.0` 加载失败，也不会和 `libgsasl` 包抢文件所有权 |
| `--disable-nls` | 应用包不需要 gettext 目录，顺带避开 `po/` |
| `--disable-gtk-doc` | worker 上没有 gtk-doc |
| `--without-gnutls` | **关键**：上游用 `AC_LIB_HAVE_LINKFLAGS(gnutls, ...)` 探测，这个 gnulib 宏查的是系统目录与 `LD_LIBRARY_PATH`，不是 pkg-config；不关掉就可能被 `/usr/local` 的同名库满足，链接行被污染、产物带上没人交付的 `DT_NEEDED`。功能代价：`gsasl --starttls` 不可用 |
| `--without-stringprep` | 同上（`AC_LIB_HAVE_LINKFLAGS(idn, ...)`，GNU libidn）。功能代价：非 ASCII 用户名不参与 stringprep 规范化 |
| `--disable-gssapi --disable-gs2` | OHOS 上没有 GSS-API 实现（krb5 家族），开着只会让 `configure` 去找不存在的东西 |

## 刻意**没有**做的事

`src/Makefile.am` 里 `gsasl_cmd.c` / `gsasl_cmd.h` 由 `gengetopt` 从
`src/gsasl.ggo` 生成，而生成规则的依赖里带着 `Makefile.am`：

```make
gsasl_cmd%c gsasl_cmd%h: gsasl.ggo Makefile.am
	$(AM_V_GEN)gengetopt --unamed-opts="HOST [PORT]" \
		--no-handle-version --no-handle-help --input $< --file-name gsasl_cmd
```

发行 tarball 里所有文件时间戳相同（`2026-06-16 05:36:52`），所以默认不会触发
重生成；但**只要打任何触碰 `src/Makefile.am` 或 `src/gsasl.ggo` 的补丁，`make`
就会去调用 worker 上根本不存在的 `gengetopt`**。本包因此不改上游源码，
只补 `build-aux` 下的两个辅助脚本。

`--version` / `--help` 也不需要补丁：`src/gsasl.c` 自己处理这两个选项
（gengetopt 生成时用了 `--no-handle-version --no-handle-help`），
两条路径都返回 `EXIT_SUCCESS`；无参数调用同样打印用法后返回 0。

## 验证结果

`test_package/test.sh` 14 项断言全部通过（设备实测输出节选）：

```
[test] gsasl --version
        [ok] gsasl (GNU SASL) 2.2.4
[test] gsasl --client-mechanisms
        [ok] 13 client mechanisms, includes SCRAM-SHA-256
[test] gsasl --mkpasswd --mechanism SCRAM-SHA-256
        [ok] 4 fields, iteration count honoured
[test] gsasl --mkpasswd is deterministic
        [ok] two runs produced identical output
[test] gsasl --no-such-option (expected failure)
        [ok] unknown option rejected
[test] /data/service/hnp/bin/llvm-readelf -d bin/gsasl | grep NEEDED
        [ok] no libgsasl dependency
All tests passed.
```

覆盖范围：`--version` / `--help` 退出码契约（平台 L2 冒烟）、无参数调用退出 0、
客户端/服务端机制清单（13 个客户端机制、含 `SCRAM-SHA-256`）、
用固定 salt + iteration-count 的 `--mkpasswd` 可复现密钥派生
（SCRAM-SHA-256 与 SCRAM-SHA-1，两次运行必须一致、换密码必须不同）、
未知选项与未知机制两个反例、以及 ELF 依赖自检（产物不得再有 `libgsasl` 的
`DT_NEEDED`）。

## 上游测试套件

`tests/Makefile.am` 里有 26 个 C 测试程序 + 6 个 shell 脚本，通过

```make
AM_TESTS_ENVIRONMENT = \
	GSASL="$(LIBTOOL) --mode=execute $(LOG_VALGRIND) ../src/gsasl$(EXEEXT)" \
	...
```

**直接驱动 `gsasl` 程序本身**。这套用例归库归档（`archives/l/libgsasl`），
因为 `ctests` 还依赖 `libutils.la` 与库侧 API；tools 归档另外用
`test_package/test.sh` 覆盖命令行契约与 SCRAM 派生。

## 已知限制

- 无 STARTTLS（GnuTLS 被显式关闭，见上）。
- 无非 ASCII / IDN 规范化（libidn 被显式关闭，见上）。
- 无 GSSAPI / GS2 / GS2-KRB5 机制。
- 因此 `gsasl --client-mechanisms` 列出 13 个机制而不是上游全量。