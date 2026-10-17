# sxid 4.20130802 — HarmonyOS PC 适配说明

## 概况

`sxid` 审计系统里的 setuid/setgid 文件与目录：按配置的 `SEARCH` 路径递归扫描，
记录属主/属组/模式，目录按 inode、普通文件按 SHA-256 跟踪，并与上次检查的
日志（`LOG_FILE`）对比，报告新增（`+`）/移除（`-`）/属性或校验和变化（`m`/`i`）。
默认由 root 的 cron 每日运行，通过邮件发送报告。

- 上游：https://github.com/taem/sxid （原始作者 Ben Collins，后由 Timur Birsh 维护）
- 形态：6 个 C 源文件的 CLI 工具（`bin/sxid`）
- 依赖：无（仅 C 标准库；`getopt_long_only` 由 OHOS bionic 提供）
- 许可证：GPL-2.0-or-later
- 源码：Debian orig tarball `sxid_4.20130802.orig.tar.gz`
  sha256 `935d665dc508bc537bc4d0fca352a66610dc8e945d9aeee246b0546a86100124`

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游是 autotools 工程（autoconf 2.69，自带 `configure`/`Makefile.in`），但只有 6 个 C 文件、零依赖 | 直接用 OHOS clang 编译 `src/{conffile,logging,notify,search,sha2,sxid}.c`，绕开 autoreconf/automake/`config.guess`/`config.sub` 整条链路 |
| 2 | `src/sxid.h` `#include "config.h"`，而 `config.h` 由 `configure` 生成 | `build()` 在 `src/` 写入最小 `config.h`：`VERSION`、`CONF_FILE`、`MAIL_PROG`、`CL_SUBJ`、`HAVE_STRTOK_R`（正是 configure 会定义的 5 个宏） |
| 3 | `getopt_long_only` 是否存在决定是否要编译随包的 GNU `getopt.c`/`getopt1.c` | OHOS bionic 已提供 `getopt_long_only`（实测 `AC_CHECK_FUNC` 等价探测 rc=0），故不编译随包 getopt；`-std=gnu99` 下 `#include <getopt.h>` 走系统头 |
| 4 | 上游无测试套件 | 上游 `Makefile.am` 只有 `bin_PROGRAMS`/man/doc，无 `make check`、无 `tests/`、无脚本 → N=0，按口径由消费者测试补全（12 条断言） |
| 5 | 命令行工具产物含 `bin/` | 软件级 `commands.json`（L0k）；装 `bin/sxid` + `man1/sxid.1` + `share/sxid/{sxid.conf,sxid.cron}` |
| 6 | 无 root / 无 cron / 无 `/etc/sxid.conf` | 真机 `/etc` 只读指向 `/system/etc`，无 `crontab`、无 `/etc/cron*`；审计需以 `-c <conf>` 指定可写配置、`-n` 输出到 stdout，不依赖邮件/定时任务 |

## OHOS/HMDFS 上 setuid/setgid 语义与 Linux 相反（实测）

这是本库适配中最关键的平台差异，直接决定 sxid 在 OHOS 上的行为边界。
用 C 程序直接调用 `chmod(2)`/`fchmod(2)` 后 `lstat(2)` 实测（真机 aarch64，HMDFS 家目录）：

```
sizes: mode_t=4 ino_t=8 uid_t=4 gid_t=4
initial                mode=0640  ISUID=0 ISGID=0 IFREG=1 IFDIR=0
chmod(04755)           mode=0750  ISUID=0 ISGID=0 IFREG=1 IFDIR=0
chmod(06755)           mode=0750  ISUID=0 ISGID=0 IFREG=1 IFDIR=0
chmod(06777)           mode=0750  ISUID=0 ISGID=0 IFREG=1 IFDIR=0
fchmod(04755)          mode=0750  ISUID=0 ISGID=0 IFREG=1 IFDIR=0
mkdir(02755)           mode=02751 ISUID=0 ISGID=1 IFREG=0 IFDIR=1
chmod(02775)/dir       mode=02751 ISUID=0 ISGID=1 IFREG=0 IFDIR=1
```

结论：

1. **普通文件无法保存 S_ISUID/S_ISGID**：`chmod 4755`/`6755`/`6777` 与 `fchmod`
   都返回成功，但 `lstat` 报回的 `st_mode` 里 s 位恒为 0（模式被投影成 `0750`）。
   `chmod` 不报错，属于**静默剥离**。
2. **目录被强制 SGID**：`mkdir`/`chmod` 出来的目录模式恒为 `2771`（`drwxrws--x`），
   属组为 `file_manager`；`chmod 0755` 也去不掉 SGID。
3. 影响：
   - 任何依赖经典 setuid 提权模型的程序在 OHOS 上无法获得特权；
   - 任何 s[ug]id 审计器（sxid、chkrootkit、tripwire、aide）在 OHOS 上
     **永远发现不了 setuid 普通文件**，却会把**每个子目录**都当成 setgid 条目；
   - sxid 的 `FORBIDDEN` + `ENFORCE`（强制去掉禁止路径的 s 位）在普通文件上是空操作，
     在目录上会因 SGID 无法清除而报 `!`（失败）。
4. 真机 `stat -c '%a'` 实测：`chmod 4755` 的普通文件 = `750`；`chmod 2755` 的目录 = `2771`。

> 家目录挂载为 `hmdfs rw,nodev,relatime,hmmac=genfs`；底层 `userdata` 为 `hmfs ... nosuid`。
> 可写路径只有 HMDFS，故普通文件 s 位剥离在设备上稳定复现。

## 测试

### 上游

上游 4.20130802 **无测试套件**：`Makefile.am` 仅定义 `bin_PROGRAMS = sxid` 与
man/doc 数据，没有 `check` 目标、没有 `tests/` 目录、没有测试脚本 → 上游用例数 **N=0**。

### 消费者测试（test_package）

`test_package/test_sxid.sh` 共 **12** 条断言，真实运行安装后的 `bin/sxid`：

1. `-V` 打印 `sXid 4.20130802`；
2. `-h` 文档含 `--spotcheck`；
3. 首次运行把 `EXTRA_LIST` 里的普通文件报为新增（`+`）；
4. 平台 `S_ISUID` 能力探测后，sxid 对 setuid 普通文件的取舍与平台一致
   （OHOS/HMDFS：被剥离 → 不列出；POSIX：保留 → 列出）；
5. 平台 `S_ISGID` 能力探测后，sxid 对 setgid 目录的取舍与平台一致
   （OHOS/HMDFS：目录恒 SGID → 列出）；
6. 中间日志以 0600 创建（`umask 077`）；
7. 日志记录 `tracked.txt` 的正确 SHA-256（用独立常量校验，不依赖 `sha256sum`）；
8. 第二次运行检测到 SHA-256 与 inode 变化（`mi`）；
9. 轮转后的日志带上新的 SHA-256；
10. 轮转后旧 SHA-256 不再存在；
11. `-l`（listall）列出被跟踪条目；
12. `-k`（spotcheck）把当前工作目录当作搜索根（输出 `Spotcheck`）。

> 第 4/5 条采用「先探测平台能力、再要求 sxid 结果与平台一致」的写法，
> 因此在保留 s 位的普通 POSIX 文件系统上同样确定性通过，不会因平台而异红。

## 已知限制

- 上游设计为 root 运行以扫描全盘；真机为普通用户 + 无 root，测试只在受控子树上运行。
- 未验证邮件通知（`MAIL_PROG`）路径：真机无 `/usr/bin/mail`、无 cron，测试统一用 `-n`
  把报告输出到 stdout。`MAIL_PROG`/`CL_SUBJ` 仍按 Linux `mail` 语义编译。
- Windows/macOS 未验证（`validate()` 限定 Linux/OHOS）。
