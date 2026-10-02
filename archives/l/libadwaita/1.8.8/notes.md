# libadwaita 1.8.8 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-28
- 编译器: clang/clang++（OHOS aarch64，conan MesonToolchain）
- 状态: built（本地 conan create 全绿，CI 验证中）

## 编译步骤

```
conan create archives/l/libadwaita/1.8.8/conanfile.py --build=missing
```

1. 源码：官方 tar.xz（sha256 校验）下载解压
2. meson setup --buildtype=release -Dintrospection=disabled -Dvapi=false
   -Ddocumentation=false -Dexamples=false -Dtests=true
3. ninja（535 目标，含全部上游测试二进制）
4. 主配方 generate() 三个关键动作：
   - PkgConfigDeps：为 Meson 产出 gtk4/glib-2.0/gio-2.0/fribidi/appstream/sassc 的 .pc
   - `_normalize_glib_pc()`：PkgConfigDeps 之后强制回写 6 个 glib 系 .pc
     （prefix 指向 glib/2.84.0.1.1 包目录，glib-2.0.pc 补 `-lintl`）
   - glib 组件键别名注入：为 `glib::gobject` / `glib::gmodule` /
     `glib::gthread` / `glib::gio` 注入无后缀键别名（libxmlb/0.3.19
     以无后缀键引用 glib 组件）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 pango 版本冲突 | gtk4 图内固定 pango/1.56.4，主配方依赖解析出现双版本 | `self.requires("pango/1.5.6.4", override=True)` + zstd/1.5.7 override 统一到 gtk4 链（不降版本） |
| 2 | G2 glib 组件键冲突（meson 依赖解析失败） | libxmlb/0.3.19（appstream 依赖）引用无 `::gobject` 后缀的 glib 组件键 | 主配方 generate() 注入 4 组键别名（`glib::gobject`→`glib` 等），test_package 同款注入 |
| 3 | `undefined reference to g_libintl_*`（`--no-undefined` 链接必炸） | 1.8.x 新增 adw-main.c / adw-tab-overview.c 直调 `g_libintl_dngettext`；PkgConfigDeps 生成的 glib-2.0.pc Libs 只有 `-lglib-2.0` 缺 `-lintl`；glib/2.84.0.1.1 包自带 libintl.so.8（12 个 T `g_libintl_*` 定义，自洽） | `_normalize_glib_pc()` 强制回写 6 个 glib 系 .pc：prefix 统一指向 d610 包目录 + glib-2.0.pc 补 `-lintl`（1.2.0 无此直调故幸免） |
| 4 | `g_log_get_always_fatal()` 链接错误 | 该符号 GLib 2.86+ 才有；ohpcd glib/2.84.0.1.1 只有 setter（2.80+，返回旧 mask） | 补丁 0001：tests/ignore-deprecations.h 改 `g_log_set_always_fatal(G_LOG_LEVEL_ERROR)` 捕获返回值（语义等价上游：抑制+恢复）；仅影响 535 目标中的 2 个（test-flap / test-preferences-window） |
| 5 | test_package GdkRGBA 20 个编译错误 | 成员名是 `.red/.green/.blue/.alpha`（非 `.r/.g/.b/.a`） | 修正成员名 |
| 6 | easing 探针端点断言失败（enum 22/24） | 源码 elastic 族公式端点并非精确 0/1：ease_in_elastic(0) = -4.88e-4、ease_in_out_elastic(0) = 8.48e-5（无 t==0 特判）；上游 test-easing.c 本身就用 epsilon 0.005 断言 | 探针端点容差对齐上游契约 0.005（非放宽，是同源） |
| 7 | 探针 D 段 SIGSEGV（fault @0x1，g_object_run_dispose 内） | **test.c 自身 bug**：AdwSpringParams 是 GBoxed（`G_DEFINE_BOXED_TYPE` + gatomicrefcount），对它调用 `g_object_unref()` = UB——mass 字段（double 1.0）的位模式被当对象弱引用链指针解引用 | 改用 `adw_spring_params_unref(sp)`；D0/D1 真 GObject 对照组验证 glib/gobject 链本身健康 |
| 8 | .so 运行行为偏离源码（elastic 值异常，源码反汇编/ md5 一致却对不上） | **共享 conan 缓存陈旧 .so 污染**：09-14 旧会话残留 libadwaita/1.8.8 缓存（旧 recipe revision / 旧源码），conan 目录名哈希碰撞导致陈旧 build/package 目录被复用，运行加载了陈旧 .so | `conan remove "libadwaita/*" -c` 全清 + clean-room 重建；教训：多任务并行共享缓存的机器上，正式构建前先清本包旧条目 |
| 9 | meson 触发 appstream subproject 全源码 clone（离线必败） | 1.8.x 起 appstream 为 required 依赖（无 required:false，带 subproject fallback） | PkgConfigDeps 产出 appstream.pc（appstream/1.2.0 已发布） |
| 10 | `gtk_doc` meson 选项报错 | 1.8 起 deprecated | 改用 `-Ddocumentation=false` |

## 源码修改

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-tests-ignore-deprecations.h.patch（portability，+5/-1） | tests/ignore-deprecations.h | `g_log_get_always_fatal()`（GLib 2.86+）→ `g_log_set_always_fatal(G_LOG_LEVEL_ERROR)` 捕获返回值（GLib 2.80+ 稳定 ABI：setter 内部强制 `\|= G_LOG_LEVEL_ERROR` 并返回旧 mask）。临时态 = GLib 默认基线（errors always fatal），与上游"抑制 ERROR-fatal 再恢复"语义等价。不影响主库与 libadwaita-1.so 链接，仅涉及 2 个上游测试二进制（test-flap / test-preferences-window） |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| gtk4 | 4.22.4 | 主依赖（Broadway-only 后端约束） |
| glib | 2.84.0.1.1 | shared=True，.pc 强制回写目标 |
| fribidi | 1.0.16 | |
| appstream | 1.2.0 | 1.8.x 新增 required |
| sassc | 3.6.2 | tool_requires（样式编译） |
| pango | 1.56.4 | override 统一到 gtk4 链 |
| zstd | 1.5.7 | override 统一到 gtk4 链 |
| zlib | 1.3.1.1 | 传递 |
| fontconfig | 2.18.1.1 | 传递 |

## 验证结果

### 无显示探针（test_package，124 checks 全 PASS，exit 0）

```
conan create archives/l/libadwaita/1.8.8/conanfile.py --build=missing
  → libadwaita/1.8.8@ohpcd/stable: Created package revision
  → test_package: libadwaita-1.8.8 no-display probe: checks=124 PASS
    (105/105 upstream-ported assertions included)
```

- A 版本/初始化态（7，消费者扩展）：adw_get_major/minor/micro_version、
  版本宏、ADW_CHECK_VERSION 正/反、adw_is_initialized()==FALSE（pre-init）
- B easing（77）：**1:1 移植上游 tests/test-easing.c 全部 70 条断言**
  （35 值 × f(0)≈0 / f(1)≈1，eps 0.005 = 上游
  g_assert_cmpfloat_with_epsilon 契约）+ 消费者扩展 7 条（LINEAR/IN_QUAD/
  OUT_QUAD/IN_CUBIC/OUT_CUBIC/IN_OUT_QUAD 解析值 + ADW_EASE_IN 单调性，
  上游仅查端点）
- C accent-color（35）：**1:1 移植上游 tests/test-accent-color.c 的
  35 条公共 API 断言**（to_rgba 精确 hex 9 + to_standalone_rgba 18 +
  rgba_to_standalone 8）
- D spring-params（5，消费者扩展——上游 1.8.8 无 test-spring-params）：
  adw_spring_params_new + damping_ratio/mass/stiffness/派生量
  damping == 2ζ√(mk) == 20.0；GBoxed 用 adw_spring_params_unref 释放

**合计 124/124 checks，其中 105 条为上游断言 1:1 移植**
（test-easing 70 + test-accent-color 公共 API 35）。

**上游 test-accent-color.c 其余 137 条断言（nearest_from_rgba roundtrip
10 + icon/elementary/KDE/Ubuntu/Cinnamon/COSMIC/macOS 调色板 127）不可
移植到消费者上下文**：它们调用 `adw_accent_color_nearest_from_rgba()`，
该函数**仅声明于私有头 `src/adw-accent-color-private.h`**（公共头
adwaita/ 无此声明），且**未从 libadwaita-1.so 导出**（实证：
`nm -D libadwaita-1.so.0 | grep nearest` 为空；同一文件中的 to_rgba /
to_standalone_rgba / rgba_to_standalone 均正常导出）。上游测试二进制
能链接该符号是因为 meson 将 tests 链接到内部静态库
libadwaita-1-internal.a（含全部符号，无可见性过滤）——消费者（conan
test_package）只能链接已安装的 .so，故这 137 条按 E471 口径分类为
"私有 API 子集，消费者上下文不可执行"，随 63/63 display 阻塞台账一并
留证（见 upstream-tests/README.md）。

### 上游测试（R51 三步法）

- 清点：tests/meson.build `test_names` 列表 63 项，构建全部成功（535 目标 0 FAILED）
- 实跑：63/63（env：GSETTINGS_BACKEND=memory GTK_A11Y=none
  G_TEST_SRCDIR/G_TEST_BUILDDIR；每测试 10s 超时）
- 通过：0
- 失败模式（63/63 同因）：`gtk_test_init` → `gtk_init` →
  `Gtk-WARNING: Failed to open display` → g_log fatal →
  `__builtin_trap()` → **SIGTRAP（rc=-5，不是 exit 1）**
- 分类（E471 口径）：display 阻塞 63/63——OHOS 无显示服务（GTK4
  Broadway-only 后端，broadwayd 签名约束下不可运行）。63 项中 61 项创建
  widget（display 依赖）；**2 项纯计算测试（test-easing /
  test-accent-color）的公共 API 断言已 1:1 移植到 test_package 无显示
  执行：105/105（100%）PASS**（test-easing 70 + test-accent-color 公共
  API 35；test-accent-color 另 137 条 nearest_from_rgba 断言依赖私有 API
  不可移植，见上节）——即可执行子集通过率 100%，失败 0
  （display 阻塞项均为平台分类，非断言失败）
- 次要环境问题（非致命，记录备查）：`Fontconfig error: Cannot load
  default config file: File not found`（fontconfig/2.18.1.1 包缺默认
  fonts.conf，未来显示链路可用前需处理）
- 证据：**已入仓** `upstream-tests/`（本目录：summary.txt + 63 份 .out
  全量原始输出 + run-upstream-tests.py 复现 runner + README.md）

### 上游测试用例修改说明

- 唯一修改 = 补丁 0001（ignore-deprecations.h）：GLib 2.86→2.84 API
  兼容（getter→setter 返回值），不改变任何测试断言与测试语义

### 补全测试用例说明

- test_package/test.c：24 项无显示探针（E471 方法论，从 gtkmm 4.0.0.1
  C++ 绑定的无显示 API 探针方案扩展到 C 原生 GNOME UI 库）——上游
  64 个测试（63 二进制）全部 display 依赖，无显示环境下上游测试
  覆盖为 0，本探针提供版本/easing/颜色/物理参数的实质功能验证

## 注意事项

- OHOS 无显示：探针不调用 adw_init()/gtk_init()；widget 类 API
  （所有需要 gtk_init 的类型）与 adw_init 本身 display 依赖，不在
  无显示探针范围
- 配方中两处 glib 特殊处理（`_normalize_glib_pc` + 组件键别名注入）
  与 gtk4/glib 链强绑定：gtk4 或 glib 版本变更时需重新验证
- AdwSpringParams 是 GBoxed 不是 GObject——后续补探针时勿混淆
  ref/unref API（本次 D 段 SIGSEGV 的根因）
- 共享 conan 缓存环境（同机多任务并行）正式构建前先
  `conan remove "libadwaita/*" -c` 清旧条目，防陈旧 .so 污染
- CI 构建超时：默认 3600s 充足（本包全量构建约 7 分钟）
---

**编译结束**: 2026-09-28 19:41
**最终状态**: built
