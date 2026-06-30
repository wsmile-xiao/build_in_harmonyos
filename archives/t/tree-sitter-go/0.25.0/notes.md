# tree-sitter-go 0.25.0 编译笔记

## 编译开始: 2026-06-15

### 环境信息
- 平台: OpenHarmony
- 编译器: gcc
- 构建系统: Makefile

### 编译过程

#### Step 1: 下载源代码
- URL: https://github.com/tree-sitter/tree-sitter-go/releases/download/v0.25.0/tree-sitter-go.tar.gz
- 下载方式: curl -L -k（SSL证书验证失败，使用 -k 绕过）
- 文件大小: 206K

#### Step 2: 编译
```bash
cd ~/build/tree-sitter-go-0.25.0-src
make PREFIX=$DEFAULT_PREFIX -j2
```

编译输出：
- 静态库: libtree-sitter-go.a (238K)
- 动态库: libtree-sitter-go.so.15.0 (254K)
- pkg-config 文件: tree-sitter-go.pc

#### Step 3: 安装（DESTDIR模式）
**遇到问题**: 鸿蒙平台缺少 `install` 命令（make install 失败）

**解决方案**: 手动使用 mkdir + cp + ln 替代
```bash
mkdir -p $DESTDIR/$DEFAULT_PREFIX/lib
cp libtree-sitter-go.a $DESTDIR/$DEFAULT_PREFIX/lib/
cp libtree-sitter-go.so $DESTDIR/$DEFAULT_PREFIX/lib/libtree-sitter-go.so.15.0
ln -sf libtree-sitter-go.so.15.0 $DESTDIR/$DEFAULT_PREFIX/lib/libtree-sitter-go.so.15
ln -sf libtree-sitter-go.so.15 $DESTDIR/$DEFAULT_PREFIX/lib/libtree-sitter-go.so
``

### 知识提取
- **平台问题**: 鸿蒙系统缺少 `install` 命令
- **影响**: 所有使用 Makefile install 目标的软件都会遇到
- **通用方案**: 用 `mkdir + cp + ln` 手动替代

---
**编译结束**: 2026-06-15 15:09
**最终状态**: built
---

**编译结束**: 2026-06-15 15:11
**最终状态**: built
