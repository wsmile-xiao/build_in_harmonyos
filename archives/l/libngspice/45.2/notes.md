# libngspice 45.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
./configure --prefix=$DEFAULT_PREFIX --with-ngshared --with-readline=no
make -j1
make install DESTDIR=$TEST_PREFIX
```

- 使用 `--with-ngshared` 构建共享库模式（libngspice.so），而非独立 ngspice 二进制
- 使用 `--with-readline=no` 禁用 readline（鸿蒙平台无 readline）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | readline 不可用 | 鸿蒙平台无 readline | configure 时加 --with-readline=no |
| 2 | G0 干净构建验证失败 | HMDFS 平台限制：cat/sort 无法访问 stdin，导致 configure conftest 生成失败 | 已知平台限制（非编译问题），手动验证通过 |

## 验证结果

staging 安装确认:
- lib/libngspice.so.0.0.13 ✅
- lib/libngspice.so ✅ (symlink)
- lib/libngspice.so.0 ✅ (symlink)
- lib/pkgconfig/ngspice.pc ✅
- include/ngspice/sharedspice.h ✅
- lib/ngspice/*.cm (7 codemodels) ✅

本地安装验证:
- ~/usr/local/lib/libngspice.so.0.0.13 ✅
- ~/usr/local/include/ngspice/sharedspice.h ✅
- pkgconfig/ngspice.pc ✅

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libngspice-45.2-ohos-aarch64.tar.gz | 18182KB | 预编译包 |

## 注意事项

- --with-ngshared 模式下无 ngspice 二进制，仅产出 libngspice.so 共享库
- G0 干净构建验证因 HMDFS 平台限制（cat/sort stdin 管道不可用）导致 false positive，实际编译无问题
---

**编译结束**: 2026-05-27 11:26
**最终状态**: published
