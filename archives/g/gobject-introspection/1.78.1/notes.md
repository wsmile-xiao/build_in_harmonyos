# gobject-introspection 1.78.1 适配笔记

## 编译环境
- 构建系统: meson + ninja
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (conan 适配中)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 3.12 distutils.msvccompiler 移除 | Python 3.12 弃用 distutils | 添加 try/except 导入 _msvccompiler |
| 2 | meson host_system == 'linux' 不匹配 | HarmonyOS 的 host_system 为 'harmonyos' | 添加 'harmonyos' 到平台检查条件 |
| 3 | 链接共享库失败 (zlib 缺 -fPIC) | glib2 及其依赖为静态库，zlib 无 -fPIC | 将 girepository 改为 static_library 构建 |
| 4 | _giscanner Python 扩展模块无法构建/加载 | hmmac 安全标签限制 + zlib 无 -fPIC | 条件构建：仅 build_introspection_data=true 时构建 |
| 5 | introspection 数据无法在构建时生成 | g-ir-scanner 需要 dlopen _giscanner.so，hmmac 阻止 | 设置 build_introspection_data=false |

## 源码修改 (ohos-adapt.patch)

1. **giscanner/ccompiler.py**: Python 3.12 兼容性 — try/except 导入 MSVCCompiler
2. **meson.build**: 平台检查添加 'harmonyos' (line 150-151)
3. **girepository/meson.build**: shared_library → static_library，移除 version/darwin_versions 参数
4. **giscanner/meson.build**: 条件构建 _giscanner 模块 (build_introspection_data=true 时构建，否则 disabler())

## 构建选项

- `--wrap-mode=nofallback` — 不下载子项目
- `-Dbuild_introspection_data=false` — 禁用 introspection 数据生成（平台限制）
- `-Dcairo=disabled` — 无 cairo 依赖
- `-Ddoctool=disabled` — 无 mako/markdown 依赖
- `default_library=static` — 静态构建（glib2 依赖链为静态）

## 平台限制

1. Python 扩展模块无法被 dlopen 加载（E212 — hmmac 安全标签限制）
2. introspection 数据生成功能在构建时禁用（工具仍安装，可在有 hnp 路径权限时生成）
3. 运行时需设置 LD_LIBRARY_PATH

## 构建产物

- `lib/libgirepository-1.0.a` — 静态库
- `bin/g-ir-compiler` — 编译器工具（已验证可运行）
- `bin/g-ir-generate` — 生成工具（已验证可运行）
- `bin/g-ir-inspect` — 检查工具
- `bin/g-ir-scanner` — 扫描器脚本（Python）
- `bin/g-ir-annotation-tool` — 注释工具脚本
- `include/gobject-introspection-1.0/` — 头文件
- `lib/gobject-introspection/giscanner/` — Python 模块
- `lib/pkgconfig/gobject-introspection-1.0.pc` — pkg-config 文件

---
**编译结束**: 2026-08-06
**最终状态**: built
