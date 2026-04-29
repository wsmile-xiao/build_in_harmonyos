# pstree 23.7 编译记录

## 编译信息

- **软件**: pstree (from psmisc)
- **版本**: 23.7
- **日期**: 2026-04-28
- **状态**: 成功

## 编译过程

### 1. 源码获取

```bash
git clone https://gitlab.com/psmisc/psmisc.git
```

源码路径: `~/tmp/psmisc/`

### 2. 编译准备

- **问题**: psmisc 整包编译失败
- **解决方案**: 单独编译 pstree.c
- **依赖检查**: ncursesw 已安装在 `~/usr/local/`

### 3. 编译命令

```bash
clang -DVERSION="23.7" \
      -o ~/tmp/pstree \
      ~/tmp/psmisc/src/pstree.c \
      -I$HOME/usr/local/include \
      -L$HOME/usr/local/lib \
      -lncursesw
```

**关键点**:
- 手动定义 `VERSION` 宏（通常由 configure 自动生成）
- 使用 `libncursesw.a`（带宽字符支持）
- 包含路径: `-I$HOME/usr/local/include`
- 库路径: `-L$HOME/usr/local/lib`

### 4. 验证

```bash
$ ~/tmp/pstree --version
pstree (PSmisc) 23.7
Copyright (C) 1993-2024 Werner Almesberger and Craig Small
```

编译成功，二进制文件大小: 142KB

### 5. 文件信息

```
-rwxrwx--- 1 user user 142K 2026-04-28 03:50 /storage/Users/currentUser/tmp/pstree
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

## 编译结束

**最终状态**: 成功

## 知识提取

### L3 - 本软件特定知识

1. **单文件编译方案**: psmisc 整包编译失败时，可单独编译 pstree.c
2. **VERSION 宏**: 需要手动定义，从 `git describe --tags` 获取版本号
3. **ncursesw**: 使用 libncursesw.a（带宽字符支持），而非 libncurses.a

### 后续工作

- 可考虑编译其他 psmisc 工具（killall, fuser 等）
- 可研究 psmisc 整包编译失败的原因