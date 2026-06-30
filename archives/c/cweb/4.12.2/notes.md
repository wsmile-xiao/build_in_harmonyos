# cweb 4.12.2 — 编译适配笔记

## 软件信息
- **名称**: cweb (C/C++/Java 文学编程文档系统)
- **版本**: 4.12.2
- **构建系统**: 简单 Makefile（非 autotools）
- **License**: Knuth-CTAN
- **源码 URL**: https://github.com/ascherer/cweb/archive/refs/tags/cweb-4.12.2.tar.gz
- **SHA256**: 519ac1c03610eea18956ed62d2996dc5a629f0c3af91f38cf4621d5deab749fd

## 编译过程

### 1. 初始化

```
python3 $SKILL_ROOT/scripts/ohc-run.py init-build cweb 4.12.2 \
  --url=https://github.com/ascherer/cweb/archive/refs/tags/cweb-4.12.2.tar.gz
```

结果：init-build 成功，源码下载和解压正常，构建系统识别为 makefile。

### 2. 编译关键问题

#### 问题 1: ELF 签名（Permission denied）

- **现象**: `./ctangle: Permission denied` — make 过程中执行 `./ctangle cweave` 失败
- **原因**: 鸿蒙系统要求 ELF adhoc self-signing 后才能执行新编译的二进制文件
- **解决**: 编译 ctangle 后，使用 `ohc-run.py sign-elf ./ctangle` 签名，再继续编译 cweave
- **知识图谱**: E106（bootstrap 程序需 ELF 签名）

#### 问题 2: 链接器 lld 的 libxml2 依赖错误

- **现象**: 链接时报错
  ```
  Error loading shared library libxml2.so.16: (needed by .../lld)
  Error relocating .../lld: xmlFreeDoc: symbol not found
  clang-15: error: linker command failed due to signal
  ```
- **原因**: OHOS SDK 的 lld 链接器依赖 libxml2.so.16，但该库在 OHOS 上不可用
- **解决**: 使用 GNU ld 替代 lld：`LINKFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd -O2"`
- **知识图谱**: E105（OHOS SDK lld 的 libxml2 依赖问题）

#### 问题 3: DESTDIR 变量名冲突

- **现象**: cweb Makefile 的 `DESTDIR= /usr/local/bin/`（可执行文件目录），与标准 staging DESTDIR 冲突
- **原因**: cweb Makefile 使用 DESTDIR 表示可执行文件目录，而非 staging 根路径
- **解决**: 创建补丁 0001-Makefile.patch：
  - 将 DESTDIR 改名为 BINDIR（`BINDIR= $(PREFIX)/bin`）
  - 新增 PREFIX 变量（`PREFIX?= /usr/local`）
  - 新增标准 DESTDIR 变量（`DESTDIR?= `，用于 staging 根路径）
  - 所有安装路径（MANDIR、MACROSDIR、EMACSDIR、CWEBINPUTS）基于 PREFIX
  - install 目标改为 `mkdir -p` + `$(DESTDIR)$(BINDIR)/$(DESTPREF)tangle` 格式
  - CFLAGS/LINKFLAGS 使用 `?= 覆盖语法`（支持命令行覆盖）
  - MANEXT 从 `l` 改为 `1`（标准 man 页编号）

### 3. 编译命令（实际执行）

```bash
source .build-context-cweb-4.12.2
cd $BUILD_SRC_DIR
# 第一阶段：编译 ctangle
make ctangle PREFIX=$DEFAULT_PREFIX CC=clang
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ./ctangle
# 第二阶段：ctangle 生成 cweave.c，编译 cweave
make cweave PREFIX=$DEFAULT_PREFIX CC=clang
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ./cweave
# DESTDIR staging 安装
make install PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX CC=clang
```

### 4. 测试验证

- `make cautiously` 通过（ctangle 能自复制 common.c 和 ctangle.c，diff 无差异）
- ctangle 功能测试通过：`ctangle wc` 正确生成 wc.c（215行）
- cweave 功能测试通过：`cweave wc` 正确生成 wc.tex（342行）
- 用户安装验证通过：`$PREFIX/bin/ctangle` 和 `$PREFIX/bin/cweave` 均可正常执行

### 5. 打包与安装

- 预编译包: `cweb-4.12.2-ohos-aarch64.tar.gz` (286KB)
- 预编译包内容: bin/cweave, bin/ctangle, lib/cweb/ 下的 2 个 .w 文件, share/ 下的 4 个文件
- 无外部依赖库

---

**编译结束**: 2026-06-09
**最终状态**: published