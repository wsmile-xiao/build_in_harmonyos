# DRAFT-libsoup3-r3-glib-shared-recipe-fix

## 问题

libsoup3/3.6.5-r2 发布二进制把 gobject 静态内嵌进 libsoup-3.0.so.0（NEEDED 无
libgobject-2.0.so.0，自带 g_type_register_fundamental 强定义），与 gtk4/4.22.4
链接的共享 glib/2.84.0.1.1（NEEDED libgobject-2.0.so.0）同时加载时，进程启动期
双 GObject 类型系统冲突（cannot register existing type 'gchar'，
gvaluetypes.c:453 SIGABRT），导致 libshumate 16 个上游测试 0/16。

## 根因

旧配方依赖 glib2/2.88.0（独立 conan 包，默认静态），把 gobject 静态内嵌进
libsoup-3.0.so.0；消费链（gtk4 链 r85/r86）使用共享 glib/2.84.0.1.1。两个
GObject 类型系统在同一进程共存 → GType 重复注册。

## 方案（配方级修复，非补丁）

1. requirements：glib2/2.88.0 → `glib/2.84.0.1.1` + `options={"shared": True}`
   （**普通 requires，不是 override**——override 依赖不进 self.dependencies，
   generate() 读 package_folder 时 KeyError）。
2. generate()：
   - glib 包内 .pc 复制并修正 prefix（包内 .pc 是 `--prefix=/`），删除
     `Requires.private: libpcre2-8` 行（本机 pkg-config 无 libpcre2-8.pc →
     "Package libpcre2-8 was not found"）；
   - pkg_config_path 顺序：pc-fix 目录在 generators **之前**（PkgConfigDeps 生成
     的 glib-2.0.pc 缺 `-lintl` → `g_libintl_bindtextdomain` 链接失败）；
   - glib bin 工具（glib-compile-resources 等）经 native file 绑定 + 
     LD_LIBRARY_PATH 前置 glib lib（共享 glib 的 ELF 工具 exec 需运行时库）。
3. package_info()：只把 glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0/gthread-2.0
   并入 cpp_info.libs；**不要并入 ffi/intl**（是 glib 运行时依赖，并入会让
   CMakeDeps 在本包内找 libffi → "Library 'ffi' not found"）。
4. 取证：`llvm-readelf -d` NEEDED 含 libgobject-2.0.so.0；`llvm-nm -D` 无
   ' T g_type_register_fundamental' 强导出；test_package 进程级复验无
   'cannot register existing type'。

## 验证

- conan create 通过（test_package L1 通过）。
- NEEDED 含 libgobject-2.0.so.0、无 g_type_register_fundamental 强导出
  （见 reports/forensics/r2-vs-r3.md）。
- 上游测试 33 项注册：28 OK / 3 FAIL（hsts 相关无 TLS 后端 + unix-socket
  AF_UNIX EPERM）/ 2 SKIP（无 glib-networking）。

## 适用边界 / 反例

- 适用：任何"静态内嵌 gobject 的发布二进制 + 共享 glib 发布二进制"共存链；
  libsoup3 类 glib 系库适配，需与 gtk4 链同源 glib。
- 反例：单一 glib 使用方（无 gtk4/无第二 glib 提供者）不触发双副本冲突；
  gssdp 的"单副本 .pc Libs 置空"方案仅在进程内无共享 glib 副本时可用。

## 查重关系

- caused_by / related: DRAFT-libshumate-libsoup3-static-gobject-dual-glib-sigabrt
  （本草稿是该上游草稿"恢复条件=发布形态修复"的配方级落地实现）
- similar_to: E348（glib pc 转发）、E444（GObject 运行时 init，机制不同）
- 七轴查重：exact/causal=false；trigger/solution=partial（与 E444 关键字交叠但
  机制不同）；combination/boundary/test_migration=true → **new_draft（路径 B）**

## 适用库

libsoup3/3.6.5-r3（archives/l/libsoup3/3.6.5-r3，分支 fix/libsoup3-3.6.5-r3）
