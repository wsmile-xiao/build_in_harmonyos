# DRAFT-buildah-hongmeng-syscall-probe-sigsys

## HongMeng 内核对未实现 syscall 号返回 SIGSYS：Go syscall 探测在启动时崩溃

### 现象

Go 编写的容器生态工具（buildah/podman/skopeo 等）在 HarmonyOS PC 上一启动就被杀死：

```
$ buildah --version
SIGSYS: bad system call
PC=0x15b80 m=0 sigcode=1
goroutine 1 [syscall]:
syscall.Syscall(0x1ac, ...)          # 0x1ac = 428 = open_tree(2)
golang.org/x/sys/unix.OpenTree(...)
github.com/cyphar/filepath-securejoin/pathrs-lite/internal/linux.init.func1()
...
github.com/opencontainers/selinux/go-selinux.CurrentLabel(...)
go.podman.io/common/pkg/config.defaultConfig()
main.mainInit()
```

### 根因

- HongMeng 内核对未注册的 syscall 号（open_tree(2)=428、openat2(2)=437 等）**直接投递 SIGSYS 杀死进程**，而不是像 Linux 那样返回 `-ENOSYS`
- filepath-securejoin/pathrs-lite 的 `HasNewMountAPI` / `HasOpenat2` 通过**真调 syscall** 来探测可用性，预期"失败返回错误码再走 fallback"，在 HongMeng 上探测本身即死
- Go runtime 的同步 SIGSYS 无法用 `signal.Notify` 安全捕获恢复（会死循环或崩溃）
- 调用链：mainInit → config.Default() → go-selinux.GetEnabled() → readConThreadSelf → procfs.OpenProcRoot() → unix.OpenTree() → SIGSYS

### 推荐方案

在 vendor 探测处加**运行时 uname 检测**（release 含 "HongMeng"），命中则直接返回 false 走上游自带的 legacy 路径（pre-5.2 内核标准支持路径）：

- `HasNewMountAPI=false` → `unsafeHostProcRoot()`（普通 open /proc）
- `HasOpenat2=false` → openat 逐段解析 fallback

这是运行时能力检测而非编译期 `__OHOS__` 宏（R8 合规），普通 Linux 行为完全不变。

参考实现：`archives/b/buildah/1.44.0/patches/0003-pathrs-lite-hongmeng-syscall-probes.patch`

### 验证

```
修复前: buildah --version → SIGSYS: bad system call (exit 2)
修复后: buildah --version → buildah version 1.44.0 (image-spec 1.1.1, runtime-spec 1.3.0), exit 0
```

### 关联

- 同家族受限能力：rootless 容器存储需要 user namespace（fork+CLONE_NEWUSER → EAGAIN，HongMeng 内核策略禁止）——独立的平台能力边界问题，见 buildah notes.md
