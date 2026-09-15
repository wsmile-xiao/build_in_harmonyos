# pinentry 1.3.3 — 鸿蒙 PC conan 制品

pinentry = **GnuPG 的 PIN / passphrase 输入对话框集合**。本配方构建两个前端：

- **pinentry-curses**（ curses 界面）
- **pinentry-tty**（纯终端）

（GUI / Qt 系列全部关闭。）

## 出包（鸿蒙 PC）

```bash
conan create archives/p/pinentry/1.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 源

```
https://gnupg.org/ftp/gcrypt/pinentry/pinentry-1.3.3.tar.bz2
sha256 c2970f16d6afb66ecddfca767d743936c86239bff936eed7fd7597a678414b63   (620687 字节)
```

## 依赖（版本**未抬升**）

| 依赖 | 版本 | 上游最低要求（实测 `configure.ac`）|
|------|------|-----------------------------------|
| **libgpg-error** | **1.55** | `NEED_GPG_ERROR_VERSION=1.16`（:239）|
| **libassuan** | **3.0.2** | `NEED_LIBASSUAN_VERSION=2.1.0`（:256）|
| **ncurses** | **6.6** | — |

> ⚠️ **不要按"同族统一抬升"推断** —— gpg-error 系各库的最低要求**差异极大**：
>
> | 库 | 要求 libgpg-error |
> |----|------------------|
> | gnupg 2.5.22 | **≥ 1.56**（需 1.61）|
> | libksba 1.8.1 | ≥ 1.28 |
> | **pinentry 1.3.3** | **≥ 1.16** |
>
> 必须**逐库**从 `configure.ac` 读取。

## OHOS 适配要点

| # | 措施 | 原因 |
|---|------|------|
| 1 | `config.guess` / `config.sub` 的 **HarmonyOS patch** | 1.3.3 上游**仍不含** ohos 支持（实测 `config.sub` 报 `Invalid configuration ... OS 'ohos' not recognized`）。**实测 1.3.2 的 2 个 patch 可干净套用到 1.3.3**（`patch --dry-run` 通过）→ 直接复用，无需重新生成 |
| 2 | **config 脚本 shebang 改为 bash** | 构建期会执行依赖包内的 `gpgrt-config` / `libassuan-config`，而 **OHOS 上 `/bin/sh` 不可用** → 需把 shebang 改为 `/data/service/hnp/bin/bash`，并设 `CONFIG_SHELL` / `SHELL`（否则脚本无法执行、configure 探测失败）|
| 3 | **显式导出 `GPGRT_CONFIG` / `LIBASSUAN_CONFIG`** | libgpg-error **1.56+ 只剩 `gpgrt-config`**；除加入 PATH 外，显式给出可让 configure 直接命中，避免 `AC_PATH_PROG` 搜索失败 |
| 4 | `LD_LIBRARY_PATH` 含依赖 lib | 构建期运行 config 脚本时可能需加载依赖 `.so` |
| 5 | `TMPDIR` 指向 build 目录 | 设备默认 TMPDIR 在 HMDFS 上写临时文件失败 |
| 6 | `configure` 内 `umask 077` → `022` | HMDFS 上临时文件权限问题。**R6 要求用 Conan API `replace_in_file`**，不手写文件 IO |

## 测试

### ⚠️ 上游**没有**可跑的自动化测试套件

pinentry 1.3.3 官方 tarball **不含 `tests/` 目录**。实测证据：

```bash
$ tar tf pinentry-1.3.3.tar.bz2 | grep -i test     # → 0 条
$ grep -nA4 '^SUBDIRS' Makefile.am                # :114 → 不含 tests
$ grep -rn '^TESTS =\|check_PROGRAMS' .           # → 无任何匹配
```

→ **`make check` 是 no-op**。

### 替代方案：驱动上游**真实对外接口**

gpg-agent 与 pinentry 之间的实际接口是 **Assuan 协议**（命令表见 `pinentry/pinentry.c`），
`test_package/run_upstream_tests.py` 直接驱动它：

| 类别 | 断言 | 依赖终端 |
|------|------|---------|
| A. 握手 + GETINFO | `GETINFO version`（== 1.3.3）、`GETINFO pid` | 否 |
| B. 协议错误处理 | 未知命令 → `ERR`、`GETINFO` 参数错误 → `ERR` | 否 |
| C. 交互命令 | `GETPIN` 返回所输入 PIN、`CONFIRM` 接受 `y`、`MESSAGE` 渲染 | **是** |

- 覆盖 **pinentry-tty** 与 **pinentry-curses** 两个前端，共 **16 项**断言
- 本地实测（`TERM=xterm` + 可读 terminfo）：**16/16 通过**
- 终端不可用时 C 类标为 **SKIP**（明确输出 `RESULT: passed=… failed=… skipped=…`），
  **绝不把"跑不了"当"通过"**（R34）
- 另有 `test_pinentry.c`（clang 现场编译）真实执行两个前端的 `--version` 并断言 `1.3.3`

### 两个易踩的测试时序陷阱（都会造成假失败）

1. curses 前端**必须等界面渲染完**再写入，且**用 `\r` 确认**（`\n` 在 curses 下不生效）
2. **不可**把 `BYE` 与 `GETPIN` 同批发出 —— 连接会在用户输入前关闭，GETPIN 永远返回空
   （实测：同批 → 失败，不同批 → 成功）

### 终端依赖说明

`pinentry-curses` **静态链接 ncurses**（`NEEDED` 里无 `libncurses`），必须能读到
**terminfo 数据库**才能初始化终端，否则报
`ncurses: cannot initialize terminal type`。OHOS/HMDFS 上 conan 制品内的 terminfo
文件 owner 为构建用户且 other 位被剥离（实测 `-rw-rw----`）—— 故"目录存在"**不等于**
"可读"，脚本会实测 `os.access(entry, R_OK)` 后再选定 `TERMINFO`。

## 产物

```
bin/pinentry-curses
bin/pinentry-tty
```
