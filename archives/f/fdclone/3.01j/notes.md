# fdclone 3.01j 适配笔记

## 编译环境
- 构建系统: makefile（自定义构建系统，非标准 autotools）
- 编译日期: 2026-06-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

fdclone 使用自定义的 Makefile 系统，不需要 configure 步骤：

1. 下载源码并解压
2. 应用补丁（硬链接改为软链接）
3. 直接运行 make（会自动生成 Makefile.tmp）
4. 使用 make install 安装

关键命令：
```bash
# 编译
make PREFIX=/storage/Users/currentUser/usr/local \
     BUILD=/storage/Users/currentUser/tmp/test-install-fdclone-3.01j \
     CC=clang \
     CFLAGS="-I/storage/Users/currentUser/usr/local/include -fPIC -O2" \
     LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"

# 安装到 staging 目录
make install PREFIX=/storage/Users/currentUser/usr/local \
     BUILD=/storage/Users/currentUser/tmp/test-install-fdclone-3.01j

# 安装到本地（用于验证）
make install PREFIX=/storage/Users/currentUser/usr/local
```

BUILD 变量相当于 DESTDIR，用于 staging 安装。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 找不到 ncurses 库 | 库路径不在默认搜索路径 | 添加 LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" |
| 2 | 硬链接失败 | HMDFS 不支持硬链接 | 修改 Makefile.in，将 `$(LN)` 改为 `$(LN) -s` |

## 源码修改

### 0001-Makefile.in.patch

将安装时的硬链接改为软链接，解决 HMDFS 文件系统限制：

```diff
--- a/Makefile.in.orig
+++ b/Makefile.in
@@ -XXX,XX +XXX,XX @@
 install-bin:
-	$(LN) $$FD_BIN$$TARGET
+	$(LN) -s $$FD_BIN$$TARGET

 install-man:
-	$(LN) $$FD_MAN$$TARGET
+	$(LN) -s $$FD_MAN$$TARGET

 install-jman:
-	$(LN) $$FD_JMAN$$TARGET
+	$(LN) -s $$FD_JMAN$$TARGET
```

具体修改：
- install-bin: `$(LN)` → `$(LN) -s`（fd → fdsh）
- install-man: `$(LN)` → `$(LN) -s`（fd.1 → fdsh.1）
- install-jman: `$(LN)` → `$(LN) -s`（fd.1 → fdsh.1）

## 依赖版本

- ncurses/6.4 (libncursesw.a) - 静态库，已安装在 ~/usr/local/lib

## 验证结果

### 本地安装验证

```bash
# 文件完整性检查
ls -lh /storage/Users/currentUser/usr/local/bin/fd*
-rwxrwx--- 1 fd (主二进制)
lrwxrwx--- 1 fdsh -> fd (软链接)
-rwxrwx--- 1 fd-unicd.tbl
-rwxrwx--- 1 fd-dict.tbl
-rwxrwx--- 1 fd-cat.ja
-rwxrwx--- 1 fd-cat.C

# 版本检查（需要终端环境）
/storage/Users/currentUser/usr/local/bin/fd --version
# 输出: ioctl(): Permission denied
# 说明: fdclone 需要终端环境运行

# ELF 签名验证
readelf -h /storage/Users/currentUser/usr/local/bin/fd
# ELF64, AArch64, DYN (Position-Independent Executable)

# 依赖库检查
ldd /storage/Users/currentUser/usr/local/bin/fd
# libncursesw.so => /storage/Users/currentUser/usr/local/lib/libncursesw.so
# libc.so => /system/lib/ld-musl-aarch64.so.1
```

## 归档文件清单

### 目录结构

```
archives/f/fdclone/
├── README.md                          # 软件级说明文档
└── 3.01j/
    ├── manifest.yaml                  # 版本级元数据
    ├── notes.md                       # 本文件（适配笔记）
    ├── patches/
    │   └── 0001-Makefile.in.patch    # 硬链接改软链接补丁
    ├── packaging/
    │   ├── fdclone-3.01j-ohos-aarch64.tar.gz       # 发布包 (2.4M)
    │   └── fdclone-3.01j-ohos-aarch64-debug.tar.gz # 调试包 (50K)
    └── reports/
        ├── quality-report.md          # 质量门禁报告
        └── test-report.md              # 测试报告
```

### 预编译包内容

发布包 `fdclone-3.01j-ohos-aarch64.tar.gz` (2.4M) 包含：

**bin/ 目录**：
- `fd` - 主可执行文件
- `fdsh` - fdsh 软链接（指向 fd）
- `fd-unicd.tbl` - Unicode 表文件
- `fd-dict.tbl` - 字典表文件
- `fd-cat.ja` - 日语目录文件
- `fd-cat.C` - 英文目录文件

**lib/ 目录**：
- `lib/external/` - 外部库目录

**man/ 目录**：
- `man/man1/fd.1` - 日语 man 页
- `man/man1/fdsh.1` - 日语 man 页
- `man/en/man1/fd.1` - 英文 man 页
- `man/en/man1/fdsh.1` - 英文 man 页

## 补丁详细信息

### 0001-Makefile.in.patch

**文件位置**: `archives/f/fdclone/3.01j/patches/0001-Makefile.in.patch`

**补丁大小**: 2KB

**生成方式**: per-file-difflib

**源码路径**:
- 原始目录: `/storage/Users/currentUser/tmp/builds/fdclone-3.01j.orig`
- 工作目录: `/storage/Users/currentUser/tmp/builds/fdclone-3.01j.work`

**补丁类型**: 平台适配补丁（platform_only: True）

**守卫状态**: pending（待添加 `#ifdef __OHOS__` 守卫）

**修改说明**:
将 Makefile.in 中所有硬链接命令改为软链接命令，解决 HMDFS 文件系统不支持硬链接的限制。

## 质量门禁结果

运行 `ohc-run.py verify-build fdclone 3.01j` 结果：

- **G1 二进制完整性**: ✅ PASS
- **G2 功能可用性**: ⚠️ PASS (1 警告 - 需要终端环境)
- **G3 可移植性**: ✅ PASS
- **G4 档案完整性**: ✅ PASS

**最终质量报告**: PASS

详细报告见: `reports/quality-report.md` 和 `reports/test-report.md`

## 注意事项

1. **构建系统特殊性**: fdclone 使用自定义构建系统，没有标准的 configure 步骤
2. **G0 验证不适用**: 无 configure 脚本，无法执行标准 G0 干净构建验证
3. **功能验证限制**: fdclone 是终端文件管理器，在无终端环境中无法完全验证功能
4. **ELF 签名要求**: 必须使用 ELF 签名工具签名后才能在鸿蒙系统执行
5. **终端环境依赖**: 用户需要在终端环境中运行 `fd` 命令启动文件管理器

## 编译知识沉淀

1. **fdclone 使用自定义 Makefile 系统，不需要 configure**
   - 直接运行 make 即可编译
   - 使用 PREFIX 变量指定安装路径
   - 使用 BUILD 变量作为 DESTDIR 的替代

2. **HMDFS 不支持硬链接，需将 $(LN) 改为 $(LN) -s**
   - 硬链接在 HMDFS 上会失败
   - 软链接可正常工作
   - 需要修改 Makefile.in 中的安装目标

3. **使用 BUILD 变量作为 DESTDIR 的替代**
   - fdclone 不支持标准的 DESTDIR
   - BUILD 变量用于 staging 安装
   - 安装路径: $BUILD/$PREFIX/bin/

---
**编译结束**: 2026-06-06 15:43
**最终状态**: published