# ACL (Access Control Lists)

## 简介

ACL（Access Control Lists）是 Linux 文件系统的扩展权限控制机制，提供比传统 Unix 权限更细粒度的访问控制。

## 功能概述

- **细粒度权限控制**：支持为多个用户和组设置不同的权限
- **继承权限**：支持默认 ACL，子文件/目录可继承父目录权限
- **命令工具**：
  - `getfacl` - 获取文件/目录的 ACL
  - `setfacl` - 设置文件/目录的 ACL
  - `chacl` - 更改文件/目录的 ACL

## OHOS 适配要点

### 1. HMDFS 文件系统限制

HarmonyOS 使用 HMDFS 文件系统，有以下限制：
- 不支持创建嵌套临时目录结构
- 需要设置 `TMPDIR=$HOME/tmp` 避免 autotools 的临时目录问题

### 2. 构建系统适配

- 需要 attr 库（Extended Attributes）支持
- 需要下载最新版 config.sub 和 config.guess 支持 ohos 操作系统
- 需要创建 attr 的 pkg-config 文件（预编译包缺少）

### 3. 编译环境设置

```bash
export TMPDIR=$HOME/tmp
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
export LDFLAGS="-L$HOME/usr/local/lib"
export CFLAGS="-I$HOME/usr/local/include"
```

## 依赖关系

### 编译依赖
- **attr** (Extended Attributes library) - 必需
- gettext - 可选（NLS 支持）

### 运行依赖
- libattr.so.1 - 运行时库依赖

## 参考资料

- 官网：https://savannah.nongnu.org/projects/acl
- 源码：https://download.savannah.gnu.org/releases/acl/
- 相关软件：attr (Extended Attributes)