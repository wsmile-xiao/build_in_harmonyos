# libdshconfig 0.20.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `autoreconf -fi` — 重新生成 configure（原始 configure 基于 autoconf 2.61，config.guess 太旧不识别 HarmonyOS）
2. 复制系统 config.guess/config.sub（automake-1.17 版本，识别 aarch64-unknown-linux-ohos）
3. `./configure --prefix=$DEFAULT_PREFIX`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make check` — 3/3 测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 (2007-03-06 版本) | 原始 configure 使用的 config.guess 太旧 | autoreconf -fi 重新生成 + 复制 automake-1.17 的 config.guess/config.sub |
| 2 | config.status 创建临时文件失败 "Permission denied" | autoconf 使用 `umask 077` 创建临时目录，HMDFS 文件系统不允许在权限为 700 的目录内创建文件 | sed 替换 config.status 中的 `umask 077` 为 `umask 022` |

## 源码修改

- config.guess/config.sub: 替换为 automake-1.17 版本（平台识别）
- config.status: `umask 077` → `umask 022`（HMDFS 兼容性修复）
- 以上均为探索阶段临时修改，通过 autoreconf -fi 重新生成构建系统

## 依赖版本

无依赖

## 验证结果

```
make check 结果:
PASS: tests/test-basic.sh
PASS: tests/test-dshconfig-searchdata.sh
PASS: tests/test-longline.sh
# TOTAL: 3  # PASS: 3  # SKIP: 0  # FAIL: 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libdshconfig.so.1.0.0 | 共享库 |
| lib/libdshconfig.a | 静态库 |
| include/libdshconfig.h | 头文件 |

## 注意事项

- HMDFS 文件系统不支持 `umask 077` 创建的目录内写文件，需改为 `umask 022`
- 原始 configure 基于 autoconf 2.61，需 autoreconf 重新生成
- 无 bin/ 目录，纯库软件
---

**编译结束**: 2026-06-26 22:10
**最终状态**: published
