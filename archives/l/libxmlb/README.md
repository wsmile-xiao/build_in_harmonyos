# libxmlb

## 简介
libxmlb 是一个高效的 XML 二进制 blob 查询库，主要用于 fwupd 等项目的快速 XML 解析。它将 XML 文件编译成二进制格式，提供极速查询能力。

## OHOS 适配要点

### 静态库链接问题
- **问题**：glib 预编译包使用静态库（libintl.a），但 meson 链接了动态库（libintl.so），导致 `undefined symbol: g_libintl_gettext` 等错误
- **解决**：修改 build.ninja 文件，将 `libintl.so` 替换为 `libintl.a`
- **知识图谱**：E081-draft-8726

### 构建配置
- **禁用 introspection**：`-Dintrospection=false`（缺少 gobject-introspection-1.0）
- **禁用 gtkdoc**：`-Dgtkdoc=false`（缺少 gtkdoc-scan 工具）

### 测试问题
- **问题**：测试程序 xb-self-test 运行时找不到 libffi.so.8 和 libxmlb.so.2
- **原因**：运行时环境配置问题（非编译问题）
- **影响**：不影响库的实际功能，状态降级为 built

## 依赖
- **glib/2.88.0**：包含 gio-2.0, glib-2.0, gobject-2.0 等模块

## 功能验证
```bash
pkg-config --modversion xmlb
# 输出: 0.3.19

xb-tool --version
# xb-tool 工具可用
```

## 预编译包内容
- bin/xb-tool
- lib/libxmlb.so.2.0.0 + 符号链接
- lib/pkgconfig/xmlb.pc
- include/libxmlb-2/*.h + libxmlb-2/libxmlb/*.h（21个头文件）

## 参考
- 源码: https://github.com/hughsie/libxmlb
- 相关项目: fwupd