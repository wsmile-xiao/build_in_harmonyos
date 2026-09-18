# libitl-gobject

## 简介

libitl-gobject 是 [ITL](https://github.com/arabeyes-org/ITL)（Islamic Tools and
Libraries）的 GObject 绑定：把 libitl 的 Hijri/Gregorian 日期换算、穆斯林礼拜
时间与 Qibla 方向计算封装成 `ItlPrayer` GObject，供 GTK/GNOME 技术栈与语言
绑定使用。

- 上游: https://github.com/aelmahmoudy/libitl-gobject
- 许可证: GPL-3.0-or-later（注意不是 libitl 的 LGPL）

## OHOS 适配

- **构建系统**: autotools + libtool。上游 tag 归档**不含**任何生成好的
  Autotools 文件（无 `configure`/`Makefile.in`/`aclocal.m4`/`ltmain.sh`/`m4/`），
  上游 README 明确要求 `autoreconf -f -i`。OHOS 下改用**分步**执行
  `aclocal → libtoolize → autoconf → automake`，绕开 HMDFS 上 `autoreconf`
  链的 `autoconf.m4f` 加载冲突（同款处理见 `archives/a/abiword-plugin-gdict`）。
- **构建期依赖**: `automake/1.18` + `libtool/2.5.4`（`tool_requires`）。
- **vendoring**: `m4/pkg.m4`、`m4/introspection.m4` 随配方提交——`configure.ac`
  用到 `PKG_CHECK_MODULES` 与 `GOBJECT_INTROSPECTION_CHECK`，这两个宏不在构建机
  默认 aclocal 搜索路径里。
- **平台识别（E007）**: automake/libtool 自带的 `config.guess`/`config.sub`
  不识别 `HarmonyOS`，`configure` 会报 `cannot guess build type`。配方在
  `configure` 前给这两个脚本打补丁，产出三元组 `aarch64-unknown-linux-ohos`；
  **不用** `--build/--host` 绕过（那会被 autoconf 判为交叉编译，跳过全部
  `AC_RUN_IFELSE` 探测并写出错误的 `config.h`）。
- **HMDFS 适配**: 生成的 `configure` 在 HMDFS 上丢失执行位，需补回后以
  `sh "<abs>/configure"` 调用；同时把脚本里的 `umask 077` 改为 `022`（E011/E114）。
- **阶段一范围**: 只交付库本体 `libitl_gobject.so`，`--disable-introspection`。
  `.gir`/`.typelib` 生成需要可用的 `g-ir-scanner`，作为独立工作项另行推进。

## 依赖

- `libitl/0.8.0`（`configure.ac` 的 `AC_CHECK_LIB([itl],[getNorthQibla])`；
  0.8.0 正好是上游要求的版本下限）
- `glib/2.84.0.1`（`PKG_CHECK_MODULES(GOBJECT, gobject-2.0 >= 2.2.0)`）

## 补丁

| 补丁 | 作用 |
|------|------|
| `0001-src-Makefile.am.patch` | 移除硬编码的 `-I/usr/include/itl`（Debian 系统路径） |
| `0002-libitl-gobject.pc.in.patch` | 修正 `.pc` 链接名 `-litl-gobject` → `-litl_gobject` |
| `0003-src-Makefile.am-vpath.patch` | `glib-mkenums` 规则输入补 `$(srcdir)/`（`basic_layout` 是 VPATH 构建） |
| `0004-itl-gobject.h-include-prefix.patch` | `<hijri.h>`/`<prayer.h>` → `<itl/hijri.h>`/`<itl/prayer.h>`（Conan 下两个包 prefix 独立） |

## 功能验证

```bash
pkg-config --modversion libitl-gobject   # 期望 0.3
pkg-config --libs libitl-gobject        # 期望 -litl_gobject -litl ...
```

`test_package/test.c` 覆盖 `itl_G2H`/`itl_H2G` 往返、`itl_h_date`/`itl_g_date`/
`itl_HijriGreg`、`ItlPrayer` 生命周期、`setLocation`/`setMethod`、
`getNorthQibla`、`getPrayerTimes`（6 项）与 `getNextDayFajr`，共 **40 条断言**，
在 OHOS aarch64 上实测 `40 assertion(s), 0 failure(s)`。

> 注意 ITL 的隐式契约：`itl_G2H`/`itl_H2G` 形参名写作 `(yg,mg,dg)`，但实现按
> 位置取 **(day, month, year)**；`itl_prayer_setLocation` 的顺序是
> **(longitude, latitude, gmtDiff, dst)**；`getNorthQibla` 返回的是 ITL 自身
> 约定角度，不能按大圆地理方位角解释。详见 `0.3/notes.md`。

## 参考

- 上游: https://github.com/aelmahmoudy/libitl-gobject
- ITL: https://github.com/arabeyes-org/ITL
- Debian 打包: https://tracker.debian.org/pkg/libitl-gobject
