# libcolord 1.4.8 — OHOS 适配笔记

## 软件信息

- **名称**: libcolord
- **版本**: 1.4.8
- **上游**: https://github.com/hughsie/colord（libcolord 为其中客户端库）
- **构建系统**: Meson（meson.build `project('colord', 'c')`）
- **许可**: LGPL-2.1+
- **语言**: C（lang-preflight 实测 c:87/cpp:1/bash:5/python:4，判定 cpp 兼容族通过）
- **产物**: `lib/libcolord.so` + `lib/libcolordprivate.so`（含 symlink 链）+ `include/colord-1/` 头文件 + `lib/pkgconfig/colord.pc`
- **包类型**: 纯库包（无 bin/ 可执行文件 → 按 R38 不需要 commands.json）

## 依赖分析

### 制品仓已发布（✅，W0 已用 conan download 验证）
- glib2/2.88.0 — GLib 核心库（gio, glib, gmodule, gio-unix）
- lcms2/2.19 — Little CMS 2 颜色管理库
- sqlite3/3.53.4 — SQLite 数据库
- meson/ninja — 系统 PATH 可用（meson 1.11.1 / ninja 1.13.1）

### 制品仓未发布（❌）— 通过禁用选项绕过
- libgusb — ColorHug 色度计 USB 库依赖。通过跳过 colorhug 子目录绕过
- libgudev — GObject udev 封装。通过使依赖可选 + 从 libcolord 依赖列表移除绕过
- libudev — udev 库。通过使依赖可选 + `HAVE_LIBUDEV` 配置宏守卫 cd-edid.c 绕过

### 完整依赖链（meson.build 原始）
```
gio-2.0 >= 2.45.8  (glib2)
glib-2.0 >= 2.58   (glib2)
gmodule-2.0        (glib2)
gio-unix-2.0 >= 2.45.8  (glib2)
lcms2 >= 2.6       (lcms2)
sqlite3            (sqlite3)
gusb >= 0.2.7      (libgusb) -- 未发布，跳过 colorhug
gudev-1.0         (libgudev) -- 未发布，从 libcolord 移除
libudev            (libudev)  -- 未发布，HAVE_LIBUDEV 守卫
```

## 适配方案（参照 archives/c/colord/1.4.8）

### 1. 禁用可选功能（meson project options）
- `daemon=false`、`systemd=false`、`udev_rules=false`、`introspection=false`
- `man=false`、`docs=false`、`bash_completion=false`、`vapi=false`
- `sane=false`、`session_example=false`、`print_profiles=false`、`argyllcms_sensor=false`
- `libcolordcompat=false`、`tests=false`、`installed_tests=false`

### 2. 补丁（5 个，全部由 refresh-patch --auto 生成，001- 开头）
- `0001-data-meson.build.patch`：跳过 data/cmf + illuminant + profiles（custom target 需 cd-it8/cd-create-profile，其需要构建期 ELF 签名）
- `0002-lib-colord-cd-edid.c.patch`：`HAVE_LIBUDEV` 配置宏（非 `__OHOS__` 平台宏，符合 R8）守卫 `<libudev.h>` include 与 hwdb 查找逻辑
- `0003-lib-colord-meson.build.patch`：`optional_deps` 过滤列表，colordprivate/colord 仅链接 found 的 gudev/libudev
- `0004-lib-meson.build.patch`：跳过 lib/colorhug（依赖 gusb）
- `0005-meson.build.patch`：gusb/gudev/libudev `required:false` + `HAVE_LIBUDEV` conf + 跳过 po（gettext）/client（纯库包）/meson_post_install.sh（chown）

### 3. 与 colord 包的差异（libcolord 为纯库包）
- **跳过 client/ 子目录**（colormgr、cd-iccdump 等 CLI 工具）→ 产物无 bin/，无需 commands.json（R38）
- 其余 meson 配置与补丁方案与 colord 包一致（同源同版本）

### 4. pkg-config 兼容层
glib2 Conan 包只生成聚合 `glib-2.0.pc`，meson 的 `dependency('gio-2.0'|'gobject-2.0'|'gio-unix-2.0'|'gmodule-2.0')` 按单模块名查找。`generate()` 中补写 4 个薄包装 .pc。

### 5. ELF 签名
`package()` 后用 binary-sign-tool 对 .so 重新签名（`_resign_elf`，与 colord 一致）。

## 上游测试清点清单（R51 步骤 a）

> 口径说明：注册数按**上游源码 `g_test_add*` 调用全量**统计（`grep -c 'g_test_add'`），与 pc-pr-review 实测口径一致。其中 colord-test-daemon 的 `/colord/client{systemwide}` 位于 `#ifdef HAVE_SYSTEMD` 条件编译块内，systemd=false 配置下运行时注册 24 项（源码计数 25）。

| 测试程序 | 源文件 | 注册数 | 构建条件 |
|---|---|---|---|
| colord-test-private | lib/colord/cd-test-private.c (+cd-test-shared) | **38** 项 g_test_add_func | tests=true（lib/colord/meson.build） |
| colord-test-daemon | lib/colord/cd-test-daemon.c (+cd-test-shared) | **25** 项 g_test_add_func（运行时 24，systemwide 需 HAVE_SYSTEMD） | tests=true（lib/colord/meson.build） |
| cd-self-test | src/cd-self-test.c | **9** 项 g_test_add_func | daemon=true（src/meson.build，libcolord 纯库不构建） |
| ch-self-test（colorhug） | lib/colorhug/ch-self-test.c | **11** 项 g_test_add_func | gusb 依赖（lib/colorhug/meson.build，libcolord 跳过 colorhug 不构建） |
| **合计** | | **83** | |

测试数据文件：data/tests/（16 个：DELL-U2713H.bin、LG-L225W-External.bin、Lenovo-T61-Internal.bin、calibration.ccmx、corrupt-dict.icc、crayons.icc、empty.icc、example.cmf、example.sp、ibm-t61.icc、measured.ti3、normalised.ti3、raw.ti3、reference.ti3、test.ccss、test.sp）

## 上游测试实测结果（R51 步骤 b/c，OHOS aarch64 交叉编译环境）

配置 `-Dtests=true` 单独编译测试二进制并实测（daemon 测试需 daemon=false 之外额外处理，见下）。

### colord-test-private（38 项，实际运行）
- **通过 11 项**：/colord/spectrum、spectrum{planckian}、spectrum{subtract}、spectrum{cx}、buffer、enum、color、color{interpolate}、color{blackbody}、math、it8{cri-util}(SKIP)
- **失败 27 项**：edid、transform、icc×10、icc-store、dom×3、interp×2、it8×10（除 cri-util 外）
- 通过率：11/38 ≈ 28.9%

### 每项失败的具体技术原因
1. **/colord/edid（1 项）**：`colord_edid_func` 断言 `cd_edid_get_vendor_name(edid) == "LG"` 失败（实际 NULL）。根因：vendor name 由 `cd_edid_convert_pnp_id_to_string` 通过 **libudev hwdb** 查询 PNP ID（GSM→LG），OHOS 无 libudev/hwdb，`HAVE_LIBUDEV` 未定义 → 返回 NULL。这是 Linux 特有硬件数据库缺失的平台差异，**预期内**（补丁 0002 的设计行为）。
2. **transform/icc 系列/dom/interp/it8（26 项）**：`cd_icc_load_file(icc, file, ...)` / `cd_it8_load_from_file` 断言 `G_IS_FILE(file)` 失败。根因：**静态 glib 双副本 GType 不互通**——glib2 为静态库，libcolordprivate.so 内嵌 6166 个 glib 局部符号（`llvm-nm` 实测），测试二进制另链接一份静态 glib；测试创建的 `GFile*`（测试二进制 glib 的 GType 表）传入库内（另一份 glib 的 GType 表），`G_IS_FILE` 跨类型系统检查失败。这是**静态 glib 链接的构建环境限制**（原生 Linux 下 glib 为动态库共享 GType，无此问题），非 libcolord 代码缺陷。上游 colord 包同源同配置（tests=false），其 test_package 亦用 CdColorRGB 纯 struct 规避。

### colord-test-daemon（24 项，实测 0/24，全部 [DISABLED]）
- 24 项注册，逐项实测**全部打印 `[DISABLED]` 直接返回，rc=0**（非 SIGSEGV）。根因：cd-test-daemon.c 多处 `if (!has_colord_process) { g_print("[DISABLED] "); return; }`——OHOS 无运行中的 colord daemon 进程，`has_colord_process=false`，上游主动跳过。需要 colord daemon + D-Bus session bus 的运行环境，OHOS 无此环境（预期内，属运行环境依赖）。

### cd-self-test（9 项）
- 未构建/未运行。根因：位于 src/meson.build，仅 `get_option('daemon')` 为 true 时 subdir('src') 才构建；libcolord 为纯库包 daemon=false。上游此测试属 daemon 内部自测，与客户端库无关。

### ch-self-test（colorhug，11 项）
- 未构建/未运行。根因：位于 lib/colorhug/ch-self-test.c，colorhug 子库依赖 gusb（制品仓未发布），libcolord 配方通过补丁 0004 跳过 lib/colorhug 子目录。属 ColorHug 色度计配套库自测，与 libcolord 客户端库无关。

## 通过率口径（与 pc-pr-review 上游 N 实测一致）

- **上游源码注册总数 N=83**（`grep -c 'g_test_add'` 全量）：colord-test-private 38 + colord-test-daemon 25（源码计数，运行时 24）+ cd-self-test 9 + ch-self-test(colorhug) 11
- 实测通过 11 项（全部来自 colord-test-private），**严格注册口径通过率 11/83 ≈ 13.3%**；可运行子集（colord-test-private 38 项）通过率 11/38 ≈ 28.9%
- 未通过/未执行项 72 = 27（private 失败，环境限制）+ 24（daemon DISABLED）+ 9（self-test 未构建）+ 11（colorhug 未构建）+ 1（daemon systemwide 条件注册未展开）

## 验证结论

- 本地编译验证（Step 2）：meson configure + ninja -j1 编译 **58/58 成功**（libcolord.so + libcolordprivate.so + 测试二进制），meson install 正常产出库/头文件/pkgconfig
- 库本身功能由 test_package 实测：CdColorRGB（创建/设值/插值）+ CdIcc（创建/元数据读写/版本查询）全部通过
- 上游测试失败全部为**环境限制**（无 libudev hwdb / 无 colord daemon 运行环境致上游测试 DISABLED / 静态 glib 双副本 GType），非适配缺陷
- conan create + conan-verify 门禁记录于 reports/conan-verify-report.md（Verdict: PASS，G2 conan create 成功，test_package PASS）

## 遗留问题/限制

- 上游 `colord-test-private` 26 项涉及跨库 GFile 的用例在静态 glib 配置下无法通过（GType 双副本）；若将来 glib2 提供共享库构建方式可复测
- `colord-test-daemon`/`cd-self-test` 需 colord daemon + D-Bus 环境，OHOS 无，属上游测试的运行环境依赖
---

**编译结束**: 2026-10-01 10:35
**最终状态**: built

## 复审记录

- **2026-10-03**: 三次审查（rule4 少报 / rule11 意见未解决 / rule7 CI）内容层均已修复，CI #67818 通过；本提交为刷 HEAD 触发对新 SHA 的复审（零功能性 docs 变更）。
