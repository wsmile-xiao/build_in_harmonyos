# E429 — PkgConfigDeps 只生成聚合 pc，PKG_CHECK_MODULES 多组件查询失败

## 错误特征
```
checking for gio-2.0... no
configure: error: Package requirements (glib-2.0 gio-2.0 gobject-2.0) were not met:
Package gio-2.0 was not found in the pkg-config search path.
Perhaps you should add the directory containing `gio-2.0.pc'
to the PKG_CONFIG_PATH environment variable
No package 'gio-2.0' found
```
（上游 configure.ac 中 `PKG_CHECK_MODULES([GLIB], [glib-2.0 gio-2.0 gobject-2.0])` 类多模块查询，缺任一组件 pc 即中止。）

## 触发条件
- 构建系统: autotools（PKG_CHECK_MODULES / PKG_CHECK_VAR）
- 阶段: configure
- 依赖: conan PkgConfigDeps 生成器 + 声明了多组件依赖（glib 系 gio/gobject、宿主私有 pc 如 bitlbee.pc 等）

## 根因分析
conan 的 PkgConfigDeps 生成器只按配方的 pkg_config_name/聚合 cpp_info 生成**单个** pc 文件（如 glib/2.84.0 仅产出 glib-2.0.pc，不产出 gio-2.0.pc/gobject-2.0.pc 组件 pc）；宿主应用包（如 bitlbee/3.6 只含 bin 二进制）也没有 .pc 可用。而上游 configure.ac 的 PKG_CHECK_MODULES 一次查询多个组件模块名，缺任一 pc 即中止。

## 解决方案

### 推荐方案
**pkg.m4 预设变量整体旁路**：pkg.m4 的 _PKG_CONFIG 对每个模块独立判断——若 `<MODULE>_CFLAGS` 与 `<MODULE>_LIBS` 环境变量**同时非空**，pkg-config 完全不执行（连版本检查都跳过）。配方在 `generate()` 里经 AutotoolsToolchain 环境注入六个变量（值全部来自 `self.dependencies` 路径，R33 合规）+ GLIB_GENMARSHAL 等工具变量；`PKG_CHECK_VAR` 类查询（如 plugindir）落回上游 configure.ac 的默认分支（如 $libdir/bitlbee）。

注意：本 conan 版本的 `AutotoolsToolchain.environment()` 是方法、`tc.generate(env=...)` 接受扩展 env（直接替换会丢 CC/CFLAGS）。

实例：bitlbee-facebook 1.2.2（archives/b/bitlbee-facebook/1.2.2）。

### 备选方案
自建组件 pc 文件目录置于 PKG_CONFIG_PATH 首位（手工补 gio-2.0.pc 等）。

### 禁止做法
- ❌ 在 build() 里裸用 shell 环境变量传 CFLAGS/LIBS（违反 R33）
- ❌ 手改生成的 configure 脚本去删 PKG_CHECK_MODULES（改生成文件违反 R6）

## 验证
```bash
# 注入六变量后重跑 configure，应无 "Package gio-2.0 was not found"：
GLIB_CFLAGS="-I<dep>/include/glib-2.0 -I<dep>/lib/glib-2.0/include" \
GLIB_LIBS="-L<dep>/lib -lglib-2.0" \
./configure --prefix=$DEFAULT_PREFIX
```

## 关联条目
- 相关: E345（dlopen 模块桩宿主测试范式）、E442
