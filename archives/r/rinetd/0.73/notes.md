# rinetd 0.73 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 `ohc-run.py init-build rinetd 0.73 --no-download --force` 初始化构建环境
2. 手动下载源码包（gitcode 镜像）并解压到 builds 目录
3. 修补 configure 脚本中的 `umask 077` → `umask 022`（HMDFS 兼容性）
4. 执行 `CONFIG_SHELL=bash bash ./configure --prefix=$DEFAULT_PREFIX`
5. 执行 `make -j1` 编译
6. 执行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
7. 执行 `make check`（无测试套件，直接通过）
8. 执行 `ohc-run.py package rinetd 0.73` 打包
9. 执行 `make install`（不带 DESTDIR）安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 执行失败，config.status 创建临时目录后无法写入 | HMDFS 文件系统上 `umask 077` 创建的目录权限为 `drwx--S---`，所有者也无法写入 | 将 configure 脚本中两处 `umask 077` 改为 `umask 022` |
| 2 | GitHub 不可达，源码包无法下载 | 网络限制，GitHub 域名超时 | 使用 gitcode 镜像下载 rinetd-0.73.tar.bz2 |
| 3 | /tmp 只读，mktemp 等命令失败 | HMDFS 文件系统限制 | 设置 TMPDIR=$HOME/tmp，使用用户目录替代 |

## 源码修改

- **0001-configure.patch**: 修改 configure 脚本第 6139 和 6144 行，将 `umask 077` 改为 `umask 022`
  - 原因: HMDFS 文件系统上 `umask 077` 创建的临时目录权限异常，导致 configure 生成的 config.status 无法写入临时文件

## 依赖版本

无额外依赖。rinetd 0.73 仅依赖标准 C 库和 POSIX 系统调用。

## 验证结果

```bash
$ $DEFAULT_PREFIX/sbin/rinetd --version
rinetd 0.73
```

二进制文件信息:
- 路径: /storage/Users/currentUser/usr/local/sbin/rinetd
- 大小: 51584 bytes
- 权限: -rwxrwx---

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rinetd-0.73-ohos-aarch64.tar.gz | 61KB | 预编译包（含二进制、配置文件、man page） |

## 注意事项

- rinetd 安装到 sbin/ 而非 bin/，G2 功能验证在 bin/ 目录下查找二进制文件时会报"无二进制文件"警告，属正常现象
- G0 干净构建验证因 Python subprocess 平台限制（tar.bz2 解压使用 zcat 失败）未能自动完成，但已手动验证编译流程可重复
- 补丁仅修改 configure 脚本的 umask 设置，不影响软件功能

---

**编译结束**: 2026-06-25 11:08
**最终状态**: built
