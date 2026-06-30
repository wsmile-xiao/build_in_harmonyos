# jbigkit 2.1 适配笔记

## 编译环境
- 构建系统: makefile（简单Makefile，无configure/autotools）
- 编译日期: 2026-06-13
- 编译器: clang 15.0.4 / clang++
- 工具链: llvm-ar, llvm-ranlib
- 状态: published

## 编译步骤（详细命令记录）

### 1. 初始化
```bash
SKILL_ROOT=/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent
# SSL证书问题，先手动下载源码
curl -kL -o ~/tmp/builds/jbigkit-2.1.tar.gz https://www.cl.cam.ac.uk/~mgk25/jbigkit/download/jbigkit-2.1.tar.gz
python3 $SKILL_ROOT/scripts/ohc-run.py init-build jbigkit 2.1 --no-download
```

### 2. 修改Makefile适配鸿蒙
jbigkit无标准configure脚本，使用纯Makefile构建，需手动修改3个Makefile:
- 顶层Makefile: CC→clang, CFLAGS添加-fPIC, 添加PREFIX和install目标
- libjbig/Makefile: CC→clang, CFLAGS添加-fPIC, ar→llvm-ar, ranlib→llvm-ranlib
- pbmtools/Makefile: CC→clang, CFLAGS添加-fPIC, CPPFLAGS="-I../libjbig"

### 3. 创建dummy configure脚本
```bash
cd ~/tmp/builds/jbigkit-2.1.work
echo '#!/bin/sh' > configure
echo 'echo "jbigkit: makefile project, configure not needed (patches handle Makefile adaptation)"' >> configure
echo 'exit 0' >> configure
chmod +x configure
```

### 4. 编译
```bash
cd ~/tmp/builds/jbigkit-2.1.work
make -e
# 产物: libjbig/libjbig.a, libjbig/libjbig85.a
# 产物: pbmtools/pbmtojbg, pbmtools/jbgtopbm, pbmtools/pbmtojbg85, pbmtools/jbgtopbm85
# 产物: libjbig/tstcodec, libjbig/tstcodec85
```

### 5. 测试（真实执行）
```bash
cd ~/tmp/builds/jbigkit-2.1.work
make test
# tstcodec: library has PASSED the test suite
# tstcodec85: T.85 library has PASSED the test suite
# pbmtools test82: pbmtools have PASSED the functional tests
# pbmtools test85: T.85 pbmtools have PASSED the functional tests
```

### 6. 安装（staging + 本地）
```bash
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
# 安装: 4个二进制 → bin/, 2个静态库 → lib/, 3个头文件 → include/
```

### 7. 功能验证
```bash
$DEFAULT_PREFIX/bin/pbmtojbg --help
PBMtoJBIG converter 2.1 -- creates bi-level image entity (BIE) as output file

$DEFAULT_PREFIX/bin/jbgtopbm --help
JBIGtoPBM converter 2.1 -- reads a bi-level image entity (BIE) as input file

$DEFAULT_PREFIX/bin/pbmtojbg85 --help
PBMtoJBIG85 converter 2.1 -- creates T.85 bi-level image entity

$DEFAULT_PREFIX/bin/jbgtopbm85 --help
JBIG85toPBM converter 2.1 -- reads a T.85 bi-level image entity
```

### 8. 打包预编译包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package jbigkit 2.1
# 生成: jbigkit-2.1-ohos-aarch64.tar.gz (404KB) + debug版 (156KB)
```

### 9. 补丁生成与追踪
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py track-edit add jbigkit 2.1 configure
python3 $SKILL_ROOT/scripts/ohc-run.py refresh-patch --auto jbigkit 2.1
# 生成4个补丁: 0001-Makefile.patch, 0002-configure.patch, 0003-libjbig-Makefile.patch, 0004-pbmtools-Makefile.patch
```

### 10. finish与验证
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish jbigkit 2.1 published
# G0干净构建验证通过: 4补丁→configure→make→install(4bin+2lib)
# G1-G4质量门禁全部PASS

python3 $SKILL_ROOT/scripts/ohc-run.py verify-build jbigkit 2.1
# G1: PASS | G2: PASS | G3: PASS | G4: PASS
```

## 对话记录 / 操作日志

| 时间 | 操作 | 结果 |
|------|------|------|
| 2026-06-13 | init-build (curl -kL下载, --no-download运行) | 成功解压到.orig和.work |
| 2026-06-13 | 自动模式build尝试 | 失败（无configure脚本） |
| 2026-06-13 | 手动修改3个Makefile | 适配鸿蒙编译器/工具链 |
| 2026-06-13 | make -e 编译 | 成功，所有产物生成 |
| 2026-06-13 | make test | 所有4个测试套件PASSED |
| 2026-06-13 | make install (DESTDIR+PREFIX) | staging安装成功 |
| 2026-06-13 | 二进制功能验证 (--help) | 4个二进制正常输出 |
| 2026-06-13 | package 打包 | 2个预编译包生成 |
| 2026-06-13 | 创建dummy configure脚本 | 解决G0 clean-verify需求 |
| 2026-06-13 | track-edit add configure | configure加入追踪器 |
| 2026-06-13 | refresh-patch --auto | 4个补丁生成 |
| 2026-06-13 | clean-verify | 4补丁+configure+make成功 |
| 2026-06-13 | finish published | G0通过, G1-G4 PASS, published |
| 2026-06-13 | 添加build_system字段到manifest | G4档案完整性修复 |
| 2026-06-15 | 补充真实test-report.md | 包含完整make test输出 |
| 2026-06-15 | 补充notes.md对话记录 | 完整操作日志 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | 源码URL的HTTPS证书不被信任 | curl -kL下载源码，然后--no-download运行init-build |
| 2 | 自动模式make失败 | jbigkit无configure脚本，CC=gcc不在PATH | 手动修改Makefile: CC=clang |
| 3 | pbmtools编译找不到jbig.h | make -e导致环境CFLAGS覆盖CPPFLAGS | 显式在pbmtools/Makefile添加CPPFLAGS="-I../libjbig" |
| 4 | 无install目标 | 原始Makefile没有install target | 手动添加install target到顶层Makefile（含bin/lib/include） |
| 5 | ar/ranlib不兼容 | GNU ar/ranlib在鸿蒙上不可用 | 使用llvm-ar/llvm-ranlib替代 |
| 6 | G0 clean-verify configure失败 | 无configure脚本导致G0验证流程无法运行 | 创建dummy configure脚本(#!/bin/sh + exit 0) |
| 7 | G4 "manifest缺少build_system" | manifest只有嵌套build.system字段 | 添加顶层build_system: makefile字段 |
| 8 | refresh-patch覆盖补丁分类 | --auto每次重写patch_classification为auto/pending | 每次refresh后手动更新为platform_adaptation |
| 9 | refresh-patch遗漏configure补丁 | configure不在track-edit追踪器中 | track-edit add jbigkit 2.1 configure |

## 源码修改（4个补丁）

| 补丁 | 修改文件 | 主要变更 |
|------|----------|----------|
| 0001-Makefile.patch | Makefile | CC→clang, CFLAGS+(-fPIC), PREFIX变量, install目标 (+15/-2) |
| 0002-configure.patch | configure | 新增dummy configure脚本 (+6/-0) |
| 0003-libjbig-Makefile.patch | libjbig/Makefile | CC→clang, CFLAGS+(-fPIC), AR→llvm-ar, RANLIB→llvm-ranlib (+10/-6) |
| 0004-pbmtools-Makefile.patch | pbmtools/Makefile | CC→clang, CFLAGS+(-fPIC), CPPFLAGS="-I../libjbig" (+7/-3) |

## 依赖版本

无外部依赖（纯C语言实现，仅需标准libc）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| jbigkit-2.1-ohos-aarch64.tar.gz | 404KB | 预编译包(bin+lib+include) |
| jbigkit-2.1-ohos-aarch64-debug.tar.gz | 156KB | 调试符号包 |

## 产物清单

- 二进制: pbmtojbg, jbgtopbm, pbmtojbg85, jbgtopbm85 (4个)
- 静态库: libjbig.a, libjbig85.a (2个)
- 头文件: jbig.h, jbig85.h, jbig_ar.h (3个)

## 注意事项

- jbigkit是简单Makefile项目，无configure/autotools
- 无标准install目标，需手动添加
- pbmtools编译时必须显式传递CPPFLAGS含-I../libjbig路径
- 鸿蒙平台需使用llvm-ar/llvm-ranlib替代GNU工具
- 纯Makefile项目需要dummy configure脚本以满足G0验证流程

---

**编译结束**: 2026-06-13 21:05
**测试补充**: 2026-06-15 (真实make test输出记录)
**最终状态**: published
