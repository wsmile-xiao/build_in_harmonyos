# libsmi — OpenHarmony 编译档案

## 软件简介
libsmi 是一个用于访问 SMI (Structure of Management Information) MIB 信息库的 C 语言库，支持 SNMP MIB 和 YANG 模块的解析。

## 编译版本
| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 0.5.0 | ✅ success | autotools | 预编译包已生成 |

## 功能特性
- MIB 模块解析器 (SMIv1, SMIv2, SMIng)
- YANG 模块解析器
- 多种格式输出 (tree, smiv2, yang, xml, python 等)
- MIB 语法检查工具 (smilint)
- MIB 模块查询工具 (smiquery)

## 工具列表
| 工具 | 说明 |
|------|------|
| smidump | MIB/YANG 模块转多种格式 |
| smilint | MIB 语法检查 |
| smiquery | MIB 模块查询 |
| smidiff | MIB 模块差异比较 |
| smixlate | OID 翻译工具 |
| smistrip | 从文档提取 MIB |
| smicache | MIB 缓存管理 |

## 依赖关系
- 无外部依赖（纯 C 实现）

## 已知限制
1. **HMDFS config.status 临时目录**: 需预创建 `$TMPDIR/libsmi_conf_fixed` 目录
2. **RPATH**: 需设置 `LD_LIBRARY_PATH=$HOME/usr/local/lib`
3. **G0 干净构建**: SKIP (HMDFS 限制)

## 相关链接
- 官方网站: https://www.ibr.cs.tu-bs.de/projects/libsmi/
- 源码下载: https://www.ibr.cs.tu-bs.de/projects/libsmi/download/

---
**归档路径**: archives/l/libsmi/