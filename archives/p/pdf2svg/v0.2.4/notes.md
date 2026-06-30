# pdf2svg v0.2.4 编译笔记

## 编译日期
2026-05-25

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang
- 构建系统: makefile（手动 Makefile）

## 依赖
- poppler 25.11.0 ✅ (含 poppler-glib)
- cairo 1.18.4 ✅
- glib2 2.84.0 ✅

## 问题与解决

### 问题1: 无 configure 脚本，需要手动编译
**原因**: pdf2svg 使用简单的 Makefile 构建系统，不包含 configure 脚本。

**解决**: 手动创建 config.h 和 Makefile 补丁，包含 OHOS SDK 头文件路径和库路径。

### 问题2: config.guess/config.sub 缺少 OHOS 支持
**原因**: 项目附带的 config.guess/config.sub 不识别 HarmonyOS。

**解决**: 添加 HarmonyOS 平台检测补丁（E007）。

### 问题3: 依赖库头文件和库路径
**原因**: 需要手动指定 poppler-glib、cairo、glib2 等库的头文件和库路径。

**解决**: 在 Makefile 补丁中添加完整的 -I 和 -L 路径。

## 编译步骤

```bash
# init
python3 $SKILL_ROOT/scripts/ohc-run.py init-build pdf2svg v0.2.4

# 应用补丁（config.h + Makefile + config.guess/config.sub）
# 手动创建 config.h 和 Makefile

# make
make

# install
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp pdf2svg $TEST_PREFIX/$DEFAULT_PREFIX/bin/

# package
python3 $SKILL_ROOT/scripts/ohc-run.py package pdf2svg v0.2.4
python3 $SKILL_ROOT/scripts/ohc-run.py package pdf2svg v0.2.4 --debug
```

## 补丁文件
- 0001-config.guess.patch: 添加 HarmonyOS 系统检测
- 0002-config.sub.patch: 添加 ohos triplet 支持
- 0003-config.h.patch: 手动创建 config.h，定义 PACKAGE/VERSION 等宏
- 0004-Makefile.patch: 手动创建 Makefile，包含 OHOS SDK 和依赖库路径

## 验证结果
- ✅ pdf2svg --version 正常

**编译结束**: 2026-05-25
**最终状态**: built