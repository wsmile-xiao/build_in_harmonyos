# fdclone

Console-based file manager for UNIX-like systems.

## 描述

fdclone (FDclone) 是一个基于终端的文件管理器，类似于 Norton Commander 或 Midnight Commander。它提供了双窗口界面、文件浏览、文件操作等功能。

fdclone 是原始 FD (File & Directory) 的克隆版本，专为 UNIX-like 系统设计，支持多种终端类型和字符集。

## 技术信息

- **语言**: C
- **构建系统**: makefile (自定义构建系统，非标准 autotools)
- **许可证**: 自定义许可证（自由软件）
- **官方网站**: http://hp.vector.co.jp/authors/VA012337/soft/fd/

## 编译版本

| 版本 | 状态 | 日期 | 补丁 |
|------|------|------|------|
| 3.01j | published | 2026-06-06 | 0001-Makefile.in.patch |

## 依赖

### 必需依赖

- **ncurses/6.4** - 终端界面库
  - libncursesw.a (静态库)
  - 已编译为静态库 (--without-shared)

## 安装

### 通过预编译包安装

```bash
# 从 cmd-pkgs 仓库下载安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- fdclone 3.01j
```

### 手动安装

从归档目录解压预编译包：

```bash
cd ~
tar -xzf fdclone-3.01j-ohos-aarch64.tar.gz
```

安装位置：
- 可执行文件: `~/usr/local/bin/fd`, `~/usr/local/bin/fdsh`
- 数据文件: `~/usr/local/bin/fd-*.tbl`
- 手册页: `~/usr/local/man/`

## 使用说明

### 启动文件管理器

```bash
# 在终端中运行
fd

# 或使用软链接
fdsh
```

### 基本操作

fdclone 使用类似 Norton Commander 的双窗口界面：

- **方向键** - 移动光标
- **Tab** - 切换左右窗口
- **Enter** - 进入目录/执行文件
- **F3** - 查看文件
- **F4** - 编辑文件
- **F5** - 复制文件
- **F6** - 移动文件
- **F7** - 创建目录
- **F8** - 删除文件
- **F10** - 退出

### 环境要求

- 需要终端环境（TTY）
- 支持的终端类型：xterm, vt100, linux, screen 等
- 需要 ncurses 库支持

## 编译注意事项

### 1. 自定义构建系统

fdclone 使用自定义的 Makefile 系统，**没有 configure 步骤**：

```bash
# 直接编译
make PREFIX=/path/to/install \
     CC=clang \
     CFLAGS="-I/path/to/include -fPIC -O2" \
     LDFLAGS="-L/path/to/lib"

# 安装
make install PREFIX=/path/to/install
```

### 2. HMDFS 文件系统限制

HMDFS 文件系统不支持硬链接，需要修改 Makefile.in：

```makefile
# 原始（硬链接）
$(LN) $$FD_BIN$$TARGET

# 修改后（软链接）
$(LN) -s $$FD_BIN$$TARGET
```

补丁文件：`patches/0001-Makefile.in.patch`

### 3. 库路径配置

需要正确指定 ncurses 库路径：

```bash
LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
```

### 4. BUILD 变量作为 DESTDIR 替代

fdclone 不支持标准的 DESTDIR，使用 BUILD 变量进行 staging 安装：

```bash
# staging 安装
make install PREFIX=/storage/Users/currentUser/usr/local \
     BUILD=/path/to/staging
```

## 已知限制

1. **终端环境依赖**: fdclone 需要终端环境运行，在非交互式 shell 中会报错 `ioctl(): Permission denied`
2. **无标准测试套件**: 没有 `make check` 目标
3. **G0 验证不适用**: 无 configure 脚本，无法执行标准 G0 干净构建验证
4. **需要 ELF 签名**: 在鸿蒙系统上执行前需要签名

## 文件说明

### 可执行文件

- `fd` - 主可执行文件（ELF 64-bit AArch64 PIE）
- `fdsh` - fdsh 软链接（指向 fd）

### 数据文件

- `fd-unicd.tbl` - Unicode 字符表
- `fd-dict.tbl` - 字典数据表
- `fd-cat.ja` - 日语目录文件
- `fd-cat.C` - 英文目录文件

## 下载

预编译包可从以下位置获取：

1. **cmd-pkgs 仓库**: https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs
2. **本地归档**: `archives/f/fdclone/3.01j/packaging/`

## 版本历史

| 版本 | 发布日期 | 说明 |
|------|---------|------|
| 3.01j | 2026-06-06 | 首次为 OpenHarmony 编译，添加 HMDFS 适配补丁 |

## 参考链接

- 官方网站: http://hp.vector.co.jp/authors/VA012337/soft/fd/
- 源码下载: https://deb.debian.org/debian/pool/main/f/fdclone/
- 编译文档: `archives/f/fdclone/3.01j/notes.md`