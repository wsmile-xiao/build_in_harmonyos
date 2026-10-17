# ephemeralpg 3.4 adaptation notes

- Upstream: `https://github.com/eradman/ephemeralpg`, source archive
  `https://eradman.com/ephemeralpg/code/ephemeralpg-3.4.tar.gz`.
- Source archive SHA256:
  `2300082455bf6a10d71a020d8b837d986dd72b0ef82572baf922f118c67cb52d`.

## Source structure

Minimal Makefile package. Build artifacts (two):
1. **getsocket** — compiled from `getsocket.c` (single C source). Uses standard
   POSIX socket API (`socket`/`bind`/`getsockname`/`close`) to fetch an unused
   TCP port and print it to stdout. No platform-specific code.
2. **pg_tmp** — generated from `pg_tmp.sh` via `sed -e 's/${release}/3.4/'`.
   A POSIX `/bin/sh` shell script that wraps `initdb`/`pg_ctl` to spin up a
   temporary PostgreSQL cluster. PostgreSQL is a **runtime** dependency, not a
   build/link dependency.

Makefile key targets:
- `pg_tmp: pg_tmp.sh` → sed version substitution, `chmod +x`.
- `getsocket: getsocket.c` → `${CC} ${CFLAGS} ${CPPFLAGS} ${LDFLAGS} getsocket.c -o getsocket`.
- `install` → installs `getsocket`, `pg_tmp` into `${PREFIX}/bin/` and man
  pages into `${MANPREFIX}/man1/`.

## Build flow

- Conan dependencies: none (`requirements()` is `pass`). PostgreSQL is runtime
  only — `pg_tmp` shells out to `initdb`/`pg_ctl` at runtime.
- `export_sources()` is provided for Conan patch handling (none needed here).
- `layout()` uses `basic_layout` with `self.folders.build = "."`.
- `source()` downloads the tar.gz via `get(..., strip_root=True)`.
- `build()`:
  - Asserts `os in ("Linux", "OHOS")` (R32).
  - `apply_conandata_patches(self)` (no patches declared).
  - Reads `CC` from `tools.build:compiler_executables` conf dict (R33: never
    bare `${CC}` shell var).
  - Runs `make -j1 CC=<cc> STRIP=true PREFIX=/usr MANPREFIX=/usr/share/man`.
- `package()`:
  - Runs `make install PREFIX= MANPREFIX=share/man STRIP=true DESTDIR=<pkg>`.
  - Empty `PREFIX` installs directly under the Conan package root (`bin/`).
- `package_info()`: `self.cpp_info.bindirs = ["bin"]` (two executables, no libs).

## OHOS adaptation key points

- **STRIP=true** passed to both `make` and `make install`: upstream `make
  install` strips the installed binary by default; the OHOS MAC kernel rejects
  stripped binaries (`Operation not permitted`). Keeping binaries unstripped
  matches the abduco 0.6 adaptation pattern.
- **getsocket.c** uses only POSIX socket APIs (`sys/socket.h`,
  `arpa/inet.h`, `netinet/in.h`, `netdb.h`) — fully OHOS-compatible, no patch
  required.
- **pg_tmp.sh** is a POSIX `/bin/sh` script. On OHOS it runs under
  `/data/service/hnp/bin/bash` (the `trap ... exec bash $0` fallback handles
  non-POSIX shells). No source modification needed.
- **/tmp handling**: `pg_tmp.sh` uses `${SYSTMP:-/tmp}` for its temp directory
  (E002: `/tmp` may be read-only on OHOS). The recipe does **not** hard-code
  `/tmp`; the runtime user may override `SYSTMP` if needed. No source patch
  required for the build/install phase.
- **make -j1** (R9): single-file C compile + sed substitution, no parallelism
  benefit, but -j1 is the safe default.

## Testing

### Conan test_package (L1 smoke test)

- The Conan `test_package` runs `getsocket` (the C binary) and asserts it
  prints a valid TCP port (1..65535, exit 0). It also verifies `pg_tmp` is
  installed and present. This is a real functional invocation of the packaged
  binary (R34), not a string-only stub.
- Result: **PASS** (getsocket returned port 43683, pg_tmp installed).

### 上游测试用例 (upstream test suite)

上游包含两个 Ruby 测试文件，使用 `stubs/` 目录模拟 PostgreSQL 命令（不依赖真实
postgres）。环境：ruby 3.4.5 (aarch64-linux-ohos)。

上游测试用例总数：**15**（test_getsocket.rb 2 + test_pg_tmp.rb 13）。

#### test_getsocket.rb — ✅ 全部通过 (2/2)

```
---
0.024: Fetch a random, unused port
0.045: Ensure a new port is picked each time
2 tests PASSED
```

验证 `getsocket` 二进制功能：获取随机空闲 TCP 端口，且每次调用返回不同端口。
此测试直接运行编译产物，不依赖 stubs 或 PostgreSQL，与 OHOS 平台完全兼容。

#### test_pg_tmp.rb — ⚠️ 4/13 通过，第 5 个用例失败，后续 8 个未运行（阻塞）

test_pg_tmp.rb 共注册 **13** 个 `try` 用例（上游实际数量，已逐行核实源码）：

```
---
0.030: Catch unknown options                                       PASS
0.033: Bogus arguments mixed with valid positional                 PASS
0.057: Run with missing Postgres binaries                          PASS
0.203: Create a new database on disk                               PASS
       Start a new instance with a specified datadir...            FAIL
       Start a new instance on a TCP port using a specified datadir (未运行)
       Start a new instance without a pre-initialized datadir      (未运行)
       Start a new instance and leave server running               (未运行)
       Start a new instance and keep the tmp datadir               (未运行)
       Stop a running instance                                     (未运行)
       Stop a running instance and remove tmp datadir              (未运行)
       Stop a running instance if query fails                      (未运行)
       Stop a running instance and keep tmp datadir                (未运行)
```

测试框架 `try`/`eq` 中 `eq` 断言失败即 `raise RuntimeError` 中止脚本，无 `rescue`
恢复机制，因此第 5 个用例失败后第 6–13 个（共 8 个）均未执行，计入阻塞。

**失败根因（非源码缺陷）**：`pg_tmp.sh` 第 42 行用 `test -O` 检查临时目录所有权，
在 OHOS HMDFS 文件系统上 `test -O` 永远返回 false（文件系统 UID 20001006 与进程
实际 UID 20020082 不匹配，`whoami` 报 "cannot find name for user ID 20020082"）。
导致 `start` 分支无法复用已有 datadir，转而调用 `initdb` 创建新目录，而 stub 的
`initdb` 用 `mkdir $2`（无 `-p`）遇到已存在的 16.3 子目录报 `File exists`。

**平台限制链**：
1. E002: `/tmp` 只读 (erofs ro) → 测试脚本硬编码 `mktemp -d /tmp/...` 失败，
   需 patch 为 `mktemp -d ${TMPDIR:-/tmp}` (本环境 TMPDIR=/storage/Users/currentUser/tmp)
2. HMDFS `test -O` 所有权检查失败 → `pg_tmp start` 无法复用 datadir
3. 同类问题见 PostgreSQL 18.3 适配 (notes.md: hmdfs 权限放宽)

**结论**：`test_pg_tmp.rb` 失败是 OHOS 平台限制（只读 /tmp + HMDFS 所有权检查），
非 ephemeralpg 源码缺陷。`pg_tmp.sh` 逻辑正确，在标准 Linux/BSD 上预期全通过。
Conan test_package 的 getsocket 烟雾测试已验证编译产物功能正常。

### 测试环境补丁说明

运行 `test_pg_tmp.rb` 需以下环境适配（不修改源码，仅测试脚本环境）：
1. 将 `mktemp -d /tmp/...` 改为 `mktemp -d ${TMPDIR:-/tmp}/...`（E002 /tmp 只读）
2. 将测试期望字符串中的 `%2Ftmp%2F` URL 编码同步替换为实际 TMPDIR 的编码
3. 上述补丁仅影响测试期望字符串匹配，不改变 pg_tmp.sh 源码行为

---

**编译结束**: 2026-08-20 10:15
**上游测试**: 2026-08-20 10:25
**最终状态**: built
