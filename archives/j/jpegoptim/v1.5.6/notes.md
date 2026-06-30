# jpegoptim v1.5.6 编译笔记

## 编译日期
2026-05-25

## 编译环境
- 系统: HarmonyOS (HongMeng Kernel 1.12.0)
- 编译器: clang
- 构建系统: autotools

## 依赖
- libjpeg-turbo 3.1.4.1 ✅

## 问题与解决

### 问题1: config.guess 无法识别 OHOS 平台
**原因**: config.guess 缺少 HarmonyOS 系统检测，导致 configure 无法确定平台类型。

**解决**: 添加 HarmonyOS 系统识别补丁（E007），在 config.guess 中添加 `*:HarmonyOS:*:*` case 分支，输出 `aarch64-unknown-linux-ohos`。

### 问题2: config.sub 不支持 ohos triplet
**原因**: config.sub 不识别 `ohos-linux` 操作系统标识。

**解决**: 在 config.sub 中添加 `ohos-linux` 和 `ohos*` 支持（E007）。

## 编译步骤

```bash
# init
python3 $SKILL_ROOT/scripts/ohc-run.py init-build jpegoptim v1.5.6

# 补丁
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl tools/config.guess tools/config.sub

# configure
./configure --prefix=$DEFAULT_PREFIX

# make
make -j2

# install (DESTDIR staging)
make install DESTDIR=$TEST_PREFIX

# package
python3 $SKILL_ROOT/scripts/ohc-run.py package jpegoptim v1.5.6
python3 $SKILL_ROOT/scripts/ohc-run.py package jpegoptim v1.5.6 --debug
```

## 补丁文件
- 0001-config.guess-ohos.patch: 添加 HarmonyOS 系统检测
- 0002-config.sub-ohos.patch: 添加 ohos triplet 支持

## 验证结果
- ✅ jpegoptim --version 正常输出

**编译结束**: 2026-05-25
**最终状态**: built