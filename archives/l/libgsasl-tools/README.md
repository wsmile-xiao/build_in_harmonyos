# libgsasl-tools

`gsasl` —— GNU SASL 自带的命令行客户端/服务端程序。

## Description

- `gsasl --client-mechanisms` / `--server-mechanisms`：打印本库支持的机制清单。
- `gsasl --client --mechanism <MECH>`：以客户端身份与真实 IMAP/SMTP 服务端协商。
- `gsasl --server`：以服务端身份应答。
- `gsasl --mkpasswd --mechanism SCRAM-SHA-256`：派生 SCRAM 服务端口令（`{mech}count,salt,stored-key,server-key`）。

## Project URL
https://www.gnu.org/software/gsasl/

## License
GPL-3.0-or-later

## HarmonyOS 适配说明

### 构建信息
- **版本**: 2.2.4
- **构建系统**: autotools（不重新生成 configure，只对 `build-aux/config.guess` / `config.sub` 打补丁）
- **编译器**: clang 15.0.4
- **依赖**: 无（libgsasl 静态链进本包）
- **链接方式**: `--disable-shared --enable-static`

### 与库包的分工
`archives/l/libgsasl` 负责 `libgsasl.a`、`gsasl.h` / `gsasl-mech.h` 与 `libgsasl.pc`；
本包只负责 `bin/gsasl`。上游 `src/Makefile.am` 里只有 `bin_PROGRAMS = gsasl`
一行，而 `examples/` 是 `noinst_PROGRAMS`，所以这一个二进制就是整个 tools 面。
`package()` 里删掉 `include/ lib/ share/`，保证同一个文件只有一个属主。

### 平台限制与补丁
| 问题 | 根因 | 处理 |
|------|------|------|
| configure 报 `cannot guess build type; you must specify one` | 随包 `build-aux/config.guess` 是 2025-07-10 版，只认 `aarch64:Linux:*`，没有 HarmonyOS 分支 | 补丁 `0001`（按知识库 E007 用 `scripts/patch-autotools-ohos.pl` 注入 `__OHOS__` LIBC 探测与 `*:HarmonyOS:*:*` 分支） |
| 同一份脚本猜出的三元组被 config.sub 判为 `Invalid configuration` | `config.sub` 的 OS 白名单里没有 `ohos-linux` | 补丁 `0002`（同一份脚本注入 `ohos-linux` → `basic_os=linux-ohos`） |
| `config.status` 临时目录不可写 | configure 用 `umask 077 && mktemp -d ./confXXXXXX`，HMDFS 忽略 chmod | `build()` 里把 `configure` 两处改成 `umask 000 && mkdir -p $TMPDIR/conf$$` |
| 工具运行期找不到 `libgsasl.so` | 默认构建 `.so`，而 tools 包会删掉 `lib/` | `--disable-shared --enable-static` |
| 探测到系统 `/usr/local` 的 GnuTLS / libidn | `AC_LIB_HAVE_LINKFLAGS` 查的是系统目录与 `LD_LIBRARY_PATH`，不是 pkg-config | `--without-gnutls --without-stringprep`（保持 hermetic） |
| 没有可用的 GSS-API 实现 | OHOS 上没有 krb5/GSS | `--disable-gssapi --disable-gs2` |
| 新二进制无法执行 | 鸿蒙安全机制要求 ELF 带 `.codesign` | `package()` 内调用 `llvm-objcopy` + `binary-sign-tool` 自签名 |

### 与 `src/Makefile.am` 里的 gengetopt 规则有关的注意事项
`src/Makefile.am` 里 `gsasl_cmd.c` / `gsasl_cmd.h` 由 `gengetopt` 从 `src/gsasl.ggo`
生成，规则带 `Makefile.am` 作为依赖。发行 tarball 里所有文件时间戳相同，所以
不会触发重新生成；但如果在本包上打任何触碰 `src/Makefile.am` 或 `gsasl.ggo` 的
补丁，`make` 会尝试调用 worker 上并不存在的 `gengetopt`。本包因此**不改上游源码**，
只补 `build-aux` 下的两个辅助脚本。

### 使用方式
```bash
gsasl --version
gsasl --client-mechanisms                 # 支持哪些机制
gsasl --mkpasswd --mechanism SCRAM-SHA-256 --password secret \
      --salt AAECAwQFBgcICQoLDA0ODw== --iteration-count 4096
gsasl --client --mechanism PLAIN --connect imap.example.com
```

### 验证结果
- `ohc-run.py conan-verify libgsasl-tools 2.2.4`: 见 `2.2.4/notes.md`
- `test_package/test.sh`: 14 项断言（`--version`/`--help` 契约、无参数调用退出 0、
  机制清单、可复现的 SCRAM-SHA-256 / SCRAM-SHA-1 派生、未知选项与未知机制反例、
  ELF 依赖自检）