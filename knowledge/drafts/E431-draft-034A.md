# E431 — PkgConfigDeps 生成 glib-2.0.pc 缺 -lintl 致 g_libintl_* 链接错误

## 错误特征
`undefined reference to 'g_libintl_dngettext'`（及 g_libintl_* 系列符号），
meson 库链接 `--no-undefined` 下必炸。

## 触发条件
- 构建系统: meson + conan PkgConfigDeps
- 阶段: make（链接阶段）

## 根因分析
PkgConfigDeps 生成的 glib-2.0.pc Libs 只有 `-lglib-2.0`，缺 `-lintl`。
新版源码直调 `g_libintl_dngettext`（如 libadwaita 1.8.x 的 adw-main.c /
adw-tab-overview.c）+ `--no-undefined` 时必炸；旧版本无此直调则幸免
（1.2.0 过、1.8.8 炸）。glib/2.84.0.1.1 包自带 libintl.so.8（12 个 T
`g_libintl_*` 定义），补 `-lintl` 指向同包即自洽，无需外部 libintl。

## 解决方案

### 推荐方案
主配方 generate() 在 PkgConfigDeps 之后强制回写 6 个 glib 系 .pc：
prefix 统一指向 `self.dependencies["glib"].package_folder` + glib-2.0.pc
的 Libs 追加 `-lintl`（参考 libadwaita/1.8.8 conanfile.py 的
`_normalize_glib_pc()`，文件缺失时全新写入兜底）。

### 禁止做法
- ❌ 给所有 .pc 无差别加 `-lintl`（仅 glib-2.0.pc 需要）
- ❌ 注入共享系统前缀（R49：必须指向 conan 私有包目录）
- ❌ 换用系统 libintl（OHOS 目标链无系统 libintl 可用）

## 验证
```bash
nm -D <glib包目录>/lib/libintl.so.8 | grep " T g_libintl"  # 确认 T 定义存在
conan create archives/l/libadwaita/1.8.8/conanfile.py --build=missing  # 链接通过
```

## 关联条目
- 相关: E430（同一 glib 缓存链排查中发现）
