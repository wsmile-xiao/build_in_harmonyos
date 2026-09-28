# E429 — Conan PkgConfigDeps 不生成依赖包内的额外 .pc 组件（meson dependency 找不到 gio-unix-2.0）

## 错误特征

meson configure（`meson setup`）在解析依赖时失败：

```
Run-time dependency gio-unix-2.0 found: NO
meson.build:XX:0: ERROR: Dependency "gio-unix-2.0" not found, tried pkgconfig
```

而该 `.pc` 实际上存在于依赖包里（`<conan-cache>/glib-*/p/lib/pkgconfig/gio-unix-2.0.pc`）。

## 触发条件

- 构建系统: meson（经 Conan MesonToolchain + PkgConfigDeps）
- 阶段: configure（`meson setup`）
- 依赖包: glib（提供 glib-2.0/gobject-2.0/gio-2.0/gio-unix-2.0/gmodule-2.0/gthread-2.0 等 .pc）
- 源码: `meson.build` 中存在 `dependency('gio-unix-2.0')`

## 根因分析

Conan 的 `PkgConfigDeps` 依据依赖包 `package_info()` 里声明的组件（cpp_info.components）
生成 .pc。glib 配方只声明了 glib-2.0/gobject-2.0/gio-2.0 等组件，**没有**声明
gio-unix-2.0 组件，因此 generators_folder 里不会生成 `gio-unix-2.0.pc`——尽管上游 glib
安装时把 `gio-unix-2.0.pc` 装进了包的 `lib/pkgconfig`。

`MesonToolchain` 生成的 `conan_meson_native.ini` 默认只让 meson 在 generators_folder
（PkgConfigDeps 输出）中搜索 .pc；依赖包自身的 `lib/pkgconfig` 不在搜索路径内。于是
`dependency('gio-unix-2.0')` 找不到。

## 解决方案

### 推荐方案

在 conanfile 的 `generate()` 中，把 generators_folder + 各依赖包的 `lib/pkgconfig`
（及 `share/pkgconfig`）写进 meson machine file 的 `[properties] pkg_config_path`，
并同步 prepend 到 `PKG_CONFIG_PATH` 构建环境变量：

```python
def generate(self):
    PkgConfigDeps(self).generate()
    tc = MesonToolchain(self)
    ...
    tc.generate()
    self._append_dependency_pkg_config_paths()   # 改写 conan_meson_native.ini pkg_config_path
    # _build_environment() 中同时 env.prepend_path("PKG_CONFIG_PATH", <dep>/lib/pkgconfig)
```

先例配方：`archives/a/accountsservice/26.27.3/conanfile.py`
（`_append_dependency_pkg_config_paths` + `_build_environment`）。

### 禁止做法

- ❌ 删除 / 改名依赖包内的 `gio-unix-2.0.pc`（`rm`/`sed -delete`/`mv`）——应让其可见，而非移除。
- ❌ 把 gio-unix-2.0 依赖改成“静默跳过 / 打桩返回 0”（会丢掉 gio-unix 真实功能）。

## 验证

```bash
# 依赖包内存在
find "$(conan cache path glib/2.84.0.1)" -name 'gio-unix-2.0.pc'
# generators 目录默认缺失（未注入前）
ls <build>/conan/*.pc | grep gio-unix
# 修复后：meson setup 无 "Dependency gio-unix-2.0 not found"，ninja 编译通过
```

libmbim-tools 1.34.0 实测：注入后 `meson setup` 通过，`meson test` 9/9，
`conan create` exit 0。

## 关联条目

- 相关: E075（PKG_CONFIG_PATH 环境变量）、E524（依赖注入私有 prefix）、E296（MesonToolchain 交叉 machine file 完整性）、E090（meson 平台探测）
