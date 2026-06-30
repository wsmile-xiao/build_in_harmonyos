# systemc

**软件名称**: SystemC  
**版本**: latest (2.3.4)  
**分类**: 系统级建模/硬件描述语言  
**状态**: ❌ failed（编译失败）

## 软件介绍

SystemC 是一种基于 C++ 的硬件描述语言和系统级建模库，主要用于：
- 电子系统设计
- 硬件仿真
- 系统级验证
- 协同设计与验证

由 Accellera Systems Initiative 组织维护，是 IEEE 1666 标准的实现。

## 编译状态

### 当前版本 (latest)

- **状态**: failed
- **编译日期**: 2026-05-25
- **失败原因**: 网络连接问题，无法下载源码包

### 失败详情

**网络问题**：
- GitHub 连接超时（65秒后失败）
- Accellera 官网返回 404
- SourceForge 被 Cloudflare 拦截（403 Forbidden）
- 国内镜像站 DNS 解析失败

**尝试的下载源**：
1. https://github.com/accellera-official/systemc
2. https://accellera.org/images/downloads/standards/systemc/
3. https://sourceforge.net/projects/systemc/
4. https://mirrors.tuna.tsinghua.edu.cn/osdn/systemc/
5. https://gitee.com/mirrors/systemc

全部失败。

## 依赖关系

**构建依赖**:
- GCC (C++ 编译器)
- autotools (autoconf, automake)

**运行依赖**:
- 无特殊依赖

## 源码信息

**下载地址**: https://accellera.org/downloads/standards/systemc  
**GitHub**: https://github.com/accellera-official/systemc  
**许可证**: Apache 2.0

## 编译记录

详见 `latest/notes.md`

## 下一步行动

需要解决网络问题或提供本地源码包后重新编译：
```bash
# 使用本地源码包
python3 $SKILL_ROOT/scripts/ohc-run.py init-build systemc 2.3.4 --no-download

# 或在网络恢复后
python3 $SKILL_ROOT/scripts/ohc-run.py init-build systemc latest
```