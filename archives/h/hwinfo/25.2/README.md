# hwinfo - Hardware Information Tool

**版本**: 25.2  
**状态**: compiling → success  
**编译日期**: 2026-04-29  

## 简介

hwinfo 是一个用于检测和报告系统硬件信息的工具。它可以识别各种硬件设备，包括 CPU、内存、磁盘、网络接口、USB 设备等。

## 编译信息

- **构建系统**: Makefile
- **编译器**: clang
- **平台**: aarch64 (OpenHarmony)
- **依赖**: 无外部依赖

## 编译问题与解决方案

### 问题 1: HD_VERSION_STRING 未定义

**现象**: 编译时报错 `use of undeclared identifier 'HD_VERSION_STRING'`

**原因**: Makefile 应自动生成 `src/hd/version.h` 文件，但因 git2log 权限问题未能生成

**解决方案**: 
```bash
cd src/hd
echo "#define HD_VERSION_STRING \"25.2\"" > version.h
```

**知识沉淀**: 新建知识条目记录 Makefile 自动生成文件的失败模式

## 安装

预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- hwinfo 25.2
```

## 使用示例

```bash
hwinfo --version       # 显示版本信息
hwinfo --short         # 简短硬件概览
hwinfo --all           # 详细硬件信息
hwinfo --cpu           # CPU 信息
hwinfo --disk          # 磁盘信息
```

## 文件清单

- `/usr/sbin/hwinfo` - 主程序
- `/usr/sbin/check_hd` - 硬件检查工具
- `/usr/sbin/convert_hd` - 硬件数据转换工具
- `/usr/lib/libhd.so.25.2` - 共享库
- `/usr/lib/libhd.a` - 静态库
- `/usr/include/hd.h` - 头文件

## 许可证

GPL-2.0-or-later

## 参考

- [官方仓库](https://github.com/openSUSE/hwinfo)
- [OpenSUSE 项目](https://build.opensuse.org/package/show/openSUSE:Factory/hwinfo)