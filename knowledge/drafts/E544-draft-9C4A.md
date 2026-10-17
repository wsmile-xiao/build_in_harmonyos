# E544 — OHOS 拒绝 AF_UNIX 路径名 socket：以确定性哈希抽象名透明回退改造 sockfile 会合点

## 现象（设备实测，真实报错）

sexpect 2.4.0 在 HarmonyOS PC 上原样构建后跑上游 CTest：

```
[ERROR] bind: Operation not permitted (1)
!! ASSERT: sexpect sp -t 10 -ttl 20 bash --norc
12% tests passed, 22 tests failed out of 25
```

仅不依赖 sockfile 的 `glob2re`、`version` 与无 tty 空跑的 `interact-re-helper` 通过。
同一二进制在 Linux 上全部通过——问题只在「客户端/服务端会合点是一个文件系统路径」。

能力矩阵探针（python，逐一 bind；设备 HarmonyOS / HongMeng Kernel 1.12）：

| 目标 | bind() 结果 |
|------|-------------|
| `$HOME/...`（HMDFS 全域） | `EPERM` Operation not permitted |
| `/tmp/x.sock` | `EROFS` Read-only file system |
| `/dev/shm/x.sock` | `EACCES` Permission denied |
| `/data/local/tmp/x.sock` | `EACCES` Permission denied |
| `\0sexpect-...`（抽象命名空间） | **成功（bind + connect + 收发数据均可用）** |

## 触发条件

- 平台：HarmonyOS PC（普通用户态进程，非应用沙箱内进程）
- 形态：工具/库的内部 IPC 以「文件系统路径」为会合点（此处：`SEXPECT_SOCKFILE` → server `bind()` / client `connect()`）
- 时机：第一次 `spawn`（server 绑定 sockfile）即失败，所有后续子命令全部不可用

## 根因分析

OHOS 对非应用进程关闭了 AF_UNIX 路径名 socket 的创建能力（hmmac/SELinux 策略：HMDFS 上 `EPERM`，
`/tmp` 本身只读，`/dev/shm` 与用户可写系统目录返回 `EACCES`），只余 **抽象命名空间**
（`sun_path[0]='\0'`，不占文件系统节点）可用。

与已有条目/草稿的差异（查重结论）：

- `E024`（AF_UNIX 受限，建议改 TCP）与 `E461`（dbus 测试，建议测试侧 abstract-first）都停留在
  「换传输/换测试配置」层面，未解决**工具自身接口不允许改会合点**的问题；
- `DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket` 给出的是**库协议级约定**
  （名称以 `@` 开头走抽象命名空间，配置/测试配合改写）；
- 本条是**对既有工具的透明回退**：用户接口（sockfile 路径）完全不变，工具内部在
  bind/connect 封装层回退，且抽象名由路径**确定性推导**，因此 server 与 client
  无需任何协议/配置改动即可重新会合。适用于「会合点路径对使用者可见、不可改名」的存量工具。

## 解决方案（推荐方案）

三处最小改动（sexpect 实测补丁 `0001`–`0003`，无平台宏、Linux 行为不变）：

1. **确定性抽象名**：`FNV-1a 64` 哈希 sockfile 路径 → `"sexpect-<16hex>"`，写入
   `sun_path+1`，长度 = `offsetof(sun_path) + 1 + strlen(name)`。server/client 同源推导，
   与路径长度（`sun_path` 108 字节上限）无关。
2. **bind 回退**：路径 `bind()` 失败且 `errno ∈ {EPERM, EACCES, EROFS}` 时改 bind 抽象名；
   其余 errno（如 `EADDRINUSE`）照旧 fatal —— 回退集合刻意收窄，避免掩盖真实错误。
3. **connect 回退**：client 先试路径 socket，失败再试抽象名。server 侧抽象模式跳过
   `realpath()`（无文件可 canonicalize）、清理阶段 `unlink()` 保持无害调用。

验证：同一设备、同一源码树，`ctest --output-on-failure -j1` → **25/25 PASS**
（含 pts EIO、僵尸回收、TTL、128KiB 分块发送等全部上游用例）。

## 禁止做法

- ❌ 把「AF_UNIX 不可用」直接当上游设计跳过测试（本库实测可从 22/25 失败修到 25/25）。
- ❌ 用放宽权限/写系统目录「造」出路径 socket（OHOS 无可写且允许 bind 的目录）。
- ❌ 把抽象名写死为常量（多实例会互相顶掉）；必须由 sockfile 路径确定性推导。

## 适用范围与边界

- 适用：任何以「路径」为 AF_UNIX 会合点的存量 CLI/守护进程（expect 类工具、自定义 IPC），
  且会合点字符串对 server/client 两端相同（本库测试均用绝对路径）。
- 边界：抽象命名空间 socket 无文件系统节点——依赖「sockfile 文件存在性」的外部脚本需改用
  工具自身的判活命令（如 `sexpect get`）；`/proc/net/unix` 可见性等按平台而定。
- 关联：`E024`、`E461`、`DRAFT-libdsme-0.67.0-ohos-abstract-af-unix-socket`（协议级 `@` 约定）、
  `DRAFT-pty-driven-interactive-test-traps`（PTY 使用侧方法论，本条是工具本体移植）。
