# byobu 6.13 编译笔记

## 编译信息
- 软件名称: byobu
- 版本: 6.13
- 构建系统: autotools (纯 shell/Python 脚本项目)
- 编译时间: 2026-05-25

## 编译过程

### 1. 源码获取
- 来源: GitHub (dustinkirkland/byobu tag 6.13)
- URL: https://api.github.com/repos/dustinkirkland/byobu/tarball/6.13

### 2. 构建系统生成
```bash
aclocal
automake --add-missing --copy
autoconf
```

### 3. 配置
```bash
./configure --prefix=$HOME/usr/local
```

**平台适配**:
- 修复 config.status 中临时目录创建逻辑
- 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "$TMPDIR/confXXXXXX"`
- 原因: 鸿蒙平台当前目录可能无写权限

### 4. 编译
```bash
make -j1
```

纯脚本项目，无需编译二进制。

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX
make install
```

## 平台适配问题

### E058: HOME 目录所有权检查
**现象**: byobu 检查 `[ ! -O "$HOME" ]` 失败，因为鸿蒙平台用户 UID 与 HOME 目录 owner UID 不匹配。

**原因**: 鸿蒙平台的多用户隔离机制，用户目录由 file_manager (UID 20001006) 创建，但实际用户 UID 为 20020088。

**解决方案**: 添加环境变量检查 `__OHOS__`，在鸿蒙平台跳过此检查：
```bash
if [ ! -O "$HOME" ] && [ -z "$__OHOS__" ]; then
```

**补丁**: 0001-home-ownership-check.patch

## 依赖说明
- 运行时依赖: tmux >= 1.5 或 screen
- 可选依赖: python-newt (配置界面), gsed

## 产物
- 预编译包: byobu-6.13-ohos-aarch64.tar.gz (468KB)
- 内容: shell 脚本 + 配置文件 + man pages

---
**编译结束**: 2026-05-25 21:52
**最终状态**: built
