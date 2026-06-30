# libcmatrix

A [Matrix](https://matrix.org) protocol library written in C using GObject.

libcmatrix requires GObject and Gio, and the library assumes that a glib main
event loop is running (All GTK apps have one). libcmatrix handles all E2EE
transparently. Handled messages/events are stored in a local database.

## Dependencies

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib-2.0 | 2.88.0 | 预编译包 |
| gio-2.0 | 2.88.0 | 预编译包 |
| olm | 3.2.16 | 预编译包 |
| libsoup-3.0 | 3.4.4 | 源码编译 |
| json-glib-1.0 | 1.10.0 | 源码编译 |
| libgcrypt | 1.11.0 | 预编译包 |
| libsecret-1 | 0.21.7 | 预编译包 |
| sqlite3 | 3.49.1 | 预编译包 |
| libpsl | 0.21.5 | 预编译包 |
| libnghttp2 | 1.69.0 | 预编译包 |
| brotli | 1.2.0 | 预编译包 |
| libc++_shared | 系统提供 | /system/lib64 |

## OpenHarmony 适配说明

### 构建系统
- meson 构建，需设置 `PKG_CONFIG_PATH` 指向 `~/usr/local/lib/pkgconfig`

### 关键适配问题
1. **glibintl-shim**: glib 静态库缺少 `g_libintl_*` 符号，需创建 `glibintl-shim.a` 桥接库
2. **json-glib 版本**: cmd-pkgs 只有 1.6.6，需从源码编译 1.10.0 (>= 1.8.0)
3. **libsoup-3.0**: cmd-pkgs 只有 libsoup-2.4，需从源码编译 3.4.4
4. **olm 软链接**: 预编译包缺少 `libolm.so` 软链接，需手动创建

### 当前状态 (v0.0.4)
- 编译状态: **published** (2026-06-01)
- 静态库: ✅ 可用
- 共享库: ✅ 编译成功（需 ELF 签名才能在鸿蒙运行时加载）
- 预编译包: ✅ 所有问题已修复（Phase 1 + Phase 2）
- 头文件: ✅ 完整 (16 个)
- pkg-config: ✅ 可用 (prefix=/usr/local)
- SONAME: ✅ 全部一致（brotli/nghttp2/libffi 已修复）

### 已修复问题 (Phase 1)
1. ✅ 预编译包缺少 libbrotlidec.so、libnghttp2.so、libz.so 外部依赖 → 已补齐
2. ✅ NEEDED 列表中 brotli/nghttp2 使用绝对路径引用 → 改为 soname-only
3. ✅ .so 文件未 strip → 全部 stripped
4. ✅ pkg-config prefix 硬编码为编译机器路径 → prefix=/usr/local

### 已修复问题 (Phase 2)
5. ✅ libffi SONAME/filename 不一致 → 重命名 libffi.so→libffi.so.8 + 软链接
6. ✅ brotli/nghttp2 无 SONAME → patchelf --set-soname 添加
7. ✅ libz.so.1 not stripped → llvm-strip + 移除 .gnu_debuglink
8. ✅ libc++_shared.so 处理 → 不打包（系统库无 .codesign，回退 /system/lib64）

### 非阻塞遗留项
1. ⚠️ 运行时动态加载需 ELF 签名（elf_signer 不可用，经 cmd-pkgs 部署后正常）
2. ⚠️ G0 干净构建需 PKG_CONFIG_PATH 设置（平台限制）
3. ⚠️ libz.so.1 BuildID 含 "bad note 26"（预编译包原始属性，不影响功能）

## 源码仓库
- https://download.savannah.nongnu.org/releases/libcmatrix/