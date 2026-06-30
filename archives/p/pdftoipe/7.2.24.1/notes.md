# pdftoipe latest 编译笔记

## 编译日期
2026-05-26

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang
- 构建系统: makefile

## 依赖
- poppler 25.11.0 ✅

## 问题与解决

### 问题1: Makefile 需要适配 OHOS 编译路径
**原因**: pdftoipe 的 Makefile 默认使用 Linux 系统路径，需要适配 OHOS SDK 路径和依赖库路径。

**解决**: 修改 Makefile 中的编译器路径、头文件搜索路径和库搜索路径。

## 编译步骤

```bash
# init
python3 $SKILL_ROOT/scripts/ohc-run.py init-build pdftoipe 7.2.24.1

# 修改 Makefile 适配 OHOS 编译环境

# make
make

# install
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp pdftoipe $TEST_PREFIX/$DEFAULT_PREFIX/bin/

# package
python3 $SKILL_ROOT/scripts/ohc-run.py package pdftoipe 7.2.24.1
python3 $SKILL_ROOT/scripts/ohc-run.py package pdftoipe 7.2.24.1 --debug
```

## 补丁文件
- 1 个补丁：Makefile 适配补丁

## 验证结果
- ✅ pdftoipe 可正常执行

**编译结束**: 2026-05-26
**最终状态**: built