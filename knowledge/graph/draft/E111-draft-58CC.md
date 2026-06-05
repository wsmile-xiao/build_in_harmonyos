# E107: toybox install 命令兼容性问题

> **结构化数据**: [graph/draft/E107-toybox-install-fail.kv](../graph/draft/E107-toybox-install-fail.kv) | **原则**: P-PLATFORM-003
> **严重度**: 🟡 warning | **分类**: platform | **自动修复**: ✅ use-gnu-coreutils

---

## 错误特征

```
install: inaccessible or not found
toybox install: incompatible options
install: cannot stat 'xxx': Permission denied
```

## 根因

鸿蒙默认使用 toybox 提供的 `install` 命令，功能比 GNU coreutils 的 `install` 简化，缺少某些选项或权限处理不完整。

## 解决方案

### 方案 1：手动复制替代 install

```bash
# 替代 install 命令
cp bin/* $PREFIX/bin/
chmod +x $PREFIX/bin/*
cp share/* $PREFIX/share/

# 替代 install -d
mkdir -p $PREFIX/bin
mkdir -p $PREFIX/share
```

### 方案 2：使用 GNU coreutils install

```bash
# 从 cmd-pkgs 安装 GNU coreutils
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- coreutils 9.10

# 使用 GNU install
$PREFIX/bin/install -m 755 bin/* $PREFIX/bin/
```

### 方案 3：修改 Makefile（不推荐）

```bash
# 在 Makefile 中替换 install 命令
sed -i 's|install -m|cp |g' Makefile
sed -i 's|install -d|mkdir -p |g' Makefile
```

⚠️ **警告**：修改 Makefile 可能引入其他问题，优先使用方案 1 或 2。

## 关键要点

- ✅ **toybox install 简化**：功能有限，部分选项不支持
- ✅ **GNU coreutils 完整**：从 cmd-pkgs 安装完整版
- ✅ **手动复制可靠**：最简单，无依赖问题

## 涉及软件

- ruby-build
- 其他使用 `install` 命令的 shell 脚本工具
- autotools 项目（Makefile 中使用 install）

## 相关模式

- [E105](E105.md) — Shell 脚本工具安装（组合出现）
- [E001](E001.md) — 找不到编译器（同为 toybox 工具链问题）

---
*doc/E107.md · knowledge graph v2 · 2026-05-19*