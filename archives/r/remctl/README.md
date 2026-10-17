# remctl（Kerberos/GSSAPI 认证远程命令执行）

## 简介

remctl 是一套"经 Kerberos/GSSAPI 认证、按 ACL 授权、在远端执行单条命令并回传 stdout/stderr/退出码"
的客户端库 + 服务端：`libremctl` 提供 `remctl_new / remctl_open / remctl_command / remctl_output /
remctl_result_free` 及一次性 `remctl()` 接口，`remctld` 是守护进程、`remctl-shell` 是
`ssh -c` 形态的免守护入口。上游由 Russ Allbery 维护，常见用途是批量运维中"只允许跑被授权的命令"。

## 软件信息

- 上游主页：https://www.eyrie.org/~eagle/software/remctl/
- 官方取包：https://archives.eyrie.org/software/kerberos/remctl-3.18.tar.gz（另有同名 `.asc` 签名件）
- 许可：MIT
- 语言/构建：C，autotools（tarball 自带预生成 `configure`，无需 autoreconf）
- 本仓交付：`libremctl.a` + 公开头 `remctl.h` + `libremctl.pc` + 可执行 `remctl`/`remctld`/`remctl-shell` + man 页

## 鸿蒙适配要点

1. **交叉三元组**：CI 的 `-pr:h` 与 `-pr:b` 同为 `ohos-aarch64` profile ⇒ conan 判"非交叉"、不注入
   `--build/--host`，而随包 `config.guess`(2022-01-09) 完全不含 OHOS 分支 ⇒ 配方显式传
   `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`，并用
   `patches/0001` 给随包 `config.sub`(2022-01-03) 回补 `ohos*` / `linux-ohos*` 两处白名单。
   框架的 `patch-autotools-ohos.pl` 在 CI worker 上不可达（`REPO_ROOT` 不 export），不作为依赖。
2. **E386（设备级 getcwd 挂）**：profile `[buildenv]` 把 `CONFIG_SHELL/SHELL` 指向 hnp bash，
   该二进制在 HMDFS 下 `getcwd()` 必挂 ⇒ 配方在 `generate()` 内把它们路由到 `/bin/sh`。
   ★关键顺序：必须先 `VirtualBuildEnv(self).generate()` 再 `save_script()`，否则配方的
   `define()` 会被链尾的 `conanbuildenv-*.sh` 静默覆盖（conan 不告警）。
3. **E114**：`configure` 里 2 处 `umask 077` 建的临时目录在 HMDFS 上 owner 自己不可写
   （`config.status ... can't create ./confXXXX/subs1.awk: Permission denied`）⇒ `build()` 内就地
   去掉 umask 前缀、保留真实目录创建。
4. **依赖建模**：`krb5/1.22.1`（1.22.2 在 remote 不存在）必需；`libevent/2.1.12` 只服务 server 侧
   （`client_libremctl_la_LIBADD` 不含 event、`client/*.c` 里 `event_` 命中 0）⇒
   `requires(..., visible=False)`，不传播给消费者。**`popt` 不是本包依赖**（全树 grep 零命中）。
   本包 configure 走 `krb5-config`/`AC_SEARCH_LIBS` 而非 pkg-config ⇒ 需把依赖 `package_folder`
   以 `--with-krb5/--with-gssapi/--with-libevent` 显式喂入。
5. **上游测试**：`make check` 经自研 C TAP 驱动 `tests/runtests -l tests/TESTS` 真实执行，
   在 `build()` 内跑通（912 条实跑全通过、63 条文件内带因 skip、29 集整集带因跳过、0 失败）。
   `make check` 的 53→0 个 `exit 127` 根因是**运行期取不到依赖 `.so`**（conan 只给链接期 `-L`），
   不是 OHOS 未签名 ELF 限制 ⇒ build 作用域 `prepend_path("LD_LIBRARY_PATH", ...)`。
6. **测试脚本可重定位**：6 个 perl 测试集 shebang 写死 `/usr/bin/perl`（本机 perl 只在
   `~/usr/local/bin`）⇒ `patches/0002` 改为 `/usr/bin/env perl`，之后它们转为上游自身的带因 skip。
7. **测试前置件**：`server/acl/localgroup` 需一份 `tests/config/krb5.conf`（其 16 条断言是纯 ACL
   逻辑，不需 KDC 与票据）⇒ `build()` 生成最小 `[libdefaults] default_realm`，属补上游要求的前置件。

## 可用版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 3.18 | built | 见 `3.18/manifest.yaml` 与 `3.18/notes.md` |

## 预编译依赖

- `krb5/1.22.1`（必需；GSSAPI/KRB5）
- `libevent/2.1.12`（非传播：仅本包 server 侧二进制需要）

## 补丁清单

| 补丁 | 类型 | 一句话 |
|---|---|---|
| `3.18/patches/0001-config-sub-ohos-triplet.patch` | portability | 给随包 config.sub 回补 OHOS 三元组白名单（2 处） |
| `3.18/patches/0002-ohos-relocatable-perl-shebang.patch` | portability | 6 个测试脚本 shebang 改 `/usr/bin/env perl` |

## 已知限制

- 不交付 perl/php/python/ruby 绑定（上游默认关闭）。
- 22 个测试集需活 KDC/keytab（本平台无）⇒ 由上游自身 `skip_all` 带因退出；另有 7 集是上游作者/
  自动化测试门。**均未按"通过"申报**。
- `remctld`/`remctl-shell` 随包交付但未做端到端服务验证（需 KDC 前置）。
- 包显式写死交叉三元组（与 SKILL §4.1"优先由 config.guess 探测"有偏差），原因见上第 1 条；
  基线若带上含 OHOS 分支的 config.guess，应改为只打补丁。

## 用法

```c
#include <remctl.h>

const char *cmd[] = { "test", "version", NULL };
struct remctl_result *r = remctl("kdc.example.org", 0, NULL, cmd);   /* port 0 ⇒ REMCTL_PORT(4373) 回落 4444 */
if (r == NULL) { /* OOM */ }
if (r->error != NULL) { fprintf(stderr, "remctl: %s\n", r->error); }
else { printf("out=%.*s status=%d\n", (int) r->stdout_len, r->stdout_buf, r->status); }
remctl_result_free(r);
```

链接：`pkg-config --libs libremctl`（交付 `libremctl.pc`，其 `Libs.private` 含 GSSAPI/KRB5 依赖）。
一次性 `remctl()` 是 4 参（`host, port, principal, const char **command`），`principal` 可为 `NULL`。
