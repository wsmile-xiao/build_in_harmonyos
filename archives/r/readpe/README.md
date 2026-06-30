# readpe (pev 工具包)

## 软件描述
readpe 是 pev (PE file analysis toolkit) 工具包的一部分，用于分析和解析 PE (Portable Executable) 格式的二进制文件。

## 功能
pev 包含多个工具：
- **readpe**: 显示 PE 文件的基本信息
- **rva2ofs**: RVA 到文件偏移转换
- **ofs2rva**: 文件偏移到 RVA 转换
- **pehash**: 计算 PE 文件哈希
- **pesec**: PE 文件安全特征分析
- **pescan**: PE 文件扫描
- **pepack**: PE 文件打包检测
- **pestr**: PE 文件字符串提取
- **pedis**: PE 文件反汇编
- **peres**: PE 文件资源提取
- **peldd**: PE 文件依赖分析

## 项目信息
- **官方网站**: https://pev.sourceforge.net/
- **GitHub**: https://github.com/mentebinaria/readpe
- **版本**: 0.81 (2020年发布，最新稳定版本)
- **许可证**: GPL v3

## 编译历史
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 0.81 | built | 2026-06-16 | 主程序编译成功，plugins 未编译 |

## 依赖
- OpenSSL (libssl, libcrypto)

## 已知问题
- OpenHarmony 需要修复 strerror_r 兼容性问题
- plugins 需要共享库支持，当前未编译
- 需要 ELF 签名才能执行