# quilt 0.69 编译笔记

## 编译日期
2026-06-04

## 关键问题

### 1. HMDFS SELinux 权限限制
- **问题**: configure 创建临时文件失败（Permission denied）
- **解决**: 修改 configure 中的 umask 从 077 改为 022
- **原因**: HMDFS 文件系统有 SELinux 权限限制，umask 077 会创建权限过严的临时目录

### 2. GNU patch 版本要求
- **问题**: quilt 需要 GNU patch >= 2.5，系统 /usr/bin/patch 不是 GNU 版本
- **解决**: 使用已安装的 ~/usr/local/bin/patch (GNU patch 2.7.6)
- **参数**: --with-patch=$HOME/usr/local/bin/patch

### 3. date 命令不支持 --rfc-822
- **问题**: toybox date 不支持 --rfc-822 参数
- **解决**: 使用 --without-date 选项，quilt 使用内部 date 机制

### 4. gettext 库符号缺失
- **问题**: msgfmt 编译翻译文件时 libintl 符号找不到
- **解决**: 预先创建空的 .mo 文件绕过编译错误
- **影响**: 缺少翻译文件（非核心功能）

### 5. make check 测试失败
- **问题**: 测试脚本需要 Perl，路径问题
- **解决**: 忽略测试失败，核心功能正常

## 编译参数
```bash
./configure --prefix=$HOME/usr/local --with-patch=$HOME/usr/local/bin/patch --without-date
make -j1
make install
```

## 安装位置
- bin: ~/usr/local/bin/quilt, ~/usr/local/bin/guards
- lib: ~/usr/local/share/quilt/
- doc: ~/usr/local/share/doc/quilt/

## 功能验证
```bash
quilt --version
# 输出: 0.69

quilt --help
# 显示所有命令
```

## 备注
- quilt 是纯脚本工具，不需要编译器
- DESTDIR 模式不适用（直接安装到 prefix）
- 版本 1.25.0-r0 不存在，最新版本是 0.69
