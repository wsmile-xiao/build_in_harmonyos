# libvirt-glib 5.0.0 适配笔记

## 编译环境
- 构建系统: meson + ninja
- 编译日期: 2026-05-25
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: **failed**

## 编译步骤

1. 下载源码
   ```bash
   # 源码已存在: libvirt-glib-5.0.0.tar.gz
   # SHA256: b7ffc65e1e0ed014b5e5bcfbb9574cd56d103eeed974b6229dbf8c62975d16b5
   ```

2. 解压源码
   ```bash
   cd ~/builds
   tar -xf libvirt-glib-5.0.0.tar.gz
   mv libvirt-glib-5.0.0 libvirt-glib-5.0.0.orig
   cp -a libvirt-glib-5.0.0.orig libvirt-glib-5.0.0.work
   ```

3. Meson 配置
   ```bash
   cd libvirt-glib-5.0.0.work
   meson setup builddir -Dprefix=/storage/Users/currentUser/usr/local
   # 配置成功，39 个构建目标
   ```

4. Ninja 编译
   ```bash
   cd builddir
   ninja -j1
   # 编译失败于第 1/125 步
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libxml2 头文件找不到 | `/storage/Users/currentUser/usr/local/include/libxml2/libxml/tree.h` 引用 `libxml/xmlversion.h`，但编译器 include 路径配置问题 | **待解决** - 需检查 libxml2 安装路径或 CFLAGS |
| 2 | 源码无修改 | 编译在第一步就失败，无需源码修改 | 记录为失败状态 |

### 详细错误信息

```
FAILED: libvirt-gconfig/libvirt-gconfig-1.0.so.0.5000.0.p/meson-generated_.._libvirt-gconfig-enum-types.c.o

/storage/Users/currentUser/usr/local/include/libxml2/libxml/tree.h:17:10: fatal error: 'libxml/xmlversion.h' file not found
#include <libxml/xmlversion.h>
         ^~~~~~~~~~~~~~~~~~~~~
1 error generated.
```

**分析**：
- libxml2 头文件安装在 `/storage/Users/currentUser/usr/local/include/libxml2/libxml/`
- meson 的 include 路径包含了 `-I/storage/Users/currentUser/usr/local/include/libxml2`
- 但源码中使用 `#include <libxml/xmlversion.h>`（相对于 libxml2 目录）
- 正确路径应该是 `-I/storage/Users/currentUser/usr/local/include/libxml2/libxml`

## 依赖版本

- glib-2.0: 2.88.0
- libvirt: 10.1.0
- libxml-2.0: 2.11.9
- pcre2: 10.47
- libffi: 3.4.4

## 验证结果

编译失败，无产物可供验证。

**部分编译产物**：
- `libvirt-glib-1.0.so.0.5000.0` - 编译成功（2.7MB）
- `libvirt-gconfig-1.0.so.0.5000.0` - 编译失败
- `libvirt-gobject-1.0.so.0.5000.0` - 编译失败

## 注意事项

1. **libxml2 头文件路径问题**：需要在后续编译时调整 include 路径
2. **预编译风险**：源码中硬编码 `/tmp` 路径（测试代码），不影响编译但需注意运行时问题
3. **依赖顺序**：必须先成功编译 libvirt 才能编译 libvirt-glib
---

**编译结束**: 2026-05-26 11:26
**最终状态**: built
