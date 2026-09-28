# OHOS 上 AF_UNIX 路径名 socket 的可用落点是唯一的，而 agent 类被测程序把 socket 建在 TMPDIR 之下

## 现象

依赖「本地 IPC 服务 + 客户端」模式的上游测试套件，在 OHOS PC 上**整包在 setup 阶段即失败**，
且错误信息远离真正原因：

```
gpg-connect-agent: waiting for the agent to come up ... (8s)
...
gpg-connect-agent: can't connect to the gpg-agent: IPC connect call failed
gpg-connect-agent: error sending standard options: No agent running
FAIL: tests/openpgp/setup.scm
Setup failed.
```

`gpg-agent --daemon` 单独跑时的真实报错是：

```
error binding socket to '/…/S.gpg-agent': Operation not permitted
```

实测案例：gnupg 2.5.22（PR #9613）上游 `make check` 78 项中，openpgp 64 项 + cms 6 项
整体无法进入用例体。

## 根因

### 1) AF_UNIX **路径名** bind 存在挂载点级白名单

在 OHOS PC 上逐挂载点实测 `socket(AF_UNIX).bind()`：

| 路径 | bind() | errno | 备注 |
|------|--------|-------|------|
| `/tmp` | ❌ | `EROFS(30)` | 只读 erofs 挂载（`/dev/block/dm-0 /tmp erofs ro`），普通文件也写不了 |
| `$HOME`、`~/.cache`、conan 构建树 | ❌ | `EPERM(1)` | HMDFS 拒绝 |
| `/dev/shm` | ❌ | `EACCES(13)` | 普通文件可写，**bind 仍被拒** |
| `/data` | ❌ | `EACCES(13)` | 权限不足 |
| **`/data/storage/el1/base`**（同级 el2/el3/el4 的 `base` 同样可用） | ✅ | — | **实测唯一可用落点** |

抽象命名空间（`\0` 前缀，不落盘）在**所有**路径都可用——但被测程序通常不给该选项，
它们按 `$TMPDIR` / `getcwd()` 拼路径名。

### 2) 关键因果链：socket 落在 **TMPDIR** 之下

多数测试框架先用 `mkdtemp()` 在 `TMPDIR` 下建临时目录，再把「程序主目录」指向它。
gnupg 的做法（`tests/openpgp/setup.scm:44`）：

```scheme
(setenv "GNUPGHOME" (getcwd) #t)
```

而 `getcwd()` 就是刚 `mkdtemp` 出来的目录 → **`S.gpg-agent` 落在 `<TMPDIR>/<tmpdir>/` 之下**。

⇒ 因此 **TMPDIR 决定了 agent socket 的可 bind 性**，这不是可选优化，而是
「套件能否真正执行」的唯一开关。

### 3) 路径长度也是变量

`sockaddr_un.sun_path` 上限 108 字节。实测把 TMPDIR 从 71 字符缩到 24 字符后，
openpgp 通过数由 53 → 55（2 项 agent 超时消失）。因此除挂载点外应**尽量缩短 TMPDIR**。

## 修复方案

1. **先探挂载点**，选一个 bind 成功的作为 TMPDIR 基址：

```sh
python3 - <<'EOF'
import socket, os
for d in ("/tmp", os.path.expanduser("~"), os.path.expanduser("~/.cache"),
          "/dev/shm", "/data/storage/el1/base"):
    p = os.path.join(d, "probe.sock")
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.bind(p); s.close(); os.unlink(p)
        print("OK  ", d)
    except Exception as e:
        print("FAIL", d, type(e).__name__, e)
EOF
```

2. **用短名重定向 TMPDIR** 后重跑：

```sh
W=/data/storage/el1/base/t        # 刻意取短名，规避 108 字节 sun_path 上限
rm -rf "$W"; mkdir -p "$W"; chmod 700 "$W"
TMPDIR="$W" make check
```

3. 若被测程序**自带**抽象命名空间选项，优先用之（见 E461）。

**不要**为了 bind 成功去放宽系统目录权限——SELinux 域限制与目录权限无关，且违反最小权限。

## 实测效果（gnupg 2.5.22，PR #9613）

| 阶段 | 规范口径 |
|------|---------|
| 初始（TMPDIR 默认） | 2/4 = 50.0%（套件大面积在 setup 阶段中止） |
| TMPDIR → `/data/storage/el1/base` | 64/70 = 91.4% |
| TMPDIR 缩短 + gpgconf 硬链接回退补丁 | **70/70 = 100.0%** |

逐子套件终态（2026-09-26）：`gpgscm` 1/1、`openpgp` **64/64（0 skipped）**、`cms` 6/6、
`migrations` 3/3、`tpm2dtests` **4/4** —— **合计 78/78 = 100.0%，0 skipped**。
（`tpm2dtests` 此前记作「无软件 TPM、环境前置缺失」，后查明真因并补齐：缺 `tpm2-tss`/`swtpm`
前置 + 配方 `--disable-card-support` 使 `keytotpm` 不编译 + 驱动脚本 shebang 为 `/bin/bash`。）

## 与 E461 的差异

E461《OHOS filesystem matrix rejects AF_UNIX file-socket bind; use abstract namespace》
已确立**原则层**结论（HMDFS 拒 bind、/tmp 只读、建议抽象命名空间 + 回退 `$TMPDIR`）。

本条补的是 E461 **缺失的可操作落点与因果链**：

- E461 说「回退 `$TMPDIR`」，但**未给可用目录清单**——照其字面把 TMPDIR 设成
  `$HOME` 或 `~/.cache` 仍然 `EPERM`；
- E461 **未指出**被测程序把 socket 放在临时目录之下（`GNUPGHOME ← getcwd ← TMPDIR`），
  因此「改 TMPDIR」是唯一开关而非可选优化；
- 本条给出可量化效果（50.0% → 100%）与 sun_path 长度因素。

## 检测方法（预扫描）

测试框架/被测程序源码中出现以下任一即应预警本条：

- `setenv "GNUPGHOME" (getcwd)` / `GNUPGHOME` + `mkdtemp`
- `unix:tmpdir=` / `--socket-path=$TMPDIR` / `S.gpg-agent` / `dbus-` socket 名
- 直接 `bind()` 到 `$TMPDIR` 拼接的路径
