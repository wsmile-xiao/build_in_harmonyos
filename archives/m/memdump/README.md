# memdump

memdump 是 Wietse Venema 写的内存取证工具：把物理内存（默认 `/dev/mem`）按块转储到
标准输出，并跳过内存空洞，可配合 `nc`/`openssl s_client` 把结果送出机器。

## 功能概述

- 默认转储物理内存 `/dev/mem`；`-k` 改转储内核内存 `/dev/kmem`。
- `-b` 读缓冲大小、`-p` 页大小、`-s` 转储总长度（三者都支持 `k`/`m`/`g` 后缀，大小写不敏感）。
- `-m map_file` 把遍历到的内存区域起止地址（十六进制，一行一段）写到映射文件，`-m-` 写标准错误。
- `-v` 递增调试详细度，审计信息走标准错误。
- 空洞处理靠 `read()` 失败后 `lseek(fd, where + page_size, SEEK_SET)` 逐页跳过；
  定义 `USE_PREAD` 的平台上改用 `pread()` 并以 `EFAULT` 判空洞（上游只给 SunOS 打开）。
- 发行包内含 `memdump.1` 手册页（`.TH MEMDUMP 1`）与 IBM Public License 1.0 全文。

## OHOS 适配

上游是 2005 年的 raw Makefile，没有任何自动配置层，适配要点（一手实测）：

1. **默认目标是个探针，不是构建**：Makefile 的第一个目标是 `what:` → `sh makedefs`，
   makedefs 用 `uname -s`/`uname -r` 拼字符串猜平台。HarmonyOS 的读数是
   `sysname=HarmonyOS`、`release=HongMeng Kernel 1.12.0`，落到 `*)` 分支
   打印 `unsupported system: HarmonyOS.HongMeng Kernel 1.12.0` 并 `exit 1`
   ⇒ 裸 `make` 必然失败，本配方显式调 `make all` 并自带 `DEFS=-DLINUX2`。
2. **构建主机没有 gcc**：Makefile 把 `CC` 写死成 `gcc -Wformat -Wunused`，
   OHOS 上只有 clang 15 ⇒ 覆盖 `CC`（值取自 Conan conf，不裸用 shell 的 `${CC}`）。
3. **`<paths.h>` 少两个宏**：LINUX2 分支指望 `paths.h` 给 `_PATH_MEM`/`_PATH_KMEM`，
   OHOS libc 的 `paths.h` 没有 ⇒ 3 处 `use of undeclared identifier`。补丁
   `0001-memdump.c.patch` 照上游 SUNOS5 分支已有的内联定义写法，加 `#ifndef` 特征守卫，
   glibc/BSD 上行为不变（不是平台特判宏）。
4. **没有 install 目标**：`manpages` 目标又依赖上游私有 `srctoman` ⇒ 配方手动搬运
   `bin/memdump`、`share/man/man1/memdump.1`、`licenses/LICENSE`。
5. **运行级限制（如实申报）**：OHOS PC 上 `/dev/mem` 与 `/dev/kmem` **设备节点不存在**
   （`stat`/`open` 返回 ENOENT，不是 EACCES/EPERM —— 不是权限不够，是节点缺失），
   故转储功能在本平台不可用；制品按上游契约报 `open /dev/mem: No such file or directory`
   并以 1 退出。这属运行级环境限制、非适配缺陷（同 `archives/b/bridge-utils/1.5` 先例口径）。
   另注：memdump 的转储逻辑是 `open`+`read`+`lseek`，**不使用 mmap**（源码只 include
   了 `<sys/mman.h>`，全文件无 mmap 调用）。
6. 上游无 `--version`/`--help`：任何未知选项都走 `usage()` → `error()` → `exit(1)`。

## 依赖关系

- 编译依赖：无外部库。仅需 C 编译器 + make（Makefile 的 `SYSLIBS` 为空，
  源码 include 面为 `sys/types.h`、`sys/mman.h`、`time.h`、`fcntl.h`、`unistd.h`、
  `string.h`、`stdio.h`、`stdlib.h`、`paths.h` 与包内 3 个头）。
- 运行依赖：`libc.so`（动态链接，见 `readelf -d`）。
- 运行期需要平台暴露 `/dev/mem`（或 `-k` 时的 `/dev/kmem`）才可真正转储；
  OHOS PC 当前不提供该设备节点。

## 参考资料

- 上游（作者发布页）：<http://www.porcupine.org/forensics/tct.html>
- 源码包（唯一官方址，明文 http——该主机 443 无监听）：<http://www.porcupine.org/forensics/memdump-1.01.tar.gz>
- 许可证：IBM Public License version 1.0（发行包内 `LICENSE`）
- 本包适配笔记：`1.01/notes.md`；编译元数据：`1.01/manifest.yaml`
