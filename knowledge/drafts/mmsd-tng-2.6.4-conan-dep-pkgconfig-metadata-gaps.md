# conan 依赖包的 pkg-config / 链接元数据缺口四类

> 草稿 ID：`mmsd-tng-2.6.4-conan-dep-pkgconfig-metadata-gaps`
> 来源任务：mmsd-tng 2.6.4 适配（Meson；10 个 conan 依赖：glib / libmm / libsoup3 /
> c-ares / libphonenumber / mobile-broadband-provider-info / dbus / json-c / meson / ninja）

本条目把一次适配中连续遇到的 4 类"上游探测不到依赖 / 链接缺符号"归并为一族：
**根因都在依赖包的元数据（cpp_info → PkgConfigDeps 产物）与上游构建脚本的期望不一致，
不是本项目源码的问题**，因此统一修在 `generate()`，绝不改上游源码。

---

## 类别 ① .pc 自定义变量缺失（数据包）

**错误**
```
meson.build:31:87: ERROR: Could not get pkg-config variable and no default provided
for <PkgConfigDependency mobile-broadband-provider-info: True []>
```

**根因**：上游 `dependency('mobile-broadband-provider-info').get_variable(pkgconfig:'database')`；
`database=` 变量**只存在于依赖包自带的 `share/pkgconfig/mobile-broadband-provider-info.pc`**，
而 PkgConfigDeps 生成的同名 .pc 只有 prefix/Name/Version。

**修复**：把依赖包的 `share/pkgconfig` 前置进 `pkg_config_path`（不要覆盖它）。

```bash
$ find <pkg> -name '*.pc'
<pkg>/share/pkgconfig/mobile-broadband-provider-info.pc
$ cat <pkg>/share/pkgconfig/mobile-broadband-provider-info.pc
pkgdatadir=${pcfiledir}/../mobile-broadband-provider-info
database=${pkgdatadir}/serviceproviders.xml
```

---

## 类别 ② 包内没有 .pc，上游却用 pkg-config 名

**错误**
```
tools/meson.build:18:6: ERROR: Dependency "dbus-1" not found (tried pkg-config and cmake)
```

**根因**：conan `dbus` 包**不提供任何 .pc**；PkgConfigDeps 按 `cpp_info` 的
`pkg_config_name` 只生成 `dbus.pc`，而上游 `dependency('dbus-1', version:'>1')` 要的是 `dbus-1`。

**修复**：在 pc 补齐目录**合成 `dbus-1.pc`**（注意 include 目录是 `<pkg>/include/dbus-1.0`）：

```ini
prefix=<dbus package_folder>
libdir=${prefix}/lib
includedir=${prefix}/include/dbus-1.0

Name: dbus-1
Description: Conan dbus package aliased as dbus-1
Version: 1.14.10
Libs: -L${libdir} -ldbus-1
Cflags: -I${includedir}
Requires: expat
```

---

## 类别 ③ 生成的 .pc 丢了 Requires（上游 .pc 有）

**错误**（只在 unit 测试里暴露）
```
ld.lld: error: undefined symbol: g_file_new_for_path
ld.lld: error: undefined symbol: g_io_error_quark
```

**根因**：conan `libmm` 的 `package_info` 未声明 gio/gobject，PkgConfigDeps 生成
`mm-glib.pc` 只有 `Requires: glib-2.0 dbus`；而上游 `mm-glib.pc` 是
`Requires: gio-unix-2.0, glib-2.0, gio-2.0, gobject-2.0`。
`unit/meson.build` 的 deps 只列 glib+mm-glib，gio 本应由 mm-glib 传递进来 → 缺 `-lgio-2.0`。
（`gglib/2.84.0.1.1` 已正确实现该 pattern，是很好的对照参考。）

**修复**：按上游补齐覆盖 `mm-glib.pc`：
`Requires: glib-2.0 gio-2.0 gobject-2.0 dbus-1`。

---

## 类别 ④ 包内有库但未列入 `cpp_info.libs`

**错误**
```
ld.lld: error: undefined symbol: utf8_range_IsValid
>>> referenced by parse_context.cc … in archive <pb>/lib/libprotobuf.a
ld.lld: error: undefined symbol: utf8_range_ValidPrefix
```

**根因**：conan `protobuf/33.6` 包内**有** `libutf8_validity.a` / `libutf8_range.a`，
但 `cpp_info.libs = ["protobuf"]` 未包含它们；protobuf ≥33 的 `parse_context.cc` 引用这两个符号。

**修复**：在补齐的 `protobuf.pc` 的 Libs 追加，**顺序必须在 `-lprotobuf` 之后**（静态库单遍扫描）：

```ini
Libs: -L${libdir} -lprotobuf -lutf8_validity -lutf8_range -lpthread
```

---

## 统一处置方案（推荐）

在 `generate()` 建一个 **pc 补齐目录**，按顺序前置：

```python
pcfix = os.path.join(self.build_folder, "pkgconfig-fix")
os.makedirs(pcfix, exist_ok=True)
extra_pc = [
    pcfix,                                             # 合成/覆盖的 .pc 优先命中
    os.path.join(mbpi.package_folder, "share", "pkgconfig"),   # ① 数据包自带 .pc
]
tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])
```

`.pc` 内容全部由 `self.dependencies[...].package_folder` 与 `ref.version` 生成
（不硬编码绝对路径、不写进依赖包目录、不污染 `/usr/local`）。

**选择口径**：能靠 pc 补齐解决的 → 不动源码；
若上游探测方式本身与包形态不匹配（如 `cc.find_library('phonenumber')` 遇到**静态库 + 自带 .pc**：
`find_library` 只给 `-l`，拿不到 include 与静态传递库）→ 才改上游为 `dependency('<pc name>')`，
并在 PR 说明理由（本例即 `patches/0001`、`patches/0003`）。

## 反例（不要这么做）

- ❌ 直接覆盖依赖包目录或全局 `/usr/local` 的 .pc —— 污染共享前缀（R49/E524），不可复现；
- ❌ 用 `__OHOS__` 包住这些修复 —— 缺口与平台无关（同一批 conan 包在 Linux 上同样复现），且违反 R8；
- ❌ 链接顺序颠倒（`-lutf8_range` 放到 `-lprotobuf` 之前）—— 静态库单遍扫描，仍报 undefined。

## 验证

```
$ meson setup <build> <src> -Dbuild-mmsctl=true
Run-time dependency glib-2.0 found: YES 2.84.0.1.1
Run-time dependency mm-glib found: YES 1.24.2
Run-time dependency libsoup-3.0 found: YES 3.6.5-r3
Run-time dependency libcares found: YES 1.34.6
Run-time dependency libphonenumber found: YES 8.13.51
Run-time dependency dbus-1 found: YES 1.14.10
Run-time dependency json-c found: YES 0.18
$ meson compile -C <build>        # 35/35 target，零 undefined symbol
```

## 证据

- 四类错误现场：`archives/m/mmsd-tng/2.6.4/reports/00a-meson-setup.log`、
  `reports/01-meson-compile-ohos.log`、`reports/03-conan-create.log`
- 配方实现：`archives/m/mmsd-tng/2.6.4/conanfile.py` → `_fix_pkgconfig()` / `generate()`
- 关联补丁：`patches/0001-meson.build.patch`、`patches/0003-unit-meson.build.patch`
