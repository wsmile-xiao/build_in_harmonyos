# sfsexp — Small, Fast S-Expression Library

小型、快速的 S-表达式（S-Expression）解析和操作库。sfsexp 提供 C 语言 API 用于解析、构建、遍历和可视化 S-表达式数据结构，支持续体（continuation）增量解析模式。

## 基本信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.4.1 |
| 许可证 | LGPL-2.1-or-later |
| 语言 | C |
| 构建系统 | autotools |
| 官方源码 | https://github.com/mjsottile/sfsexp |

## OHOS 编译版本

| 版本 | 状态 | 构建日期 | 补丁数 | 预编译包 |
|------|------|---------|--------|---------|
| 1.4.1 | built | 2026-05-22 | 4 | sfsexp-1.4.1-ohos-aarch64.tar.gz |

## 库功能概览

- **sexp.h**: 核心 API（`parse_sexp`, `print_sexp`, `destroy_sexp`, `cparse_sexp` 等）
- **sexp_ops.h**: 操作函数（`copy_sexp`, `find_sexp`, `bfs_find_sexp`, `sexp_list_length` 等）
- **sexp_vis.h**: DOT 可视化（`sexp_to_dotfile`）
- **sexp_memory.h**: 内存管理（自定义分配器接口）
- **sexp_errors.h**: 错误码定义
- **cstring.h**: C 字符串动态缓冲
- **faststack.h**: 快速栈实现

## 依赖

无外部依赖，仅依赖 libc。

## OHOS 适配要点

- config.guess/config.sub 需添加 HarmonyOS（linux-ohos）平台检测
- configure 和 Makefile.in 中 umask 077 需改为 007（HMDFS 权限限制）
- 动态链接的测试程序因 OHOS ELF 签名限制无法运行，需静态链接验证