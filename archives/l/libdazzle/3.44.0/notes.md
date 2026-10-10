# libdazzle 3.44.0 适配笔记

## 编译环境

- 构建系统: meson（conan tool_requires meson/1.11.0）
- 编译日期: 2026-09-29
- 编译器: clang 15（/data/service/hnp/bin/clang，OHOS aarch64 sysroot）
- 状态: built（conan-verify 全闸门通过：G0/G1/G2/G3/G4/L2/L4/L5）

## 编译步骤

1. `init-build` → `lang-preflight`（detected=c, meson 构建）
2. `conan-init` 生成骨架后手写 meson 配方：`requires(glib/2.84.0.1, gtk/3.24.43)`（对齐 gtk/3.24.43 依赖图，glib 版本必须一致，R36）、`tool_requires(meson/1.11.0)`
3. meson 选项：`with_introspection=false`（g-ir-scanner 不可用）、`with_vapi=false`、`enable_gtk_doc=false`、`enable_tools=false`（纯库包）、`enable_tests=true`
4. `conan create` 干净构建 → 上游测试套件 build() 内真实执行 → `conan-verify` 全闸门

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson custom_target 阶段 `glib-mkenums` execve EACCES（#126），且同一文件几秒内时好时坏 | el2 HMDFS 对未签名新文件的 execve 信任整窗抖动；`#!/bin/sh` 脚本包装器无法自签 | glib python 工具（glib-mkenums/gdbus-codegen/glib-genmarshal）改用 host clang 编译**C 启动器**并 binary-sign-tool 自签——签名 ELF 稳定可执行 |
| 2 | C 启动器 execv python3 返回 127 | OHOS execve 溯源策略：self-sign ELF 无法 execve 应用签名卷(el1) 的 python3（借道 /system/bin/sh 也被拒） | 启动器 execv `/storage/Users/currentUser/usr/local/bin/python3`（用户卷，meson 同款解释器，实测可执行） |
| 3 | lld `unable to find library -lcairo-gobject` 等 13 个传递依赖，后改绝对路径仍 ENOENT；clang 报 `no such file or directory` 指向确实存在的文件 | el2 HMDFS 对 **conan 解压产物** 的读取对 clang/lld 稳定失败（实测发现 16 字节截断残片，异步修复；conan python 自身可读、我方 shell 的 clang 可读、conan 子进程 clang 必失败） | generate() 将全部依赖 .so/.a **实体化复制**到 build_folder/deplibs 镜像，并改写生成 .pc 的 Libs（-l→镜像绝对路径），链接全部绕开 conan 解压产物 |
| 4 | 链接 `g_libintl_gettext` 等未定义 | OHOS musl 无 gettext；gi18n-lib.h 消费者引用 g_libintl_* | 照 gtk/3.24.43 先例在 glib-2.0.pc 的 Libs 追加 `-lintl`（glib 包自带 libintl.so） |
| 5 | 打包产物缺 `libdazzle-1.0.so` 别名，test_package 链接失败 | meson install 的 symlink 在 HMDFS 落地失败，只剩 `libdazzle-1.0.so.0` 实体文件 | `_create_shared_lib_aliases` 从任意真实 `.so.*`（深版本优先）复制补齐 `.so.0`/`.so` 别名 |
| 6 | 上游测试二进制执行抖动 | 新编译 ELF 的执行信任窗口 | 每个测试执行前 binary-sign-tool 自签；`test-signal-group`/`test-binding-group` 上游注册同一二进制，按唯一路径去重签名 |

## 源码修改

无补丁（patches 为空）。全部适配在 conanfile.py 的 generate/build/package 阶段完成。

## 依赖版本

- glib/2.84.0.1（对齐 gtk/3.24.43 依赖图）
- gtk/3.24.43（传递携带 atk/pango/cairo-gobject/gdk-pixbuf 等 20 包）
- meson/1.11.0（tool_requires）

## 验证结果

```bash
conan create archives/l/libdazzle/3.44.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 上游测试套件（meson 注册 29 项，build() 内经 broadwayd 无头显示真实执行）：
#   broadway_display=yes，28/29 PASS
#   唯一 FAIL：test-directory-reaper（FATAL-ERROR: Failed to create symlink）
#   —— 夹具需创建 symlink，HMDFS 不支持 symlink（踩坑清单 #29），本宿主不可执行
# conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全部 PASS
# 消费者端到端 test_package：16/16 断言 PASS（GType 注册、pattern spec 语义、
#   Levenshtein 距离、ref/unref 生命周期，镜像库直连 + 运行前自签）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libdazzle-1.0.so.0 | 1.1 MB | SONAME 实体库（HMDFS 实体复制，非 symlink） |
| lib/libdazzle-1.0.so | 1.1 MB | dev 别名（实体复制） |
| lib/pkgconfig/libdazzle-1.0.pc | - | pkg-config 元数据（prefix 已 sanitize） |
| include/libdazzle-1.0/ | - | 全量公开头文件 |

## 注意事项

- **依赖库镜像规避**（本配方核心机制）：el2 HMDFS 对 conan 解压产物 .so 的读取对 clang/lld 不稳定（ENOENT/截断残片），generate() 中 `_materialize_dep_libs` 把依赖库复制到构建目录镜像、`_absolutize_pc_libs` 改写 .pc 指向镜像——后续 GNOME/meson 栈的包适配可直接复用此范式。
- glib python 工具必须用编译型 C 启动器 + 自签（不能用 #!/bin/sh 脚本包装器，也不能 execv el1 bundle python3）。
- 上游 test-directory-reaper 因 HMDFS 无 symlink 永久不可执行，非配方缺陷；其余 28 项真实通过。
- 上游 bug：tests/meson.build 中 `test('test-signal-group', test_binding_group)` 注册的是 test-binding-group 二进制，test-signal-group 可执行文件从未被套件运行。
---

**编译结束**: 2026-09-30 00:11
**最终状态**: built
