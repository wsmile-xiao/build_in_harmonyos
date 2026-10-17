# lakai

lakai 是一套在 Linux/Unix 主机与 AKAI 采样器（S1000/S2000/S3000 系列）之间
通过 SCSI 总线交换采样（samples）与程序（programs）数据的工具集。

## 功能概述

- `liblakai.a` + `lakai.h`：封装 SCSI Generic（`sg`）设备访问与 S2000 专用
  SCSI 命令字（`S2000_MODE` / `S2000_SEND` / `S2000_STATUS` / `S2000_RECEIVE`），
  提供设备打开/关闭、状态查询、程序与采样列表枚举、采样与程序数据读写、
  删除等完整 API。
- `lakbak`：把采样器内存中的全部采样与程序完整备份到主机文件。
- `lakres`：把备份文件完整还原回采样器内存。
- `lakclear`：清空采样器 RAM 中现有的采样与程序。
- `lakai_asciitoakai()` / `lakai_akaitoascii()`：主机 ASCII 与 AKAI 字符集
  之间的双向转换（设备端只接受 AKAI 压缩字符表示）。

## OHOS 适配

- **构建系统**：上游仅提供 GNU Makefile（无 configure/autotools/cmake），
  OHOS 上可直接使用 `make` 原生编译，**零补丁**。
- **打包方式**：上游 `install` 目标依赖宿主 `install(1)` 工具并在 OHOS
  环境不可用，配方改为在 `package()` 中用 Conan `copy()` 收集产物
  （`bin/lakbak`、`bin/lakres`、`bin/lakclear`、`lib/liblakai.a`、
  `include/lakai.h`），不修改上游 Makefile。
- **编译器**：按 R33 从 Conan conf（`tools.build:compiler_executables`）
  读取 clang 绝对路径后显式传给 make，不依赖 shell 中的 `CC`。
- **SCSI 依赖**：源码 `#include <scsi/sg.h>` 与 `<scsi/scsi.h>`，OHOS sysroot
  已自带这两个头文件；无第三方依赖。
- **运行限制**：真实数据交换需要 SCSI 通用设备节点（`/dev/sg*`）且目标
  设备为 PROCESSOR 类型。无采样器时 `lakai_open()` 会按设计返回失败，
  库本身仍可正常链接与调用（可离线验证的 API 契约见 `0.1/tests/`）。
- **已知差异**：上游为 2004 年的 Linux 代码，编译时有 8 处
  `-Wpointer-sign` 类警告（`unsigned char *` 与 `char *` 混用），
  不影响功能，未做改动以保持与上游一致。

## 依赖关系

- 编译依赖：无（仅 libc 与 sysroot 头文件）
- 运行依赖：无

## 上游测试情况

上游 **无任何测试**：`Makefile` 中没有 `check`/`test` 目标，
源码树也没有 `tests/` 目录。本归档按仓库测试质量规范在
`0.1/tests/` 下自研了覆盖库 API 与三个 CLI 的测试，并在
`build()` 中真实编译执行（详见 `0.1/test_package/MANIFEST.yml`）。

## 参考资料

- 上游发布页：https://sourceforge.net/projects/lakai/
- 源码包：https://downloads.sourceforge.net/project/lakai/lakai/0.1/lakai-0.1.tar.gz
- 作者：Frank Neumann（`AUTHORS`）
- 许可证：GPL-2.0-only（见 `COPYING`；Debian 版权文件亦标注 `License: GPL-2`，
  即仅第 2 版，无 “or later” 条款）
