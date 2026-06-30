# cdrtools

## 简介

cdrtools 是一个光盘刻录工具集，包含以下主要工具：
- **mkisofs**: 创建 ISO 9660 文件系统映像
- **cdrecord**: 光盘刻录工具
- **cdda2wav**: CD 音轨提取工具
- **readcd**: 光盘读取工具

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 3.02a09 | published | 2026-05-28 |

## 编译说明

cdrtools 使用 Schily makefilesystem，不使用标准的 autotools configure。构建系统会自动检测操作系统和编译器。

### HarmonyOS 适配

需要创建以下文件：
- `RULES/os-harmonyos.id`: 操作系统识别文件
- `RULES/os-harmonyos.def`: 操作系统定义文件
- `DEFAULTS/Defaults.harmonyos`: 默认配置文件

### 构建命令

```bash
make -j1 GMAKE_NOWARN=true INS_BASE=$HOME/usr/local
make install INS_BASE=$HOME/usr/local DESTDIR=$HOME/test-install-cdrtools-{version}
```

## 依赖

无外部依赖。

## 许可证

CDDL-1.0 (Common Development and Distribution License)