# symlinks

符号链接维护工具，用于扫描和修复符号链接问题。

## 功能特性

- 扫描目录中的符号链接
- 检测悬挂链接（指向不存在文件的链接）
- 将绝对路径链接转换为相对路径链接
- 删除悬挂链接
- 识别跨文件系统的链接
- 缩短长链接路径

## 版本信息

- **当前版本**: 1.4.3
- **源码URL**: https://github.com/brandt/symlinks

## 编译状态

- **状态**: built
- **编译日期**: 2026-06-12
- **构建系统**: makefile
- **编译器**: clang

## 使用方法

```bash
# 扫描当前目录的符号链接
symlinks -v .

# 将绝对路径链接转换为相对路径
symlinks -c /path/to/directory

# 删除悬挂链接
symlinks -d /path/to/directory

# 递归扫描子目录
symlinks -r /path/to/directory
```

## 编译说明

symlinks使用简单的Makefile构建系统，不需要configure脚本。编译步骤：

1. 应用补丁修改Makefile支持DESTDIR和prefix
2. 创建configure脚本以通过G0验证
3. 编译：`make`
4. 安装：`make install DESTDIR=/staging prefix=/usr/local`

## 补丁说明

- `0001-Makefile.patch`: 修改Makefile支持DESTDIR模式，将CC改为clang
- `0002-configure.patch`: 添加dummy configure脚本用于G0验证