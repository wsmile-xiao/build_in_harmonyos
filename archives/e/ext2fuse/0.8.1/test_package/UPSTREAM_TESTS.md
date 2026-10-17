# ext2fuse 0.8.1 上游测试台账

## 测试来源

- 源码归档：`ext2fuse-src-0.8.1.tar.gz`
- SHA256：`431035797b2783216ec74b6aad5c721b4bffb75d2174967266ee49f0a3466cd9`
- 测试套件：`tests/pjd-fstest-20080412`
- 上游入口：该目录的 `README` 要求先执行 `make` 编译 `fstest`，再进入真实
  文件系统挂载点，以 root 身份执行 `prove -r /path/to/fstest/`。
- 顶层入口：ext2fuse 顶层 `make check` 没有注册这组 vendored 测试，因此不能
  用“`make check` 返回绿色”代替对该目录的盘点和执行。

## 完整盘点

本轮从同一份源码归档解包后，对 `tests/pjd-fstest-20080412/tests/` 递归统计
所有数字命名的 `.t` 文件，共 **184 个测试文件**：

| 类别 | 发现 | 执行 | 通过 | 失败 | 阻塞 |
|---|---:|---:|---:|---:|---:|
| `chflags` | 14 | 14 | 14 | 0 | 0 |
| `chmod` | 12 | 12 | 7 | 5 | 0 |
| `chown` | 11 | 11 | 5 | 6 | 0 |
| `link` | 18 | 18 | 9 | 9 | 0 |
| `mkdir` | 13 | 13 | 8 | 5 | 0 |
| `mkfifo` | 13 | 13 | 8 | 5 | 0 |
| `open` | 24 | 24 | 15 | 9 | 0 |
| `rename` | 21 | 21 | 11 | 10 | 0 |
| `rmdir` | 16 | 16 | 9 | 7 | 0 |
| `symlink` | 13 | 13 | 6 | 7 | 0 |
| `truncate` | 15 | 15 | 11 | 4 | 0 |
| `unlink` | 14 | 14 | 8 | 6 | 0 |
| **合计** | **184** | **184** | **111** | **73** | **0** |

这里的“184”是 `.t` 文件数，不是每个文件内的 TAP assertion 数。执行环境为
新真机普通 HMDFS 隔离目录，因设备没有 `prove`/Perl 而逐个用 `/bin/sh`
启动脚本；真实 ext2/FUSE 挂载闭环仍单独按设备能力阻塞记录。消费者
`test_package` 的 4 个断言仍单独按安装、版本、帮助和缺参路径统计。

## 真实执行记录

### 0. 本机补齐工具并复跑（2026-09-12）

为避免因为缺少宿主机工具就直接跳过，先在 Windows 本机尝试补齐上游
TAP 运行环境：

```text
winget install --id StrawberryPerl.StrawberryPerl --source winget --silent
```

结果：安装器下载阶段因网络错误 `0x80072efd` 失败，Strawberry Perl 未安装。
随后复用 Git for Windows 自带的 Perl（版本 `5.42.2`），并将 CPAN
`Test-Harness 3.52` 解包到本机临时目录
`C:\Users\ASUS\Documents\Codex\ext2fuse-local-test\Test-Harness-3.52`。
`App::Prove`、`TAP::Harness` 和 `TAP::Harness::Env` 均可加载，未修改仓库
文件，也没有把宿主机工具结果冒充设备结果。

本机还完成了上游源码校验和 OHOS 目标辅助程序交叉编译：

```text
源码包 SHA256：
431035797B2783216EC74B6AAD5C721B4BFFB75D2174967266EE49F0A3466CD9

OHOS Clang：
aarch64-unknown-linux-ohos-clang -Wall fstest.c -o fstest-ohos-aarch64
```

交叉编译返回 `0`，生成 28,384 字节 ELF64 AArch64 文件；`llvm-readelf -h`
确认 `Machine: AArch64`。由于当前 Windows 主机没有 OHOS ELF 执行环境，
该文件只作为“目标辅助程序可编译”证据，不能在 Windows 上直接运行。

### 0.1 本机 TAP 入口和代表性用例

使用下载的 `Test-Harness 3.52` 执行递归 dry-run，命令返回码为 `0`。该结果
只证明官方 `prove` 入口已能启动和解析测试目录，不代表任何测试通过。

随后在 Git Bash 中实际执行两个代表性测试文件，保留了失败结果：

| 用例 | 实际结果 | 失败原因 |
|---|---:|---|
| `tests/mkdir/00.t` | 36 个断言，5 通过，31 失败，文件返回 `1` | 测试脚本引用的 `../../fstest` 不存在；OHOS AArch64 ELF 不能在 Windows 主机执行 |
| `tests/open/00.t` | 47 个断言，9 通过，38 失败，文件返回 `1` | 同上；失败输出明确为 `No such file or directory` |

最后使用同一运行器尝试完整套件，设置 120 秒限时：

```text
prove -r tests/pjd-fstest-20080412/tests
```

结果：120 秒后由 `timeout` 返回 `124`。在超时前已经启动 41 个测试文件，
`chmod`、`chown`、`link` 等文件中持续出现 `../../fstest: No such file or
directory`；日志还显示部分只使用 shell 的断言能够通过。该宿主机结果不计入
OHOS 目标套件的通过/失败统计，因为它没有运行在 OHOS 文件系统和 FUSE 挂载
环境中。

本机 DevEco SDK 的 `hdc list targets` 返回空设备列表；QEMU AArch64 未安装。
因此当前本机没有第二条能够执行 OHOS ELF 的运行通道。已检查 Windows 原生
LLVM 作为替代方案，但直接编译上游 `fstest.c` 因缺少 POSIX 头文件
`sys/param.h` 失败；这也是继续使用 OHOS sysroot 交叉编译、而不伪造 Windows
helper 的原因。

### 1. 真机源码解包

在 HarmonyOS 真机上执行：

```sh
tar -xzf ext2fuse-src-0.8.1.tar.gz
find tests/pjd-fstest-20080412/tests -type f -name '*.t' | wc -l
```

结果：解包返回 `0`，设备端重新统计为 `184`。

### 2. 上游官方 `make`

在 `tests/pjd-fstest-20080412` 执行上游原始命令：

```sh
make
```

结果：返回码 `2`。上游 `Makefile` 硬编码执行：

```text
gcc -Wall fstest.c -o fstest
make: gcc: Permission denied
make: *** [Makefile:12: fstest] Error 127
```

这不是把测试静默跳过，而是保留了官方命令的真实失败。失败点是设备当前
shell/测试域无法使用该 Makefile 指定的 `gcc`。

### 3. 上游测试工具的可行替代编译

根据适配中已经验证过的 OHOS 工具链约束，使用可写临时目录调用设备上的
HarmonyOS Clang wrapper：

```sh
mkdir -p /data/storage/el2/base/cache/ext2fuse-upstream-20260912/tmp
TMPDIR=/data/storage/el2/base/cache/ext2fuse-upstream-20260912/tmp \
  sh /storage/Users/currentUser/usr/local/bin/cc \
  -Wall fstest.c -o fstest
```

结果：返回码 `0`，`fstest` 生成成功。直接运行 `fstest` 能输出官方 usage，
实际无参数返回码为 `1`；对当前设备目录执行 `stat`、`create`、`stat`、
`unlink` 的辅助程序 smoke 返回码均为 `0`。这说明测试辅助程序已经能够在
目标架构上启动并完成基本 syscall 调用。该结果只计入“测试工具编译/
启动前置通过”，不计入 184 个 `.t` 用例通过。

### 4. `prove`/Perl 运行器

上游 README 要求 `prove -r`。真机检查：

```sh
command -v prove
command -v perl
```

结果：两者均未找到。因此无法在设备端启动官方 TAP 递归运行器。没有使用
自写循环、空目录或宿主机 Perl 冒充真实上游执行。

### 5. ext2 测试镜像和挂载

为排除“没有测试盘”这一可修复原因，真机已创建一次性 32 MiB ext2 镜像：

```sh
dd if=/dev/zero of=ext2.img bs=1M count=32
mke2fs -t ext2 -F ext2.img
mount -t ext2 -o loop ext2.img mnt
```

结果：

- `dd`：通过，返回码 `0`；
- `mke2fs`：通过，返回码 `0`；
- `mount`：返回码 `1`，设备 mount 工具报告 `mount: bad /etc/fstab: No such file or directory`；
- `mount -o loop` 和自动 loop 变体均得到同样结果。

因此本轮不是因为没有 ext2 镜像而少报测试，而是镜像已经准备好，当前设备
mount 能力仍不可用。

### 6. FUSE 设备能力

执行：

```sh
ls -l /dev/fuse
test -r /dev/fuse
test -w /dev/fuse
```

结果：

```text
ls: /dev/fuse: Permission denied
```

读检查和写检查返回码均为 `1`。这直接阻塞 ext2fuse 的真实 FUSE 会话启动；
不能用普通 HMFS 目录、mock mount 或 `echo PASS` 替代。

### 7. 新真机逐文件 shell 直跑（2026-09-13）

为回应“不能因为缺少 `prove` 就直接跳过”的审查意见，在新设备
`10.62.178.77:2222` 上继续尝试了另一条可执行路径。该设备具备设备侧
`make`、OHOS `cc`、Python 和 `mke2fs`，但没有 `perl`/`prove`，也没有
可用的包管理器安装入口。因此将 184 个数字命名的 `.t` 文件逐个放入独立的
普通 HMDFS 目录，用上游脚本自己的 shell 入口启动：

```sh
for test_file in $(find tests/pjd-fstest-20080412/tests -type f -name '*.t'); do
    mkdir -p <isolated-directory>
    cd <isolated-directory>
    /bin/sh "$test_file" > tap.txt 2>&1
done
```

真实结果：

```text
发现脚本：184
逐个启动：184
shell 返回码 0：184
TAP ok 断言：1115
TAP not ok 断言：833
```

这里的 `shell 返回码 0` 只表示脚本进程完成；上游脚本把断言状态写到
TAP 文本，部分脚本即使包含 `not ok` 也不以非零 shell 状态结束。更重要的是，
这些脚本运行在普通 HMDFS 目录，而不是 `mount -t ext2` 后的真实 ext2 挂载点，
也没有通过官方 `prove` runner。因此这次直跑按“上游脚本实际启动”计入
文件级执行结果：111 个文件没有 `not ok`，73 个文件出现 `not ok`。同时，
**1115/833 不能作为 ext2/FUSE 挂载闭环的通过证据**，也不能替换正式
`prove -r` 结果。

## 最终结论

本轮对上游测试的真实统计为：

```text
发现：184
执行：184
通过：111
失败：73
阻塞：0
```

同时已完成且单独记录：

```text
上游 fstest.c 解包：通过
官方 make：失败（Makefile 硬编码 gcc，设备返回 Permission denied）
OHOS Clang fallback 编译 fstest：通过
fstest 启动 smoke：通过（无参数 rc=1，符合 usage 错误路径）
fstest 基本 syscall smoke：通过（stat/create/stat/unlink 均 rc=0）
32 MiB ext2 镜像创建：通过
prove/perl：正式 runner 阻塞（设备未安装）
ext2 mount：真实挂载闭环阻塞（mount 返回 bad /etc/fstab）
/dev/fuse：真实挂载闭环阻塞（Permission denied）
```

只有在设备管理员提供可执行的 `prove`/Perl、可挂载的 ext2 测试点以及当前
测试域对 `/dev/fuse` 的访问权限后，才可以把普通 HMDFS 直跑结果替换成
真实 ext2/FUSE 挂载点下的官方 runner 数字。恢复后应执行：

```sh
cd <ext2-mount-root>
prove -r <path-to>/tests/pjd-fstest-20080412
```

并把 TAP 原始结果、通过数、失败数和阻塞数一并更新到本文件及
`MANIFEST.yml`。
