# lomiri-schemas

Lomiri 桌面栈的**声明式数据包**：GSettings schema、AccountsService D-Bus 接口描述、
polkit 策略与 pkg-config 元数据。不含任何可编译代码。

## 简介

lomiri-schemas 由 UBports 从 Lomiri 主仓中拆出，目的是让 Lomiri 本身与 Ayatana
Indicators 在打包/构建准备阶段就能拿到所需的 schema 文件，而不必等整个 Lomiri
栈就绪（同类做法参考 Canonical 的 gsettings-ubuntu-schemas）。

内容：

- **6 个 GSettings schema**（15 个 `<schema>` 节点）：`com.lomiri.Shell` 及
  Greeter / Interface / Launcher / Devices / Decorations / IntegratedMenus /
  Gestures / Shortcuts 子 schema、`com.lomiri.phone`、`com.lomiri.sound`、
  `com.lomiri.notifications.settings[.applications]`、`com.lomiri.touch.sound`、
  `com.lomiri.touch.system`。
- **6 个 AccountsService D-Bus 接口 XML**，安装到 `share/dbus-1/interfaces/`，
  并在 `share/accountsservice/interfaces/` 建相对符号链接。
- **polkit**：`com.lomiri.AccountsService.policy` + `50-com.lomiri.AccountsService.rules`。
- **pkg-config**：`lomiri-schemas.pc`（`Requires: glib-2.0`）。

## OHOS 适配要点

- 纯 CMake 数据包（上游 `project(... LANGUAGES NONE)`），无交叉编译障碍；产物全部是
  文本与 schema。
- **补丁 0001**：上游用 `intltool-merge --xml-style` 渲染 `.gschema.xml.in`，该 Perl
  脚本硬依赖 `XML::Parser` 模块，OHOS 设备的 perl 没有它，6 个 schema 全部构建失败。
  这些 gschema 输入不含 gettext 标记、上游也无 `po/` 目录，`--no-translations` 渲染
  与原文逐字节等价，故补丁改用 `configure_file(... COPYONLY)`，并去掉
  `find_package(Intltool REQUIRED)`。
- `find_package(GSettings)` 的 CMake 模块来自 `cmake-extras/1.9`；Conan 的
  `conan_cmakedeps_paths.cmake` 不写 `CMAKE_PREFIX_PATH`，配方 `generate()` 追加一条
  把它补上。
- `gettext`（msgfmt/msgmerge）是构建期工具，走 `tool_requires`；并把它的 `bin/`
  前置进 `CMAKE_PROGRAM_PATH`，避开 OHOS SDK 里的 shebang 坏条目。
- `pkg-config gio-2.0 --variable glib_compile_schemas` 在 Conan 侧为空（PkgConfigDeps
  只按 cpp_info 生成 `.pc`），配方补写该变量，避免 CTest 校验命令退化成空。
- schema 安装目录经 `-DGSETTINGS_LOCALINSTALL=ON` 落进本包
  `share/glib-2.0/schemas/`（默认会写进只读的 glib 依赖 prefix）。
- 上游 `CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT` 兜底会把 prefix 改成 `/usr`，
  配方显式下发 `CMAKE_INSTALL_PREFIX` cache 变量绕过。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib | 2.88.3 | 运行期 GSettings；另提供 `glib-compile-schemas` |
| cmake-extras | 1.9 | GSettings CMake 模块（构建期） |
| gettext | 0.22.5.1 | msgfmt/msgmerge（构建期） |

## 功能验证

```bash
# 安装后校验 schema 是否被 GSettings 接受（--strict 把告警当错误）
<glib-prefix>/bin/glib-compile-schemas --strict --dry-run \
  <lomiri-schemas-prefix>/share/glib-2.0/schemas

# pkg-config 元数据
PKG_CONFIG_PATH=<lomiri-schemas-prefix>/share/pkgconfig pkg-config --modversion lomiri-schemas
```

本仓 `test_package/test_lomiri_schemas.py` 把这套校验固化成 48 项断言（含 XML 良构、
15 个 schema id 就位、D-Bus/polkit 文件、pc 元数据），在 OHOS 目标实跑。

## 参考

- [源码仓库](https://gitlab.com/ubports/development/core/lomiri-schemas)
- [Lomiri 项目](https://lomiri.com/)
