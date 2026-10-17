# daemonize 1.7.8 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# 1. 下载源码 (GitHub tag: release-1.7.8)
# URL: https://github.com/bmc/daemonize/archive/refs/tags/release-1.7.8.tar.gz

# 2. 修复 configure 脚本中的 umask 问题
#    (HMDFS setgid 导致 umask 077 创建的临时目录不可写)
sed -i 's/umask 077/umask 022/g' configure

# 3. 配置
./configure --prefix=$DEFAULT_PREFIX

# 4. 编译
make

# 5. 安装到 staging
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied on confXXXXXX/subs1.awk | HMDFS setgid bit causes `umask 077 && mktemp -d` to create dirs with `drwx--S---` (2700) permissions, blocking owner writes | Changed `umask 077` to `umask 022` in configure script |

## 源码修改

### configure — umask fix
- 文件: `configure`
- 修改: `sed -i 's/umask 077/umask 022/g' configure`
- 原因: HMDFS 文件系统在 setgid 目录下，umask 077 创建的临时目录（drwx--S---）无法写入，导致 config.status 失败
- 影响: 3处 `umask 077` → `umask 022`（行 4500, 5248, 5253）

## 依赖版本

无外部依赖。daemonize 是纯 C 程序，仅依赖标准 C 库和 POSIX 头文件。

## 验证结果

```bash
# 二进制可执行
$ ./daemonize --version
daemonize, version 1.7.8

# testdaemon 测试程序正常运行
$ ./testdaemon
[2026/08/06 05:46:53] ----------- NEW RUN
[2026/08/06 05:46:53] Working directory=...
[2026/08/06 05:46:55] Message to standard output.
[2026/08/06 05:46:55] Message to standard error.
```

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/daemonize | 守护进程工具二进制 |
| share/man/man1/daemonize.1 | man 手册页 |

## 注意事项

- daemonize 是命令行工具，需要创建 commands.json (R38)
- 无 make check 目标，通过手动运行 testdaemon 验证
- 源码 tag 为 `release-1.7.8`（不是 v1.7.8）
---

**编译结束**: 2026-08-06 05:52
**最终状态**: built
