# E432 — PkgConfigDeps 按 conan 包名生成 `.pc`，与上游模块名不一致时探测 miss

## 错误特征
头文件找得到，链接却报上游依赖的符号未定义：

```
checking for gstreamer-1.0... no
configure: WARNING: No pkg-config for gstreamer-1.0
checking for gst/gst.h... yes
checking for gst_element_set_state in -lgstreamer-1.0... no
configure: error: Media engine gstreamer not found.
...
ld.lld: error: undefined symbol: g_once_init_enter        # 来自 glib-2.0
ld.lld: error: undefined symbol: g_type_register_static   # 来自 gobject-2.0
```

## 触发条件
- 构建系统: autotools（`PKG_CHECK_MODULES`）
- 阶段: configure → linking
- 前提: 依赖配方未设 `cpp_info.set_property("pkg_config_name", <上游模块名>)`，
  例：包名 `gstreamer` 而上游模块名是 `gstreamer-1.0`

## 根因分析
`PkgConfigDeps` 默认以 **conan 包名**产出 `gstreamer.pc`；上游查的是真实模块名
`gstreamer-1.0.pc`，于是 `PKG_CHECK_MODULES` 失败，退回 `AC_CHECK_LIB` 式的兜底链接
（只有 `-lgstreamer-1.0`），**丢掉了 `Requires: glib-2.0` 及其传递库**，最终在链接期以
glib/gobject 未定义符号的形式暴露。

## 推荐方案
在 `generate()` 内为不一致的模块名生成别名 `.pc`，并保留 `Requires` 行：

```python
alias = os.path.join(self.build_folder, "pkgconfig-alias")
body = open(os.path.join(self.build_folder, "gstreamer.pc")).read()
save(self, os.path.join(alias, "gstreamer-1.0.pc"), body)
# PKG_CONFIG_PATH 前置 alias 目录
```
验证：`pkg-config --libs gstreamer-1.0` 应展开出
`-lgstreamer-1.0 ... -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lffi -lpcre2-8 -lz ...` 全链。

## 影响范围
所有以 pkg-config 探测依赖的 autotools 配方（gstreamer/GTK/SDL/speexdsp 等
包名与上游模块名不一致者）。更彻底的修法是依赖侧补 `pkg_config_name` 属性。
