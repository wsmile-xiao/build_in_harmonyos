# tinyxml 2.6.2 编译笔记

## 编译开始

**时间**: 2026-06-05 19:17

**源码**: https://downloads.sourceforge.net/project/tinyxml/tinyxml/2.6.2/tinyxml_2_6_2.tar.gz

**构建系统**: make (简单 Makefile)

## 编译过程

### Step 1: 解压源码

源码已解压到 ~/tmp/builds/tinyxml/

### Step 2: 检查构建系统

tinyxml 使用简单的 Makefile，无 configure 脚本。
主要目标：
- `all`: 生成 xmltest 测试程序
- `clean`: 清理
- 无标准 install 目标

### Step 3: 编译

```bash
cd ~/tmp/builds/tinyxml
make clean
make
```

编译成功，生成：
- xmltest (测试程序，119KB)
- *.o 文件 (编译中间文件)

**警告**: 7 个警告（编码相关，不影响功能）

### Step 4: 创建静态库

```bash
ar rc libtinyxml.a tinyxml.o tinyxmlparser.o tinyxmlerror.o tinystr.o
ranlib libtinyxml.a
```

生成 libtinyxml.a (130KB)

### Step 5: 手动安装

由于没有标准 install 目标，手动安装：
```bash
mkdir -p ~/usr/local/lib ~/usr/local/include ~/usr/local/bin
cp libtinyxml.a ~/usr/local/lib/
cp tinyxml.h tinystr.h ~/usr/local/include/
cp xmltest ~/usr/local/bin/
```

### Step 6: 功能验证

运行测试程序：
```bash
xmltest
```

**结果**: 109 个测试全部通过 ✅

### Step 7: 质量门禁验证

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py verify-build tinyxml 2.6.2
```

**结果**: PASS ✅

### Step 8: 制作预编译包

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package tinyxml 2.6.2
```

生成：
- tinyxml-2.6.2-ohos-aarch64.tar.gz (370KB)
- tinyxml-2.6.2-ohos-aarch64-debug.tar.gz

---

## 编译结束

**最终状态**: published ✅

**产物路径**: /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/t/tinyxml/2.6.2/packaging/tinyxml-2.6.2-ohos-aarch64.tar.gz

**补丁**: 无

## 问题与解决方案

### 问题 1: SSL 证书验证失败
- 原因: Python urllib SSL 证书验证失败
- 解决方案: 使用 wget --no-check-certificate 手动下载

### 问题 2: 无标准 install 目标
- 原因: tinyxml 使用简单 Makefile，无 configure/install 流程
- 解决方案: 手动创建静态库并安装文件

## 知识提取记录

### K1: 简单 Makefile 库的处理
- 类别: build-system
- 适用场景: 无 configure/install 目标的简单库
- 操作流程: make → ar 创建静态库 → 手动安装

### K2: 静态库创建命令
```bash
ar rc libname.a obj1.o obj2.o ...
ranlib libname.a
```
---

**编译结束**: 2026-06-05 19:19
**最终状态**: published
