# clib — C 包管理器

C 语言的包管理器，用于安装和管理 C/C++ 包。提供命令行工具从 GitHub 和其他源下载、安装 C 库。

## 基本信息

| 属性 | 值 |
|------|-----|
| 名称 | clib |
| 版本 | 2.8.7 |
| 许可证 | MIT |
| 语言 | C (C99) |
| 构建系统 | Makefile |
| 依赖 | curl (libcurl) |
| 源码地址 | https://github.com/clibs/clib |

## 二进制列表

clib 安装后提供以下 9 个命令行工具：

| 命令 | 功能 |
|------|------|
| `clib` | 主命令入口 |
| `clib-install` | 安装包 |
| `clib-search` | 搜索包 |
| `clib-init` | 初始化新项目 |
| `clib-configure` | 配置包 |
| `clib-build` | 构建包 |
| `clib-update` | 更新包 |
| `clib-upgrade` | 升级包 |
| `clib-uninstall` | 卸载包 |

## 编译版本索引

| 版本 | 状态 | 日期 | 补丁 | 说明 |
|------|------|------|------|------|
| 2.8.7 | built | 2026-06-16 | 1个 (0001-Makefile.patch) | 需DESTDIR补丁；依赖curl 8.19.0 |

## 安装前置条件

用户安装 clib 预编译包前需确保系统已安装 curl（libcurl）。预编译包中已包含 libcurl.so.4 等外部动态库作为 lib/external/ 目录下的依赖。

## 平台适配说明

- Makefile 原始不支持 DESTDIR，已通过补丁添加支持
- `scripts/feature-test-pthreads` 在鸿蒙平台不存在，但不影响编译
- `pthread_cancel` 在 musl/OHOS 上不可用，clib 的并行下载功能受限，不影响基本使用
