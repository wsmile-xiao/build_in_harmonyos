# erfa 2.0.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

ERFA 同时支持 autotools 和 meson 两种构建系统。autotools 在鸿蒙 HMDFS 上失败，改用 meson 构建。

```bash
cd /storage/Users/currentUser/tmp/builds/erfa-2.0.1.work
meson setup builddir --prefix=$HOME/.local --default-library=static
ninja -C builddir -j4
meson test -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools config.status 失败 (E081) | HMDFS 限制：源码目录下创建临时子目录 confXXXXXX/subs1.awk 时 Permission denied | 改用 meson 构建系统，meson 不在源码目录创建临时文件 |
| 2 | eraVersion() 函数找不到 | eraVersion() 声明在 erfaextra.h 而非 erfa.h | 测试代码需同时 #include <erfa.h> 和 <erfaextra.h> |

## 源码修改

无补丁。meson 构建系统在鸿蒙上开箱即用，无需修改源码。

## 依赖版本

无外部依赖。ERFA 是纯 C 库，仅依赖系统提供的 libm。

## 验证结果

```bash
$ meson test -C builddir
ninja: Entering directory `builddir'
ninja: no work to do.
1/2 t_erfa_c       OK 0.06s
2/2 t_erfa_c_extra OK 0.04s
Ok:                 2
Expected Fail:      0
Fail:               0
Unexpected Pass:    0
Skipped:            0
Timeout:            0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| builddir/src/liberfa.a | 1673660 bytes | 静态库 |

## 注意事项

- autotools 在 HMDFS 上不可用（E081），必须使用 meson 构建
- eraVersion()、eraVersionMajor/Minor/Micro 等版本函数声明在 erfaextra.h，不在 erfa.h
- ERFA 许可证为 BSD-3-Clause（3-clause BSD），非 GPL。ERFA 虽然基于 SOFA 库，但 SOFA 许可证条款允许 ERFA 以 BSD-3-Clause 重新发布
---

**编译结束**: 2026-08-21 09:51
**最终状态**: built
