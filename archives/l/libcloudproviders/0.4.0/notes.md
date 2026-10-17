# libcloudproviders 0.4.0 适配笔记

## 编译环境
- 构建系统: meson (>= 1.9.0)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

```bash
# 配方通过 conan create 驱动：
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 内部流程：source() 解压官方 tarball → generate() PkgConfigDeps + MesonToolchain
#   → build() meson.configure + meson.build → package() meson.install + ELF 签名
```

meson 配置关键选项：
- `-Dintrospection=false -Dvapigen=false`：裁剪 GIR/Vala 语言绑定（见下）
- `-Ddocumentation` 默认 false
- `wrap_mode=nodownload`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `dependency('gio-unix-2.0')` 找不到 | glib conan 配方只声明 glib-2.0/gobject-2.0/gmodule-2.0/gthread-2.0/gio-2.0 五个组件，无独立 gio-unix-2.0 组件，PkgConfigDeps 不生成 gio-unix-2.0.pc | `_create_gio_unix_pc_alias()`：从 glib 包内 lib/pkgconfig 复制 gio-unix-2.0.pc 并重写 `prefix=/` → 包实际路径（accountsservice dbus-1.pc 同款模式） |
| 2 | gnome.mkenums_simple / gnome.gdbus_codegen 找不到工具 | PkgConfigDeps 生成的 .pc 不含 glib_mkenums/glib_genmarshal/gobject_query/gdbus_codegen 变量 | `_augment_glib_pkg_config()`：用 python wrapper（runpy 加载包内脚本，保证 __file__ 位于 bin/ 可定位 share/glib-2.0 数据）注入 .pc 变量（accountsservice 已验证模式） |
| 3 | vapigen 与 introspection 耦合 | src/meson.build 中 `generate_vapi(sources: libcloudproviders_gir[0])` 引用 introspection 产物 | 两选项必须同关（introspection=false + vapigen=false），避免引用未定义变量 |
| 4 | OHOS 无 DBus session bus | 上游 test/meson.build 构建的两个测试程序（server/client）是 DBus session bus 集成/演示程序，未注册 meson test() | 不作为 CI 自动化测试；test_package 自研断言覆盖 GType 注册/单例/枚举 ABI/导出 API（bus 可用时） |

## 源码修改

无（纯配方层适配，无补丁）

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib (glib-2.0/gio-2.0/gio-unix-2.0) | 2.88.3.1 | 唯一编译依赖，transitive_headers/libs |

## 可选特性裁剪说明

- `introspection`（GIR/typelib）：供 Python/JS 语言绑定，C 消费者不需要
- `vapigen`（Vala 绑定）：依赖 introspection 产物，同关
- 核心库 libcloudproviders.so + 6 个头文件 + cloudproviders.pc（pkg-config）完整保留

## 验证结果

```bash
# test_package L1 测试（conan create 自动执行）：
#   GType 注册检查 5 项 + collector 单例 3 项 + 枚举 ABI 4 项 = 12 断言
#   session bus 可用时追加 exporter round-trip 断言（OHOS 无 dbus-daemon 自动跳过）
```

## 注意事项

- 上游测试（testcloudprovidersserver/client）需 DBus session bus，OHOS 无
  dbus-daemon 无法运行，已在 MANIFEST.yml 与 PR body 如实说明（平台限制）
- ELF 签名：OHOS 下 .so 需 llvm-objcopy 去 .codesign + binary-sign-tool 自签名
---

**编译结束**: 2026-09-18 16:24
**最终状态**: built
