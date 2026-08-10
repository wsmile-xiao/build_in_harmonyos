# pwgen 2.08 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HarmonyOS 上 `mktemp -d` 配合 `umask 077` 创建目录权限为 `drwx--S---`(2700)，导致无法写入文件 | 补丁 0001-configure.patch：移除 `umask 077`，使用 `${TMPDIR}` 创建临时目录并 `chmod 755` |
| 2 | make -j2 时 `jobserver mkfifo: Operation not permitted` | HarmonyOS 上 mkfifo 不允许 | 非致命警告，make 自动降级为单线程编译成功 |

## 源码修改

- 补丁文件: `patches/0001-configure.patch`
- 修改文件: `configure`
- 修改内容:
  - `mktemp -d "./confXXXXXX"` → `mktemp -d "${TMPDIR:-/tmp}/confXXXXXX"` + `chmod 755`
  - `umask 077 && mkdir` → `mkdir && chmod 755`
  - 移除 `umask 077`（HarmonyOS 上导致目录权限过严）

## 依赖版本

无外部依赖（6个C源文件自包含）

## 验证结果

```bash
$ pwgen --help
Usage: pwgen [ OPTIONS ] [ pw_length ] [ num_pw ]
...
$ pwgen 10 3
aiThee7oon
eiYesh2aeb
He6ahth7xe
$ pwgen -s 15 5
LB1ysf4EqQ8F80a
cSBj6pZPg9uX47M
AG4LQPkODHOA3Dx
UbL4ahhyF1Mcrux
xbzkVBQtwdVLA5Y
```

## 注意事项

- pwgen 是命令行工具（application），不是库
- conanfile.py 使用 `package_type = "application"` 和 `cpp_info.bindirs`
- commands.json 已在软件级别目录声明
---

**编译结束**: 2026-08-08 02:53
**最终状态**: built
