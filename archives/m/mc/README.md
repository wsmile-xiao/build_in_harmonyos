# Midnight Commander

GNU Midnight Commander 是一个功能强大的视觉文件管理器。

## 功能特性

- 双面板文件管理界面
- 支持多种文件系统操作
- 内置文本编辑器
- 支持远程文件访问（FTP、SFTP）
- 可扩展的文件类型识别

## 编译说明

### 依赖

- glib2 (>= 2.0)
- ncurses 或 slang
- autoconf, automake

### 构建系统

使用 autotools，标准构建流程：
```bash
./configure --prefix=$DEFAULT_PREFIX
make
make install DESTDIR=$TEST_PREFIX
```

### 已知问题

- 平台检测可能需要更新 config.guess/config.sub