# m17n-lib 1.8.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### 初次尝试（失败）
1. configure --prefix=/storage/Users/currentUser/usr/local --with-included-gettext
2. 修改 example/Makefile: LDFLAGS = -Wl,--allow-shlib-undefined
3. make -j1
4. 运行时验证失败：libintl_dgettext: symbol not found

### 成功方案：静态链接 libintl.a
1. configure --prefix=/storage/Users/currentUser/usr/local --with-included-gettext
2. **修改 src/Makefile**：
   - 添加 `libm17n_core_la_LIBADD += $(top_builddir)/intl/libintl.a`
   - 添加 `libm17n_core_la_DEPENDENCIES = $(top_builddir)/intl/libintl.a`
3. make -C src clean && make -C src -j1
4. make install
5. 运行时验证成功 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 时 LDFLAGS="-lintl" 导致编译器测试失败 | LDFLAGS 传递到编译器测试阶段导致找不到库 | 使用 --with-included-gettext 内嵌 libintl |
| 2 | 链接时 undefined reference: libintl_dgettext | HarmonyOS libintl.so.8.proxy 使用符号重命名 (g_libintl_dgettext) | 添加 -Wl,--allow-shlib-undefined 绕过链接验证 |
| 3 | **运行时 libintl_dgettext: symbol not found** | **libintl.so.8.proxy 与标准 libintl 符号不兼容** | **✅ 静态链接 libintl.a 到 libm17n-core.so** |

## 源码修改

- **src/Makefile**: 添加 libintl.a 静态链接到 libm17n_core_la_LIBADD 和 DEPENDENCIES

## 依赖版本

- libxml2: 2.x

## 验证结果

```bash
# 编译成功
make: 无错误退出

# 运行时验证 ✅
$ /storage/Users/currentUser/usr/local/bin/m17n-conv --version
m17n-conv (m17n library) 1.8.6
Copyright (C) 2003-2011 AIST, JAPAN

# 符号验证 ✅
$ nm /storage/Users/currentUser/usr/local/lib/libm17n-core.so.0.4.2 | grep libintl_dgettext
00000000000233dc T libintl_dgettext

# 动态依赖验证 ✅（无 libintl.so）
$ readelf -d /storage/Users/currentUser/usr/local/lib/libm17n-core.so.0.4.2
  (NEEDED)  Shared library: [libxml2.so]
  (NEEDED)  Shared library: [libc.so]
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libm17n-core.so.0.4.2 | 477KB | 核心库（已静态链接 libintl.a） ✅ |
| libm17n.so | - | 主库 |
| libm17n-flt.so | 109KB | FLT库 |
| libm17n-gui.so | 342KB | GUI库 |

## 关键解决方案总结

✅ **问题解决**：通过静态链接 intl/libintl.a 到 libm17n-core.so，成功绕过 HarmonyOS 的 libintl.so.8.proxy 符号重命名机制。

**修改位置**：
- `src/Makefile` 第 580-582 行
- 添加 LIBADD 和 DEPENDENCIES

**技术原理**：
- libintl.a 中包含标准 gettext 符号（libintl_dgettext 等）
- 静态链接后符号编译进 .so，运行时不再依赖 libintl.so
- 避免了 libintl.so.8.proxy 的符号重命名问题

---
**编译结束**: 2026-06-03 10:32
**最终状态**: built
**修复状态**: ✅ 运行时验证成功
---

**编译结束**: 2026-06-03 10:49
**最终状态**: built
