# DRAFT-pkgm4-preset-nonempty-gate — pkg.m4 预置变量判定是 test -n，空串预置等于未预置

> **Contributor**: Awstme | **Status**: DRAFT | **Updated**: 2026-09-02
> **Severity**: blocking (2) | **Category**: autotools / configure / pkg-config / conan
> **Audience**: 所有通过预置 `*_CFLAGS`/`*_LIBS` 绕过 pkg-config 的 Conan/OHOS autotools 配方

## 触发（trigger）

- OHOS 目标环境无目标 pkg-config/目标 .pc，Conan 配方按 E236 la-free 模式
  预置 `DBUS_CFLAGS/DBUS_LIBS/GLIB_CFLAGS/GLIB_LIBS` 让 configure 走预置分支。
- 目标 configure 含 pkg.m4 门禁（PKG_CHECK_MODULES）**以及**经 acinclude.m4
  引入的独立模块检查（libaudclient 的 `checking for GLIB ... glib-2.0 >= 2.28`）。

## 症状（symptom）

预置变量任一为空串时，configure 不报"预置语法错误"，而是掉进 pkg-config
查询路径并报与真实问题无关的错误（`The pkg-config script could not be
found` / `No package 'dbus-1' found`），中止点取决于哪个变量为空——
DBUS_* 空 → DBUS 检查点中止；GLIB_* 空 → 独立 GLIB 检查点中止。

## 机制（root cause）

pkg.m4 展开后的预置判定是 `test -n "$DBUS_CFLAGS"` 语义——**空串不算预置**。
"已预置"分支要求变量非空且（多数版本）非空白。独立于 PKG_CHECK_MODULES 的
acinclude.m4 检查生成同样的判定代码，因此**每个模块检查涉及的全部
CFLAGS/LIBS 预置变量都必须非空**。生成脚本中判定原样可见：

```sh
grep -n 'test -n "$DBUS_CFLAGS"' configure
```

## 修复（rec）

与 dbus-glib/0.114 已验证配方一致的 E236 la-free 预置模式：四个变量在
conanbuild 环境内全部赋非空真实值（指向构建私有目录内的依赖头/归档），
值来自 conan dependencies 的 cpp_info，不使用占位串。配合
`unset CONFIG_SHELL`（见姊妹草稿 DRAFT-autoconf269-config-shell-unset-not-empty）
后调用 configure。

## 查重（dedup）

- E075（C_INCLUDE_PATH/pkg-config 环境变量陷阱、cflags empty）：不同机制——
  E075 是环境变量兜底导致检测假阴性；本条目是 pkg.m4 **预置分支的门禁语义**
  （test -n）与"每个模块检查都要全量非空预置"的组合要求。
- E089（pkg.m4 缺失导致 PKG_INSTALLDIR/aclocal 问题）：autotools 基础设施层，
  与预置门禁无关。
- E236（.la libdir 过期/la-free 方案）：本条目的**上游配套方案**（预置值来源），
  交叉引用不重叠。
- E264（*-config 脚本依赖发现）：不同发现机制。
- 全库 grep `pkg.m4 预置`/`test -n "$DBUS`/`GLIB_CFLAGS`：无命中。

## 证据（evidence）

- libaudclient 3.5-rc2 设备适配：DBUS/GLIB 四变量全量非空预置后，configure
  DBUS 检查点与独立 GLIB 检查点同时走预置分支，conan create EXIT=0；
  空串预置行为在 dbus-glib/0.114 已验证配方演进中有同型失败记录（两代配方
  一致采用全量非空）。
- 生成 configure 中 `test -n "$DBUS_CFLAGS"`/GLIB 同构判定逐字核验。
- PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7671

## 关系

- similar_to: E075、E089、E236、E264
