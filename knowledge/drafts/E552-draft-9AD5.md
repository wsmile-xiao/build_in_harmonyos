# E552 — meson GIR（generate_gir）选项化以适配无 gobject-introspection 工具链的 OHOS 目标

## 错误特征

meson 配置阶段报：

```
src/meson.build:97:19: ERROR: Dependency "gobject-introspection-1.0" not found (tried pkg-config and cmake)
```

或工具链探测失败：

```
Program g-ir-scanner found: NO
```

典型症状：上游 meson 项目**无条件**调用 `gnome.generate_gir(...)`（GObject/GLib 家族库常见），
而 OHOS 目标侧既无 gobject-introspection 的 pkg-config 描述，也无 g-ir-scanner/g-ir-compiler
可执行工具链，configure 阶段即硬失败。

## 触发条件

- 构建系统: meson
- 阶段: configuration
- 适用项目: 所有用 meson 构建、依赖 gobject-introspection 生成 GIR/typelib 的 GObject 家族库
  （GLib 系 / GNOME 系，含 libhitaki 这类 ALSA/GNOME 生态库）
- 平台: OHOS/HarmonyOS PC（目标侧无 GI 工具链；本仓 glib/at-spi2-core 配方均禁 introspection 属同型先例）

## 根因分析

1. OHOS 目标侧（aarch64-linux-ohos）不提供 gobject-introspection 工具链：
   g-ir-scanner/g-ir-compiler 不可执行，且 HMDFS 对非现场编译的既有共享库拒绝 exec mmap
   （`dlopen → Permission denied`），pygobject 亦无法加载 glib 共享库。
2. 上游 `src/meson.build` 无条件调用 `gnome.generate_gir`，且 meson 无关闭选项 →
   `dependency('gobject-introspection-1.0')` 硬失败于 configure，**库本体尚未开始编译**。
3. 该依赖只用于生成 GIR/typelib（语言绑定与文档用），对 C 库本身的编译、链接、交付无影响；
   GIR 关闭后库本体/头文件/pkg-config 可正常交付。

## 解决方案

### 推荐方案

最小补丁 + 配方选项化（默认保持上游行为，OHOS 关闭）：

1. `meson_options.txt` 新增布尔选项（默认 `true`，与上游行为一致）：

   ```meson
   option('introspection',
     type: 'boolean',
     value: true,
     description: 'Generate GObject introspection data (requires gobject-introspection toolchain)',
   )
   ```

2. `src/meson.build` 用 `get_option('introspection')` 包裹 `gnome.generate_gir(...)` 调用。
3. Conan 配方 `generate()` 中 `MesonToolchain` 传 `tc.project_options["introspection"] = "false"`
   （配合 doc 一并关闭），使 OHOS 构建不触碰 GI 依赖。

验证：无 GIR typelib 环境下，GObject 类型系统仍正常注册（`g_type_from_name` 非 0）、
glib-mkenums 生成的枚举符号仍完整——由鸿蒙专项测试（test_package/test_ohos.c）回归确认。

### 禁止做法

- ❌ 在 patches/ 中用 `__OHOS__` 平台宏做空壳 stub（R8 铁律：patches 默认禁止平台宏，空壳 stub 更违规）
- ❌ 手写假 .gir/.typelib 或伪造 g-ir-scanner（R9 欺骗检测红线）
- ❌ 因缺 GI 就整体判定 `env_unsupported` 停止适配（库本体可正常交付，属可修问题）

## 验证

```bash
# 关闭 introspection 后 meson configure/编译/安装（libhitaki 实测）
meson setup build -D doc=false -D introspection=false   # exit 0
meson compile -C build                                   # 23/23 目标, exit 0
meson install -C build                                   # exit 0

# 配方八道门禁（conan-verify G0-G4 + L2/L4/L5 全 PASS）
conan create archives/l/libhitaki/0.2.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 鸿蒙专项回归：无 GIR typelib 下类型系统注册 + 枚举值一致
ctest --test-dir <test_package build> -R test_libhitaki_ohos   # Passed
```

## 关联条目

- 相关: E179（OHOS 下共享库 dlopen Permission denied / 禁 introspection 同族方案，
  `-Dbuild_introspection_data=false` / `--disable-introspection`）
- 相关: E348（glib2 聚合 .pc 转发型 .pc，GObject 库 meson 依赖解析的另一面）
- 因果: E090（meson host_system == 'linux' 不匹配 HarmonyOS 的平台检测类问题，同属 meson+OHOS 配置面）
