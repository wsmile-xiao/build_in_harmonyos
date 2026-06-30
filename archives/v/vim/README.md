# Vim - Vi IMproved

## 软件简介

Vim 是一个高度可配置的文本编辑器，用于高效地创建和修改文本。它是 vi 编辑器的改进版本，提供了强大的编辑功能。

## 功能特性

- **Huge 版本**：包含完整功能集
- **多字节支持**：支持中文等多语言文本
- **Python3 支持**：可使用 Python 脚本扩展
- **终端支持**：内置终端模拟器
- **语法高亮**：支持数百种编程语言
- **代码补全**：智能补全功能

## 编译信息

### 版本
- 当前版本：9.1.1000
- 包含补丁：1-1000

### 依赖
- ncurses 6.4（终端库）

### 平台适配
- 解决 HMDFS 文件系统权限问题（E011）
- 修改 configure 中的 umask 077 为 umask 022
- ELF 签名确保可执行性

### 编译参数
```bash
./configure --prefix=$DEFAULT_PREFIX \
  --with-features=huge \
  --enable-multibyte \
  --enable-python3interp \
  --with-tlib=ncursesw \
  --enable-cscope
```

## 安装使用

### 安装路径
- 二进制：`~/usr/local/bin/vim`
- 工具：`~/usr/local/bin/xxd`

### 验证安装
```bash
vim --version
xxd -v
```

## 注意事项

- 首次执行需要安全弹窗确认
- 需要 ncurses 库支持
- HMDFS 平台需要应用 E011 补丁

## 资源链接

- 官网：https://www.vim.org/
- 源码：https://github.com/vim/vim
- 文档：https://vimhelp.org/