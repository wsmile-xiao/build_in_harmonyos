# gnome-menus 3.36.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15（/data/service/hnp/bin/clang）
- 目标平台: HarmonyOS PC（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

配方（conanfile.py）内完成，关键命令与顺序：

```bash
# 1) configure（AutotoolsToolchain + 本包追加项）
./configure --enable-shared --disable-static --prefix=/ \
    --bindir='${prefix}/bin' --sbindir='${prefix}/bin' \
    --libdir='${prefix}/lib' --includedir='${prefix}/include' \
    --oldincludedir='${prefix}/include' --enable-introspection=yes
# 2) 编译
make -j20
# 3) 上游官方测试（TEST_QUALITY_SPEC §3.1，autotools 包必做）
make check
# 4) 安装
make install    # 包内 lib/libgnome-menu-3.so.*、bin/gnome-menu-spec-test
```

`--enable-introspection=yes` 触发 GOBJECT_INTROSPECTION_CHECK，在 make all 阶段
生成 GMenu-3.0.gir 并编译出 GMenu-3.0.typelib（GI 运行时供 pygobject 的
`from gi.repository import GMenu` 使用，alacarte 依赖此 typelib）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报未知平台（config.guess 不识别 HarmonyOS） | 上游 config.guess/config.sub 无 ohos 识别分支 | 补丁 0001-port-for-ohos.patch：config.guess 增加 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`；config.sub 增加 `ohos-linux` 分支并把 `ohos*` 列入可接受系统名（E007） |
| 2 | config.status 生成 subs*.awk 报 Permission denied | HMDFS umask 077 | build() 内把 configure 的 `umask 077` 改写为 `umask 022`（E011） |
| 3 | GISCAN 报 `ModuleNotFoundError: No module named 'distutils'` | Python 3.12 已移除 stdlib distutils，而 giscanner/utils.py:385、ccompiler.py 在模块级 `import distutils`；系统 python 与 conan python 均不带 setuptools | 随配方自带 gi-distutils/（最小集 distutils + jaraco + more_itertools），由 g-ir wrapper 注入 PYTHONPATH |
| 4 | 修好 3 后报 `ModuleNotFoundError: No module named 'giscanner._giscanner'` | 扩展 EXT_SUFFIX 必须与运行它的 python 一致；且鸿蒙 loader 只允许 conan python dlopen 自身安装树 lib-dynload 下的扩展（E212） | wrapper 显式用 conan python 执行 g-ir-scanner，并在 generate() 把 gobject-introspection 包内 giscanner（含 _giscanner.so）复制进 conan python 的 lib-dynload 后签名 |
| 5 | g-ir-scanner 解析 `--library` 报 can't resolve libraries | giscanner/shlibs.py 调 `ldd`，鸿蒙 PC 无 ldd（hnp/usr/system bin 均无） | wrapper 旁生成 ldd shim（`llvm-readelf -d` 输出 ldd 风格），并前置 PATH；同时补 PKG_CONFIG_PATH 指向 conan generators |
| 6 | libtool 警告 `library libffi.la was moved` | 依赖包路径在该次构建中变化 | 警告级，不影响产物；libmenu 链接与 typelib 生成均正常 |

## 源码修改

单一补丁 `patches/0001-port-for-ohos.patch`（portability）：
- `config.guess`：case 首位新增 HarmonyOS 分支，覆盖 aarch64/arm/x86_64/i?86
- `config.sub`：新增 `ohos-linux` → `os=linux-ohos`；系统名可接受列表加入 `ohos*`

配方内未改动上游 C 源码（除上述补丁与 configure umask 外）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib | 2.84.0.1（共享） | libmenu 核心依赖；typelib 运行时需 dlopen libglib-2.0.so.0 |
| gobject-introspection | 1.78.1.1 | GObject Introspection 工具链（g-ir-scanner/g-ir-compiler）+ GLib/GObject/Gio typelib |
| libintl | 0.26.1 | 合并 libintl.so.8（libintl_* + g_libintl_* 双符号），g-ir-scanner 进程内 python 与共享 glib 共存 |

## 验证结果

### 上游官方测试（层 1）

```bash
$ make check
Making check in libmenu
make[1]: Nothing to be done for 'check'.
Making check in desktop-directories
make[1]: Nothing to be done for 'check'.
Making check in layout
make[1]: Nothing to be done for 'check'.
Making check in util
make[1]: Nothing to be done for 'check'.
Making check in po
make[1]: Nothing to be done for 'check'.
$ echo $?
0
```

**上游用例数 = 0（实测，非省略）**：无 tests/ 目录；5 个子目录 Makefile.am 均无
`TESTS=` / `check_PROGRAMS` / `check-local` / `check_SCRIPTS`；
`util/test-menu-spec.c` 注册为 `noinst_PROGRAMS = gnome-menu-spec-test`（交互式
菜单布局打印工具，人工核对用，`make check` 不执行）；`m4/progtest.m4` 是 gettext
autoconf 宏。统计命令与命中项核实见 test_package/MANIFEST.yml 头部注释。

### test_package（层 2，消费者视角）

```bash
$ clang test_gmenu.c -o test_gmenu -I<pkg>/include ... -lgnome-menu-3
$ GMENU_TEST_LOG=test_gmenu_summary.txt LD_LIBRARY_PATH=<pkg>/lib:<glib>/lib ./test_gmenu
[PASS] sandbox temp dir created: /storage/Users/currentUser/gmenu-test-XXXXXX
[PASS] sandbox menu/apps/directories written under ...
[PASS] gmenu_tree_new("applications.menu") != NULL
[PASS] gmenu_tree_load_sync() == TRUE
[PASS] canonical menu path inside sandbox: .../config/menus/applications.menu
[PASS] gmenu_tree_get_root_directory() != NULL
[PASS] root directory name == "Applications" (got "Applications")
[PASS] root menu id == "Applications" (got "Applications")
[PASS] gmenu_tree_directory_iter(root) != NULL
[PASS] iter yielded a submenu
[PASS] submenu name == "Accessories" (got "Accessories")
[PASS] submenu .directory resolved: .../desktop-directories/ohos-test.directory
[PASS] submenu menu id == "Accessories" (got "Accessories")
[PASS] gmenu_tree_directory_iter(submenu) != NULL
[PASS] submenu iter yielded an entry
[PASS] entry GDesktopAppInfo != NULL
[PASS] entry display name == "OHOS Test App" (got "OHOS Test App")
[PASS] entry Exec resolved: /bin/true
[PASS] entry desktop file id == "ohos-test-app.desktop" (got "ohos-test-app.desktop")
[PASS] exactly 1 submenu in root (got 1)
[PASS] no entries directly under root (got 0)
[PASS] exactly 1 entry collected from Accessories submenu (got 1)
[PASS] gmenu_tree_get_entry_by_id("ohos-test-app.desktop") != NULL
[PASS] entry-by-id has GDesktopAppInfo
[PASS] gmenu_tree_get_root_directory() stable on re-read
[SUMMARY] assertions=25 failures=0
test_gmenu OK
$ echo $?
0
```

`conan create` 端到端实测（本机 = CI 同款 OpenHarmonyPC 设备）：

```
gnome-menus/3.36.0 (test package): [PASS] test_gmenu: [SUMMARY] assertions=25 failures=0
gnome-menus/3.36.0 (test package): [PASS] GMenu-3.0.typelib present
```

### 产物校验

| 产物 | 路径 | 说明 |
|------|------|------|
| 共享库 | lib/libgnome-menu-3.so.0.0.1（soname libgnome-menu-3.so.0） | 保留上游 ABI |
| typelib | lib/girepository-1.0/GMenu-3.0.typelib | GI 运行时（pygobject `from gi.repository import GMenu`） |
| GIR | share/gir-1.0/GMenu-3.0.gir | 接口描述（g-ir-compiler 已消费生成 typelib） |
| 头文件 | include/gnome-menus-3.0/gmenu-tree.h | 消费者编译用 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libgnome-menu-3.so.0.0.1 | 133,504 B（约 130 KB） | 菜单规范实现（libmenu）；soname libgnome-menu-3.so.0 |
| lib/girepository-1.0/GMenu-3.0.typelib | 5,836 B | GI 运行时 typelib |
| share/gir-1.0/GMenu-3.0.gir | 44,231 B | GIR 描述 |

## 注意事项

- 本包依赖 gobject-introspection/1.78.1.1（GI 工具链）与 libintl/0.26.1（合并双符号），
  两者为同批发布的 infra 包；g-ir wrapper 的 PYTHONPATH/LD_LIBRARY_PATH 由本配方
  自持（构建 env 不传播到 make 子进程）。
- test_gmenu.c 只验证 API 路径与菜单解析逻辑，不依赖桌面环境（沙箱 XDG 树）；
  因此可在 CI 无桌面环境下确定性通过。测试程序内存管理已做过压测
  （连续 30 次运行：30/30 退出码 0、均为 assertions=25 failures=0），无间歇性崩溃。
- 上游无自动化用例，后续上游若引入 tests/，`make check` 会自动纳入（配方已固化该调用）。
- 本地预 CI 复现命令（本机即 CI 同款设备）：

  ```bash
  conan create archives/g/gnome-menus/3.36.0 \
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
      --build=gnome-menus/*
  ```
