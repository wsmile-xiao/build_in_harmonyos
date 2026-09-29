# glib 只提供静态库时，dconf（静态链入 glib）与其消费者（也静态链入 glib）会在同一进程形成两份 GLib 实例，GObject 信号/类型系统跨实例失配 → 运行期崩溃

> Draft: `DRAFT-MLITE-055-GLIB-STATIC-DOUBLE-INSTANCE-DCONF-CRASH`
> Stem: `mlite-0.5.5-glib-static-double-instance-dconf-crash` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-GLIB-STATIC-DOUBLE-INSTANCE-DCONF-CRASH
- **严重度**: 3（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: runtime|glib|static-linking|dependency-defect
- **触发工具**: runtime
- **阶段**: runtime

## 错误特征

```
signal '.*' is invalid for instance .* of type '\(\)'|weak_ref_data_get_surely|g_variant_type_info_check|Bail out! GLib
```

匹配关键词：`glib, dconf, 静态库, GObject, signal is invalid, of type (), weak_ref_data_get_surely, g_variant_type_info_check, duplicate glib`

## 根因

glib/2.84.0 在制品仓只有 .a；libdconf.so 的 DT_NEEDED 仅 libz.so/libc.so（glib 被静态链入，且 glib 符号未导出到 .dynsym，readelf --dyn-syms 命中 0 个），消费者（如 mlite 的 mdconf*.cpp）又静态链入自己那份 glib。两套 GObject 类型注册表互不可见：对 dconf 对象连接 “changed” 信号时得到 “signal 'changed' is invalid for instance … of type '()'”，随后 GLib 断言 weak_ref_data_get_surely / g_variant_type_info_check 失败并 Bail out（SIGABRT/SIGSEGV）。

## 影响范围

所有同时链接 glib（直接或经 pkg-config）与 dconf（或任何静态链入 glib 的库）的包；症状只在运行期出现，编译链接全绿。仅在 glib 有共享库（或该依赖改为动态链 glib）时才消失。

## 验证命令

```bash
readelf -dW <dconf_pkg>/lib/libdconf.so.1.0.0 | grep NEEDED   # 无 libglib-2.0.so.0 → 静态链入；readelf --dyn-syms | grep -c g_variant_new → 0（不导出）
```

## 处置建议

- **优先级**: 1
- **方案**: `use-upstream-conditional-config-or-make-glib-shared`
- **说明**: (1) 首选：走上游原生“dconf 关闭”构型（如 mlite 的 packagesExist(dconf) 分支），依赖链收缩且不产生双 GLib；(2) 若必须启用 dconf：需要依赖侧修复——glib 出 shared 库并让 dconf 动态链接（影响面大，应单独立项），或 dconf 以 -fvisibility=default/导出 glib 符号（不推荐，会与消费者符号冲突）；(3) 不要尝试“消费者少链一份 glib”：静态库符号不导出，去掉 -lglib-2.0 会直接链接失败；(4) 运行期验收必须覆盖 dconf 相关 API，否则双实例问题会被漏掉。
- **参考命令**: `(dconf 关闭构型) 不引入 dconf 依赖 → pkg-config --exists dconf 返回 1 → 上游条件分支跳过 MDConf* 类`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：基础库只有静态版时，**同一进程出现两份该库实例**（一份被依赖包静态链入、一份被消费者静态链入）→ GObject/GVariant 等"全局类型注册表"跨实例失配 → 运行期崩溃。
- **识别信号**：`signal '…' is invalid for instance '0x…' of type '()'`、`weak_ref_data_get_surely` 断言失败、`g_variant_type_info_check` 断言失败、`Bail out!`；编译链接全绿。
- **判别方法**：`readelf -dW <依赖库>.so | grep NEEDED` 看不到 `libglib-2.0.so.0`（说明静态链入）；`readelf --dyn-syms <依赖库>.so | grep -c g_variant_new` 为 0（说明未导出，消费者无法复用其符号）。
- **通用处置**：① 优先走上游**原生条件构型**（如 `packagesExist(dconf)` 为假的分支），从依赖链上消除双实例；② 若必须启用该依赖：让基础库提供 **shared** 版本并让依赖包**动态链接**（属依赖侧改造，应单独立项），或在消费方改用与依赖包同一份 shared 基础库；③ **不要**尝试"消费者少链一份"——静态符号未导出，去掉 `-lglib-2.0` 会直接链接失败。
- **适用范围**：glib 系（glib/gio/gobject）、任何"静态链入基础库且不导出符号"的依赖包与其消费者共存场景。
