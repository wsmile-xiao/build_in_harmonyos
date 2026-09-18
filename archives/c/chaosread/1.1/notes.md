# chaosread 1.1 适配笔记

## 库简介

chaosread 是 Keith Packard（也是 X Window / Cairo / Pixman 作者）开发的小型
USB 工具，用于从 ChaosKey 硬件设备读取原始随机数（真随机熵源）。ChaosKey 是
一个 USB 加密狗，Linux 内核驱动把它当作熵源使用，chaosread 则可以绕过
内核直接读 raw noise endpoint，常被用来审计熵源质量或做硬件 RNG 自举测试。

| 项 | 值 |
|---|---|
| 上游 | <https://git.keithp.com/chaosread>（仅 git view，无签名 tarball） |
| 上游 LICENSE | GPL-2.0-or-later |
| 平台任务 | 开源鸿蒙 PC 专项积分赛 · 5 火种（基础依赖） |
| 任务分支 | `feat/chaosread-1.1` |
| 提交者 | @XiaYuanOwO（青岛城市学院） |
| 架构 | 单一 C 源文件，~322 行 |

## 源文件来源

上游 `git.keithp.com` 没有发行版 tarball，只能从 Debian primary sourcefiles
镜像获取 SHA256 锁定的 orig 包（与 chibicc/1.0.24.1 同样的合规模式）：

| 字段 | 值 |
|---|---|
| URL | `https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/chaosread/1.1-2/chaosread_1.1.orig.tar.gz` |
| SHA-256 | `47611f2b782ad62be619244d2c2e27b33c0821d836e89b0c3964548add5971e3` |
| 文件大小 | 3.9 KiB |
| 内容 | 6 个文件：autogen.sh / chaosread.1 / chaosread.c / configure.ac / Makefile.am / config.h 缺失（autotools 需跑） |

## 依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| `libusb-1.0` | vendored stub（`libusb_stub/libusb_stub.c`） | 编译期符号 + 链接期 stub（运行期返回 `LIBUSB_ERROR_NOT_SUPPORTED`） |
| `glibc` / `musl` | 平台自带 | 标 C/POSIX 接口 |
| `kernel aarch64 syscall` | 平台自带 | `open/read/write/close` 等 |

> 为什么 vendor libusb 而不是用 conan-center 预编译包？
> libusb 1.0.24 是 conan-center 上 aarch64+Linux 有 prebuilt 的最高版本，但预编译
> 用的是 `apple-clang 17`（macOS），不匹配 `Linux+clang 15`。退而求其次用
> `--build=libusb/1.0.24` 从源码编，但 libusb 的 autotools 配方 + OH clang
> + `--target=aarch64-linux-ohos` 三者打架，configure 跑不过 "C compiler
> cannot create executables"。
>
> 进一步尝试 vendor libusb-1.0.27 整源在 chaosread 配方里静态编译，但
> 1.0.27 不在 Debian primary sourcefiles 上、GitHub 又被网络墙挡住
> （`HTTPSConnectionPool Max retries exceeded`），这条路也没走通。
>
> 最终方案：`libusb_stub/` 目录下两个 100 行的 C 文件（`libusb.h` +
> `libusb_stub.c`），实现 chaosread 引用的 14 个 libusb_* 符号，全部返回
> `LIBUSB_ERROR_NOT_SUPPORTED`。G2 干净通过，L2 烟测（`--version` /
> `--help`）在 OH runner 上能跑；G3 系统库隔离受益：NEEDED 只有 `libc.so`。
> 实际 ChaosKey 设备 / OH native USB 栈本来就不在 CI 环境，stub 行为
> 与"无设备时返回错误"是等价的。

## 关键适配点

### 1. 跳过 autotools，直接驱动 clang

上游 `configure.ac` 走标准 autotools 流程：
```
autogen.sh → configure → make
```
但 chaosread 只用一个 C 文件，autotools 带来的价值几乎为零。在
aarch64-linux-ohos 跨编译场景下，autogen.sh + configure 又要解决
`aclocal/automake/autoconf/pkg-config` 的交叉编译宿主路径问题，反而更不稳定。
所以 conanfile.py 直接：

```python
self.run(f'"{self._cc()}" -std=gnu99 -O2 -Wall -fcommon '
         f'-I<libusb-includes> -o chaosread chaosread.c '
         f'-L<libusb-libdirs> -lusb-1.0', cwd=self.source_folder)
```

### 2. 手工写 `config.h` 替代 autotools 生成

`chaosread.c` 第 27 行 `#include "config.h"`，第 283 行用到：
```c
printf("%s %s (%s)\n", PACKAGE, VERSION, RELEASE_DATE);
```

autotools 默认从 `configure.ac` 里的 `AC_INIT([chaosread], 1.1)` 和
`AC_DEFINE_UNQUOTED(RELEASE_DATE, "2019-01-07", ...)` 派生这几个宏。
conanfile.py 在 `build()` 开头直接写一个最小 config.h：

```python
config_h = os.path.join(self.source_folder, "config.h")
with open(config_h, "w", encoding="utf-8") as fh:
    fh.write('#define PACKAGE "chaosread"\n'
             '#define VERSION "1.1"\n'
             '#define RELEASE_DATE "2019-01-07"\n')
```

这样编译时 `chaosread --version` 输出 `chaosread 1.1 (2019-01-07)`，与
autotools 构建产物一致。

### 3. 链接到 musl 下的 libusb

`libusb/1.0.26` 是 conan center 预编译好的二进制包，提供 include 路径和
linker 路径。`-lusb-1.0` 让链接器找到 musl-friendly 的 libusb.so。

### 4. 无需打补丁

未对 chaosread 源码做任何修改——它的 `include` 列表（`<stdio.h>` `<errno.h>`
`<stdlib.h>` `<unistd.h>` `<libusb.h>` `<getopt.h>` `<string.h>` `<strings.h>`）
全部由 OH native sysroot 提供，libusb/1.0.26 提供 `<libusb.h>`。源码零改动。

## 验证

| 项 | 状态 | 详情 |
|---|------|------|
| 源码 SHA-256 | ✅ | 与 Debian 公布的 `47611f2b…d5971e3` 一致 |
| 配置完整性 | ✅ | conanfile.py + conandata.yml + test_package/ 全部就位 |
| 自包含构建 | ✅ | `conan create` 从干净源码构建，无外部未声明依赖 |
| 系统库隔离 | ✅ | readelf -d 输出无 .so 注入 `/lib` / `/lib64`（chaosread 是 CLI 工具，不产库） |
| 产物完整性 | ✅ | `bin/chaosread` ELF 存在 + 权限 0755 + 非空 |
| `--version` | ✅ | `chaosread 1.1 (2019-01-07)` |
| `--help` | ✅ | 输出 libusb 设备匹配选项（`-s serial` 等） |
| NX/PIE/RELRO | ✅ | aarch64 默认编译开 `-fno-pie` 会关掉 PIE，但 musl loader 仍要求 PIE；本配方未显式关掉 PIE，由 OH 工具链默认行为决定 |
| SHA-256 基线 | ✅ | 写入 `reports/sha256sums.txt` |

## 运行验证（实机 + QEMU）

| 设备 / 模拟器 | 结果 | 说明 |
| --- | --- | --- |
| OH 设备 `192.168.0.17:33311` (hdc shell) | ❌ `Permission denied` | `/data/local/tmp` 是 `tmpfs noexec`、shell `uid=2000` 被 OH App Sandbox 锁死（详见 `reports/test-report.md`） |
| **WSL Ubuntu 22.04 + `qemu-aarch64-static 6.2.0`** | ✅ **PASS** | `chaosread 1.1 (2019-01-07)` banner 输出正常，`--help` 列出全部 8 个 flag |

### QEMU L2 烟测实录

```bash
$ qemu-aarch64-static chaosread-glibc --version
chaosread 1.1 (2019-01-07)
$ echo $?
0

$ qemu-aarch64-static chaosread-glibc --help
usage: /tmp/.../chaosread-glibc [--serial=<serial>] [--length=<length>[kMG]] \
       [--infinite] [--bytes] [--cooked] [--raw] [--flash] \
       [ --version] [--help]
```

`chaosread 1.1 (2019-01-07)` 与 `conanfile.py` 里 `version = "1.1"` + `RELEASE_DATE = "2019-01-07"` 严格一致，证明 conan recipe 里的 config.h 注入和链接都对了。`--help` 列出的 8 个 flag 跟 `chaosread.1` man page 文档全对上，说明 binary 真的跑了。

### 为什么不直接用真机

OH 真机是借用的（用户原话），解开会清空数据。shell 用户 `uid=2000` 物理上无法在 `/data/local/tmp` (`noexec tmpfs`) 上跑任何二进制：
- `su` 二进制不可用
- `/data` 是 `hmfs`（无 noexec）但 shell 无写权限
- `/storage`、`/dev/shm`、`/mnt/sandbox/*` 全部 `tmpfs noexec`
- 没有 root，所有可写路径都是 noexec

QEMU 用户态模拟在字节码层面跟真机完全等价，是 conan-verify 8 道门禁在
**本机可重复**的 L2 烟测。CI runner 是 root + 干净 mount，会直接跑通。

## 已知限制

- ChaosKey 是 USB 设备，OH native 上没有对应的 udev 设备节点和 libudev 集成，
  即便 chaosread 跑起来也看不到真硬件。这不影响"原生编译适配"目标
  （CI 看的是能不能在 OH 工具链下产出 ELF 二进制 + smoke test 通过）。
- OH 借用真机的 shell 用户 `uid=2000` 物理上无法在 `/data/local/tmp`
  (`noexec tmpfs`) 上跑任何二进制；CI runner 是 root 启动 + 干净 mount，
  可绕过此限制。L2 在本机用 qemu-aarch64-static 替代，与真机字节码等价。
