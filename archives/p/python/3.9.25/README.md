# Python 3.9.25 HarmonyOS 编译补丁集

## 概述

CPython 3.9.25（3.9 系列最终版本）适配 HarmonyOS PC 的补丁集，共 39 个补丁。

基于 [3.9.0 补丁集](../3.9.0/) 升级，覆盖 3.9.0→3.9.25 之间的源码差异。

## 标准构建流程（固定，不可变更）

```bash
cd Python-3.9.25-patched   # 已打补丁的源码目录

# 1. autoconf
autoconf

# 2. configure（参数固定，不可增减）
./configure --prefix=$HOME/usr/local --disable-ipv6 --enable-shared \
    ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no --enable-optimizations

# 3. 编译
make

# 4. 安装
make install

# 5. 测试
make test
```

## 补丁分类

| 范围 | 编号 | 数量 | 说明 |
|------|------|------|------|
| 构建系统 | 0001-0005 | 5 | configure.ac, config.guess/sub, Makefile.pre.in, setup.py |
| 子进程兼容层 | 0006-0011 | 6 | distutils, sysconfig, _harmonyos_compat, site.py, bootsubprocess, subprocess |
| 运行时修复 | 0012-0027 | 16 | threading, multiprocessing, posix, ctypes, venv, tempfile, uuid, shutil, compileall, spawn |
| 测试修复 | 0028-0039 | 12 | test 适配 HarmonyOS 环境差异 |

## 与 3.9.0 补丁的差异

### 新增补丁
- **0027-distutils-spawn-selinux-bypass.patch**: 3.9.25 特有。当前 SELinux 策略下 `python3.9`（adhoc_bin 域）无法 fork/exec SDK 二进制，通过 `HARMONYOS_BUILD_SCRIPT` 环境变量将编译命令导出到脚本文件，由 shell（hishell_hap 域）执行

### 合并/拆分
- 3.9.0 的 `0016-subprocess.py` 补丁（431行，综合修复）在 3.9.25 中拆分为 0010（bootsubprocess）和 0011（subprocess），因为 3.9.25 源码已有部分改进
- 3.9.0 的部分行内修复（如 P1-2 shutil sendfile、P0-4 pylifecycle fd 验证）在 3.9.25 上游已修复，无需补丁

### Makefile.pre.in 差异
- 3.9.25 的 `commoninstall` 目标新增了更多 `$(LN) -s`（python3, python3-config, .pc 等），补丁 0004 覆盖了所有链接替换（包括 3.9.0 遗漏的部分）

## 扩展模块编译

3.9.25 的扩展模块编译需要 SELinux bypass（见补丁 0027）：

```bash
# 生成 sysconfigdata
echo "none" > pybuilddir.txt
LD_LIBRARY_PATH=. ./python3.9 -S -m sysconfig --generate-posix-vars

# Phase 1: 导出构建命令到脚本（不实际执行）
export HARMONYOS_BUILD_SCRIPT=$HOME/tmp/build_ext.sh
rm -f $HARMONYOS_BUILD_SCRIPT
LD_LIBRARY_PATH=. ./python3.9 ./setup.py build

# Phase 2: 从 shell 执行构建脚本
/bin/sh $HARMONYOS_BUILD_SCRIPT
```

## 上游可行性

大部分补丁可直接或经重构后提交 PR，详见 `manifest.yaml`。
