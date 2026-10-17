# E321: PkgConfigDeps 不生成 gmodule-no-export-2.0.pc 导致 meson configure 失败

## 基本信息
- **严重度**: 3 (blocking)
- **类别**: meson | pkgconfig | glib
- **触发工具**: meson
- **阶段**: configure
- **首次发现**: gdk-pixbuf 2.42.12 编译 (2026-08-07)

## 错误签名

configure 阶段:
```
ERROR: Could not get pkg-config variable and no default provided for 'gmodule_supported' in 'gmodule-no-export-2.0'
```

或：
```
Programs found: NO
Message: Did not find pkg-config variable 'gmodule_supported'
```

## 根因分析

PkgConfigDeps 只从依赖 recipe 的 `package_info.components` 生成 `.pc` 文件。glib 的
conan recipe 只声明了 `gmodule-2.0` 组件，未声明 `gmodule-no-export-2.0`。

gdk-pixbuf 等 GNOME 库的 `meson.build` 使用 `dependency('gmodule-no-export-2.0')`
且调用 `get_variable('gmodule_supported')` 判断 gmodule 是否可用，configure 阶段直接失败。

HarmonyOS PC 上 glib 以 conan 包方式提供，`.pc` 由 PkgConfigDeps 按 recipe 组件生成，
缺少组件声明时不会自动补全。

## 受影响范围

所有基于 glib 的 GNOME meson 库（gdk-pixbuf / pango / gtk 等）在使用 conan 构建时。

## 解决方案

### 方案 1（推荐）：recipe generate() 中手工合成 gmodule-no-export-2.0.pc

```python
def _write_gmodule_no_export_pc(self):
    """合成 gmodule-no-export-2.0.pc（PkgConfigDeps 不生成）."""
    pc = self.generators_folder / "gmodule-no-export-2.0.pc"
    pc.write_text(
        f"prefix={self.dependencies['glib'].package_folder}\n"
        "libdir=${prefix}/lib\n"
        "includedir=${prefix}/include\n"
        "gmodule_supported=true\n"
        "Name: GModule\n"
        "Description: Dynamic module loader for GLib\n"
        "Requires: glib-2.0\n"
        "Version: 2.0.0\n"
        "Libs: -L${libdir} -lgmodule-2.0\n"
        "Cflags: -I${includedir}/glib-2.0 -I${libdir}/glib-2.0/include\n",
        encoding="utf-8",
    )
```

### 禁止做法
- ❌ 不要试图在 meson 侧绕过：gdk-pixbuf 的 meson.build 硬依赖 `gmodule-no-export-2.0`
- ❌ 不要用 `--wrap-mode` 或 pkg-config path 手工塞入宿主机 .pc（会引入宿主机 glib）

## 验证
```bash
conan create ... && meson setup build -Dgio_sniffing=false
# configure 不再报 gmodule_supported 缺失
```

## 关联条目
- 相关: E123（glib proxy-libintl），E090（meson host_system）
