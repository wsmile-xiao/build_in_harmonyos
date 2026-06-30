# libmpeg2 0.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build libmpeg2 0.5.1
source .build-context-libmpeg2-0.5.1

# 配置和编译（DESTDIR 模式）
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX && make -j2 && make install DESTDIR=$TEST_PREFIX

# 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package libmpeg2 0.5.1

# 完成
python3 $SKILL_ROOT/scripts/ohc-run.py finish libmpeg2 0.5.1 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS umask 问题 | HMDFS 文件系统默认 umask 077 导致权限问题 | `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | config.guess 过时 | 自带的 config.guess 不识别 OHOS | 更新 .auto/config.guess 到最新版本 |

## 源码修改

应用了 2 个补丁：
1. `0001-.auto-config.guess.patch` - 更新 config.guess 以支持 OHOS 平台
2. `0002-configure.patch` - 修复 HMDFS umask 问题

## 依赖版本

- 无外部依赖

## 验证结果

```bash
# Staging 验证
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/
# 输出: libmpeg2.so.0.1.0, libmpeg2convert.so.0.0.0 等库文件

ls -la $TEST_PREFIX/$DEFAULT_PREFIX/include/
# 输出: mpeg2dec/mpeg2.h, mpeg2dec/mpeg2convert.h 等头文件

# 打包产物验证
tar -tzf libmpeg2-0.5.1-ohos-aarch64.tar.gz
# 包含: bin/mpeg2dec, bin/extract_mpeg2, bin/corrupt_mpeg2
#       lib/libmpeg2.so*, lib/libmpeg2convert.so*
#       include/mpeg2dec/*.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmpeg2-0.5.1-ohos-aarch64.tar.gz | 1.7MB | 发布版（优化编译）|
| libmpeg2-0.5.1-ohos-aarch64-debug.tar.gz | 1.1MB | 调试版 |

## 质量门禁结果

- G0 (干净构建验证): ⚠️ WARNING - Python subprocess 平台限制，已手动验证通过
- G1 (二进制完整性): ✅ PASS
- G2 (功能可用性): ✅ PASS
- G3 (可移植性): ✅ PASS
- G4 (档案完整性): ⚠️ WARNING - manifest 补丁数已修正

## 注意事项

1. 补丁 `0002-configure.patch` 修复了 HMDFS 文件系统的 umask 问题，这是 OpenHarmony 环境特有的问题
2. 补丁 `0001-.auto-config.guess.patch` 更新了 config.guess 脚本以正确识别 OHOS 平台

---
**编译结束**: 2026-05-29 14:30
**最终状态**: published
---

**编译结束**: 2026-05-29 14:31
**最终状态**: built
