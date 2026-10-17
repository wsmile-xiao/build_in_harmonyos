# libppd 2.1.1 适配记录

## 软件简介

libppd 是 OpenPrinting 的 PPD（PostScript Printer Description）
文件处理库。它是 CUPS 3.x 时代 PPD API 的抽离，提供 PPD 文件
解析、属性访问、选项处理等功能，供打印驱动和过滤器使用。

- 上游：https://github.com/OpenPrinting/libppd
- 作者：OpenPrinting
- 许可证：Apache-2.0
- 语言：C
- 构建系统：autotools（autogen.sh + configure.ac + Makefile.am）
- 上游版本：2.1.1（GitHub tag）
- conan 版本：2.1.1

## 源码信息

- 下载 URL：https://github.com/OpenPrinting/libppd/archive/refs/tags/2.1.1.tar.gz
- SHA256：6f728cce3fb5eb862dec63859a9b258ae04684bb63345c7aaf47100826ea1ee6
- 大小：409211 字节
- 选择理由：GitHub 是 libppd 官方仓库，CI build_and_test.sh
  的 mirror fallback 覆盖 github.com，CI worker 可达。

## 依赖关系

libppd 硬依赖 CUPS 库（libcups）：

- configure.ac 优先检测 `pkg-config --exists cups3`（CUPS 3.x）
- 检测失败则 fallback 到 `cups-config`（CUPS 2.x）
- 仓库里有 cups 2.4.19，走 cups-config fallback 路径

仓库依赖：
- cups/2.4.19（已存在）

## 构建与安装

libppd 使用标准 autotools 构建：

1. `source()`：下载并解压 GitHub release tarball
2. `build()`：
   - `autoreconf`（生成 configure）
   - `configure --with-cups-config=cups-config`
   - `make`
3. `package()`：
   - `make install` 到 package_folder
   - 清理 `*.la` 和 `pkgconfig/` 目录

## 安装布局

- `lib/libppd.a`（静态库）
- `include/ppd/...`（头文件）
- `licenses/LICENSE`

## 测试策略（R34）

- 编译测试程序链接 libppd
- 验证 `ppd.h` 头文件可访问
- 验证 `libppd.a` 静态库存在

## 已知限制

- libppd 需要 cups-config 工具（由 cups/2.4.19 提供）
- 静态链接时需要确保 cups 也是静态库
