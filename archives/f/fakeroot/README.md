# fakeroot — 伪 root 环境

fakeroot 通过 LD_PRELOAD 拦截系统调用，在不具备真实 root 权限的情况下模拟 root 环境。主要用于软件打包构建流程中，让构建脚本认为自己在 root 权限下运行。

## 核心功能

- 拦截 `chmod`、`chown`、`mknod`、`stat`、`lstat` 等系统调用
- 伪造文件所有权和权限信息
- 创建伪 root 环境用于包构建
- faked 守护进程管理伪造状态（支持 SysV IPC 和 TCP 两种通信模式）

## 鸿蒙平台说明

### LD_PRELOAD 拦截状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 进程身份拦截（getuid/getgid） | ✅ 可用 | `fakeroot -- id` 输出 uid=0(root) |
| 文件 stat 拦截 | ⚠️ 受限 | stat/lstat 拦截不生效，显示真实文件信息 |
| chown 命令 | ❌ 缺失 | toybox 未提供 chown 命令 |
| faked IPC | ✅ TCP 模式 | SysV IPC 不可用，自动切换 TCP |

**结论**: fakeroot 的进程身份拦截在鸿蒙上正常工作，对检测 `id -u == 0` 的构建脚本有实用价值。文件权限/所有权伪造功能受平台限制（musl libc + HMDFS），此为平台限制而非编译 bug。

### 构建补丁

编译 fakeroot 需要以下 3 个补丁：

1. **0001-config.guess.patch** — 添加 HarmonyOS 系统识别
2. **0002-config.sub.patch** — 添加 ohos-linux triplet
3. **0003-configure.patch** — HMDFS umask 077 → 022 修复

### HMDFS umask 077 问题

HMDFS 分布式文件系统对 `umask 077` 创建的目录实施安全限制，不允许在其中写入文件。autotools 的 `configure`/`config.status` 使用 `umask 077 && mktemp -d` 创建临时目录会触发 Permission denied。

**修复方法**：
```bash
sed -i 's/umask 077 && mktemp -d/mktemp -d/g' configure
sed -i 's/umask 077 && mkdir/umask 022 && mkdir/g' configure
```

## 版本信息

- 版本: 1.37.2
- 构建系统: autotools
- 语言: C
- 许可证: GPL-3.0+

## 安装产物

- `bin/fakeroot` — 主脚本（shell 脚本）
- `bin/faked` — 守护进程二进制
- `lib/libfakeroot-0.so` — LD_PRELOAD 共享库
- `lib/libfakeroot.a` — 静态库
- `share/man/` — 多语言手册页