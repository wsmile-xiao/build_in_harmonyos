# libbfio

基础文件输入/输出库（Basic File Input/Output library）。

## 简介

libbfio 是 libyal 取证家族的基础 I/O 抽象层，纯 C 编写，为上层取证格式库
（libregf、liblnk、libmsiecf、libfs* 系列等）提供统一的文件访问接口：
普通文件、文件池（file pool，按名称集合聚合多个文件）、内存流与范围 IO
（子区域映射），支持窄/宽字符文件名（宽字符需构建期开启）。
本包为 20170123 版本线（monolithic API：`libbfio.h` 内联声明全部公开函数），
下游 libyal 库按该 API 线链接。

本库为纯库包，无可执行文件工具。

## 官网

https://github.com/libyal/libbfio

## 许可证

LGPL-3.0-or-later

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 20170123 | built | 2026-09-18 | autotools | 0（平台适配在配方 build() 内联完成） |

### 平台适配说明

| 问题编号 | 说明 | 解决方案 |
|----------|------|----------|
| E007 | GNU config.guess（2015-01-01）不识别 HarmonyOS | 内联添加 HarmonyOS 检测分支 |
| E007 | GNU config.sub（2017 结构）不识别 ohos 三元组 | maybe_os 列表与 os 合法性列表各加 `linux-ohos*` |
| E011 | HMDFS 上 umask 077 临时目录创建者无法写入 | configure/config.status 内 `umask 077`→`022` |
| E027 | configure 默认启用 NLS 依赖 gettext | `--disable-nls` |

### 源码来源说明

上游 GitHub 仓库重置后 20170123 的 release 资产已不存在；本包使用 Debian
的 pristine orig tarball（无 +dfsg、无重打包），内容哈希由 PGP 签名的
`libbfio_20170123-6.dsc` 锚定，溯源过程见版本级 notes.md。

## 依赖

无外部依赖。内部包含 libyal 系列子库（libcerror、libcthreads、libcdata、
libcfile、libcpath、libcsplit、libclocale、libcnotify、libuna）。
