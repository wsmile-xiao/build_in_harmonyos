# E105: Shell 脚本工具安装

> **结构化数据**: [graph/draft/E105-shell-script-tools.kv](../graph/draft/E105-shell-script-tools.kv) | **原则**: P-BUILD-005
> **严重度**: 🟡 warning | **分类**: build_system | **自动修复**: ❌ manual

---

## 错误特征

```
install: inaccessible or not found
Shell script tools don't require traditional compilation
```

## 根因

Shell 脚本工具（如 ruby-build）不需要传统编译流程，但安装命令可能因 toybox 兼容性问题失败。

## 解决方案

### 标准安装流程

```bash
# 1. 下载源码
git clone --depth 1 https://github.com/rbenv/ruby-build.git

# 2. 手动复制文件（如果 install 命令失败）
PREFIX=$DEFAULT_PREFIX
cp bin/* $PREFIX/bin/
cp share/* $PREFIX/share/
chmod +x $PREFIX/bin/*
```

### DESTDIR 模式打包

```bash
# 创建 staging 目录
TEST_PREFIX=$HOME/tmp/test-install-ruby-build-latest
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX

# 手动复制文件到 staging 目录
cp -r bin $TEST_PREFIX/$DEFAULT_PREFIX/
cp -r share $TEST_PREFIX/$DEFAULT_PREFIX/
chmod +x $TEST_PREFIX/$DEFAULT_PREFIX/bin/*

# 打包
tar czf ruby-build-latest-ohos-aarch64.tar.gz -C $TEST_PREFIX .
```

## 关键要点

- ✅ **无 ELF 二进制**：shell 脚本无需 ELF 签名
- ✅ **检查可执行权限**：`chmod +x bin/*`
- ✅ **验证脚本功能**：`ruby-build --version`、`ruby-build --list`

## 涉及软件

- ruby-build
- 其他 shell 脚本工具（如 pyenv、nodenv）

## 相关模式

- [E107](E107.md) — toybox install 命令兼容性问题
- [E002](E002.md) — 临时目录不可写（可能影响 staging）

---
*doc/E105.md · knowledge graph v2 · 2026-05-19*