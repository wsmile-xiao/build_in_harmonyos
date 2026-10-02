# libadwaita 1.8.8 测试报告

## 环境

- 目标平台: OHOS aarch64（conan 交叉编译，**无显示服务**——GTK4 Broadway-only
  后端约束，broadwayd 签名约束下不可运行）
- 主依赖: gtk4/4.22.4、glib/2.84.0.1.1（shared）、fribidi/1.0.16、
  appstream/1.2.0（1.8.x 新增 required）、sassc/3.6.2（build-time）
- 构建: meson（-Dtests=true 全量，535 目标 0 FAILED，约 7 分钟）

## 1. Conan 配方验证（conan-verify 门禁）

| 门禁 | 结果 |
|------|------|
| G0 预构建风险评估 | PASS |
| G1 配方完整性 | PASS |
| G2 conan create（干净构建） | PASS（535 目标 0 FAILED） |
| G3 系统同名库隔离 (R26) | PASS |
| G4 产物完整性 | PASS（libadwaita-1.so / libadwaita-1-internal.a / 85 头文件） |
| L2/L4/L5 smoke/安全/基线 | PASS |

## 2. test_package 无显示探针（124 checks）

```
libadwaita-1.8.8 no-display probe: checks=124 PASS   (exit 0)
(105/105 upstream-ported assertions included)
```

| 段 | 覆盖 | 数量 |
|----|------|------|
| A | 版本/初始化态（消费者扩展）：adw_get_major/minor/micro_version、ADW_*_VERSION 宏、ADW_CHECK_VERSION 正/反、adw_is_initialized()==FALSE | 7 |
| B | easing：**1:1 移植上游 tests/test-easing.c 全部 70 条断言**（35 值 × f(0)≈0/f(1)≈1，eps 0.005 = 上游 g_assert_cmpfloat_with_epsilon 契约）+ 消费者扩展 7 条（解析值 + 单调性） | 77 |
| C | accent-color：**1:1 移植上游 tests/test-accent-color.c 的 35 条公共 API 断言**（to_rgba 精确 hex 9 + to_standalone_rgba 18 + rgba_to_standalone 8） | 35 |
| D | spring-params（消费者扩展，上游 1.8.8 无对应测试）：new + damping_ratio/mass/stiffness/派生量 damping==2ζ√(mk)==20.0（GBoxed，adw_spring_params_unref 释放） | 5 |

**合计 124/124，其中 105 条为上游断言 1:1 移植（105/105 = 100%）**。
方法论: E471 无显示 API 探针（从 gtkmm 4.0.0.1 C++ 绑定扩展至 C 原生）。
探针不调用 adw_init()/gtk_init()（display 依赖）。

**不可移植子集说明**：上游 test-accent-color.c 其余 137 条断言
（nearest_from_rgba roundtrip 10 + 调色板 127）调用
`adw_accent_color_nearest_from_rgba()`——该函数仅声明于私有头
`src/adw-accent-color-private.h`，未从 libadwaita-1.so 导出
（nm -D 实证）；上游测试二进制因链接内部静态库
libadwaita-1-internal.a 可用该符号，消费者不可用。该 137 条分类为
"私有 API 子集"，不入探针（详见 notes.md）。

## 3. 上游测试（R51 三步法）

- **清点**: tests/meson.build `test_names` 列表 = **63** 项，构建全部成功
- **实跑**: **63/63**（env: GSETTINGS_BACKEND=memory GTK_A11Y=none
  G_TEST_SRCDIR/G_TEST_BUILDDIR，每测试 10s 超时）
- **通过**: **0**（63/63 同因失败，非断言失败）
- **失败模式（63/63 同因）**: `gtk_test_init` → `gtk_init` →
  `Gtk-WARNING: Failed to open display` → g_log fatal → `__builtin_trap()`
  → SIGTRAP（rc=-5）
- **分类（E471 口径）**: display 阻塞 63/63——OHOS 无显示服务。其中 61 项
  创建 widget（display 依赖，无法无显示执行）；**2 项纯计算测试
  （test-easing / test-accent-color）的公共 API 断言已 1:1 移植到
  test_package 无显示执行：105/105（100%）PASS**（test-easing 70 +
  test-accent-color 公共 API 35；另 137 条依赖私有 API 不可移植，见第 2
  节）——即可执行子集通过率 100%，0 断言失败
- **次要环境问题**（非致命，记录备查）: `Fontconfig error: Cannot load
  default config file: File not found`（fontconfig/2.18.1.1 包缺默认
  fonts.conf，未来显示链路可用前需处理）
- **证据（已入仓）**: `upstream-tests/`（summary.txt + 63 份 .out 全量
  原始输出 + run-upstream-tests.py 复现 runner + README.md）

## 4. 上游测试用例修改说明

唯一修改 = 补丁 0001-tests-ignore-deprecations.h.patch（portability，
+5/-1）：`g_log_get_always_fatal()`（GLib 2.86+）→
`g_log_set_always_fatal(G_LOG_LEVEL_ERROR)` 捕获返回值（GLib 2.80+ 稳定
ABI：setter 内部 `|= G_LOG_LEVEL_ERROR` 并返回旧 mask）。仅影响
test-flap / test-preferences-window 两个测试二进制的编译，**不改变任何
测试断言与语义**。

## 5. 补全测试用例说明

test_package/test.c 124 项无显示 checks（见第 2 节），其中 105 项为上游
test-easing / test-accent-color 公共 API 断言的 1:1 移植，另 19 项为
消费者扩展（版本/初始化态 7、easing 解析值与单调性 7、spring-params
5——上游 1.8.8 无 test-spring-params）。上游 63 个测试中 61 个 display
依赖，无显示环境下不可执行；可执行的纯计算子集之公共 API 断言已全量
移植覆盖（R34 合规，ok 累积决定退出码）。

## 结论

无显示功能验证全部通过；display 依赖部分（63/63 上游测试）受 OHOS 平台
无显示服务限制阻塞，按 E471 口径分类留证。配方可发布。
