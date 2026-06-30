# tree-sitter-python

Python grammar for tree-sitter - 用于解析Python代码的语法树生成器。

## 软件信息

- **主页**: https://github.com/tree-sitter/tree-sitter-python
- **分类**: 语言解析器
- **许可证**: MIT

## 编译版本

| 版本 | 状态 | 日期 | 构建系统 |
|------|------|------|----------|
| 0.23.6 | built | 2026-06-12 | cmake |

## 功能说明

tree-sitter-python 是 tree-sitter 的 Python 语言绑定，提供：
- 高性能的 Python 语法解析器
- 错误容忍的语法树生成
- 用于代码分析、编辑器语法高亮等场景

## 编译产物

### 0.23.6

- **共享库**: libtree-sitter-python.so
- **头文件**: tree_sitter/tree-sitter-python.h
- **pkg-config**: tree-sitter-python.pc
- **预编译包**: tree-sitter-python-0.23.6-ohos-aarch64.tar.gz (533KB)

## 使用方法

### 安装预编译包

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- tree-sitter-python 0.23.6
```

### 验证安装

```bash
pkg-config --modversion tree-sitter-python
# 输出: 0.23.6
```

## 编译注意事项

1. **tar 解压**: HMDFS 不支持硬链接，使用 Python tarfile 模块解压
2. **构建系统**: CMake 自动检测，无需手动指定
3. **无依赖**: tree-sitter-python 不依赖其他库

## 相关链接

- [详细编译笔记](0.23.6/notes.md)
- [编译配置](0.23.6/manifest.yaml)