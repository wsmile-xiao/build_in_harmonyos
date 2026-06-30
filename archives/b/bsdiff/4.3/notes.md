# bsdiff 4.3 适配笔记

# 鸾蒙 OHOS aarch64 编译记录

## 编译环境
- 构建系统: makefile（BSD 风格）
- 编译日期: 2026-06-08
- 编译器: clang 15.0.4
- 链接器: bfd（通过 -fuse-ld=bfd 指定）
- 平台: 鸿蒙 OHOS aarch64 (HongMeng Kernel 1.12.0)
- 状态: published ✅

## 编译步骤

### 步骤 1: 安装依赖 bzip2

```bash
# bzip2 已有归档，重新下载编译安装
python3 $SKILL_ROOT/scripts/ohc-run.py init-build bzip2 1.0.8
cd ~/tmp/builds/bzip2-1.0.8.work
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib LDFLAGS="-fuse-ld=bfd" -j2
make install PREFIX=$HOME/usr/local
```

### 步骤 2: 初始化 bsdiff 编译环境

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build bsdiff 4.3 \
  --url=https://deb.debian.org/debian/pool/main/b/bsdiff/bsdiff_4.3.orig.tar.gz
```

### 步骤 3: 手动编译（AI 步骤）

bsdiff 使用 BSD 风格的 Makefile，非标准 autotools，需要手动编译：

```bash
cd ~/tmp/builds/bsdiff-4.3.work
clang -O2 -Wall -fPIC -I$HOME/usr/local/include \
  -o bsdiff bsdiff.c -L$HOME/usr/local/lib -lbz2 -fuse-ld=bfd
clang -O2 -Wall -fPIC -I$HOME/usr/local/include \
  -o bspatch bspatch.c -L$HOME/usr/local/lib -lbz2 -fuse-ld=bfd
```

### 步骤 4: 安装到 staging 和系统路径

```bash
mkdir -p $TEST_PREFIX$DEFAULT_PREFIX/{bin,man/man1}
cp bsdiff bspatch $TEST_PREFIX$DEFAULT_PREFIX/bin/
cp bsdiff.1 bspatch.1 $TEST_PREFIX$DEFAULT_PREFIX/man/man1/
cp bsdiff bspatch $DEFAULT_PREFIX/bin/
cp bsdiff.1 bspatch.1 $DEFAULT_PREFIX/man/man1/
```

### 步骤 5: ELF 签名和功能验证

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/bin/bsdiff
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf ~/usr/local/bin/bspatch
```

### 步骤 6: 预编译包制作

```bash
cd $TEST_PREFIX$DEFAULT_PREFIX
tar czvf archives/b/bsdiff/4.3/packaging/bsdiff-4.3-ohos-aarch64.tar.gz bin/ man/
```

### 步骤 7: 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish bsdiff 4.3 built
# 状态更新为 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器 libxml2.so.16 缺失 | OHOS SDK 的 lld 链接器缺少 libxml2 动态库 | 使用 `LDFLAGS="-fuse-ld=bfd"` 切换到 bfd 链接器 |
| 2 | bspatch.c 中 `u_char` 未定义 | BSD 特有类型，鸿蒙/Linux 不支持 | 补丁添加 `typedef unsigned char u_char;` |
| 3 | BSD Makefile `.ifndef` 语法错误 | `.ifndef` 是 BSD Make 特有语法，GNU Make 不支持 | 补丁替换为 `ifdef ... else ... endif` |
| 4 | 编译规则缺失 | BSD Make 依赖隐式规则，GNU Make 需要显式规则 | 补丁添加显式编译命令 |
| 5 | `${INSTALL}` 变量未定义 | Makefile 中 `${INSTALL}` 未初始化 | 补丁改用 `cp -f` 直接复制 |
| 6 | DESTDIR 不支持 | 原始 Makefile 没有 DESTDIR 变量 | 补丁添加 `DESTDIR ?=` 和 `mkdir -p` |
| 7 | LDFLAGS `?=赋值不生效 | `?=` 会被环境变量覆盖 | 改为 `=` 强制赋值 |
| 8 | manifest 缺少 `build_system` 字段 | verify_build.py 检查顶级 `build_system:` | 添加 `build_system: makefile` |
| 9 | ELF 签名缺失 | 鸿蒙要求二进制签名才能执行 | 使用 `sign-elf` 签名后才能测试 |
| 10 | bzip2 依赖未预安装 | bsdiff 需要但环境中未安装 | 先编译安装 bzip2 1.0.8 |

## 源码修改

| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| Makefile | CFLAGS 从 `+=` 改为 `?=`；添加 LDFLAGS=`-fuse-ld=bfd`；添加 DESTDIR 支持；`.ifndef` → `ifdef/else/endif`；显式编译命令；`cp -f` 替代 `${INSTALL}` | 0001-Makefile.patch |
| bspatch.c | 在 `#include` 后添加 `typedef unsigned char u_char;` | 0002-bspatch.c.patch |

## 依赖版本

| 依赖 | 版本 | 类型 | 安装方式 |
|------|------|------|----------|
| bzip2 | 1.0.8 | 链接库（静态） | 手动编译安装到 ~/usr/local |

## 验证结果

### 编译验证

```bash
file ~/usr/local/bin/bsdiff ~/usr/local/bin/bspatch
# bsdiff: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
# bspatch: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

readelf -d bsdiff | grep NEEDED
# NEEDED: libc.so（仅依赖 libc，bzip2 通过静态链接）
```

### 功能测试

```bash
# 文本文件补丁测试
bsdiff orig.txt new.txt patch.bin       # ✅ 退出码 0
bspatch orig.txt recovered.txt patch.bin # ✅ 退出码 0
diff new.txt recovered.txt               # ✅ 无差异

# 二进制文件补丁测试（10KB）
bsdiff bin_orig.bin bin_new.bin bin_patch.bin     # ✅ 退出码 0
bspatch bin_orig.bin bin_recovered.bin bin_patch.bin # ✅ 退出码 0
diff bin_new.bin bin_recovered.bin                 # ✅ 无差异

# 大文件补丁测试（1MB 局部修改）
bsdiff large_orig.bin large_new.bin large_patch.bin     # ✅ 退出码 0
# 补丁仅 160 字节（压缩率 99.98%）
bspatch large_orig.bin large_recovered.bin large_patch.bin # ✅ 退出码 0
diff large_new.bin large_recovered.bin                     # ✅ 无差异

# 错误参数处理
bsdiff              # ✅ 正确输出 usage，退出码 1
bspatch             # ✅ 正确输出 usage，退出码 1
bspatch nonexistent out patch # ✅ 报错 "No such file or directory"，退出码 1
```

### 质量门禁

```
G0 干净构建: ✅ PASS（补丁自包含性验证通过）
G1 二进制完整性: ✅ PASS
G2 功能可用性: ✅ PASS（1 个警告：首次运行需 ELF 签名）
G3 可移植性: ✅ PASS
G4 档案完整性: ✅ PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/bsdiff | 170,120 字节 | 二进制补丁生成工具 |
| bin/bspatch | 165,928 字节 | 二进制补丁应用工具 |
| man/man1/bsdiff.1 | 2,226 字节 | bsdiff 手册页 |
| man/man1/bspatch.1 | 2,038 字节 | bspatch 手册页 |
| bsdiff-4.3-ohos-aarch64.tar.gz | 346,185 字节 | 预编译包 |

## 注意事项

1. bsdiff 是 BSD 风格 Makefile 项目，非标准 autotools，需要 GNU Make 兼容性补丁
2. 必须先安装 bzip2 1.0.8 的静态库和头文件
3. 鸿蒙平台 lld 链接器问题需使用 bfd 替代
4. 二进制需要 ELF 签名才能在鸿蒙上执行
5. LDFLAGS 变量使用 `=` 赋值（而非 `?=`），避免被环境变量覆盖
6. 补丁中 DESTDIR 路径使用 `${DESTDIR}${PREFIX}` 格式

## 知识沉淀

### 平台适配经验（L1）

- **BSD Makefile GNU Make 兼容**: `.ifndef` → `ifdef ... else ... endif`; 需要添加显式编译规则
- **lld 链接器替代**: OHOS SDK 的 lld 链接器缺少 libxml2.so.16，需要使用 `-fuse-ld=bfd`

### 构建模式经验（L2）

- **BSD 特有类型**: `u_char` 在非 BSD 系统需手动 typedef
- **INSTALL 变量替代**: 未定义的 `${INSTALL}` 用 `cp -f` 替代
- **DESTDIR 支持**: BSD Makefile 通常不支持 DESTDIR，需手动添加

### 本版笔记（L3）

- bsdiff 仅依赖 libc.so，bzip2 通过静态链接内嵌
- 补丁文件体积非常小（1MB 文件局部修改 → 160 字节补丁）

---

**编译结束**: 2026-06-08
**最终状态**: published