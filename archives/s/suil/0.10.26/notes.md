# PROGRESS: suil 0.10.26

## Build Status: SUCCESS（零补丁）

### 任务背景勘误
任务背景称 suil 构建系为 waf——基于旧版认知。实测 v0.10.26 tarball 内只有
`meson.build` + `meson_options.txt`，上游 2021 年起（David Robillard 迁移潮）
LV2 全家桶已统一从 waf 迁到 meson，仓内 `lv2/1.18.11-git` 同系（build:
system: meson）。适配按 meson 走，仓内先例：lv2（同上游作者）、c-list/c-rbtree
（MesonToolchain + PkgConfigDeps）。

### Phase 1: Init + W0 依赖检查
- [x] lv2/1.18.11-git 制品仓实测：recipe + binary 均已发布
      （`conan install --requires=lv2/1.18.11-git` 直下 package 6b129b0...）
- [x] 上游源码：gitlab.com/lv2/suil tag v0.10.26 tarball 实测下载
      sha256=7087e6eb13d4a5ebfd5be6c59277ec068bbcfe60b90db3bb58e58d79c0f2d465
- [x] tar tzf 完整性验证（61 文件，gzip 格式合法）

### Phase 2: 探索编译（零补丁一次通过）
- [x] 手写 meson cross file（system=linux, cpu_family=aarch64, clang15）
      + PKG_CONFIG_PATH 指向 conan 缓存的 lv2.pc
- [x] `meson setup` 配置通过：lv2 1.18.11 命中，x11/gtk/qt/cocoa 全部
      disabled（OHOS PC 无窗口系统接入）
- [x] `meson compile -j1` 6/6 目标编译链接通过：
      libsuil-0.so.0.10.26 + test/headers/test_headers
- [x] `meson install DESTDIR` staging 验证：
      lib/libsuil-0.so.0.10.26（+ .so.0/.so 两条符号链接，HMDFS 上正常）
      include/suil-0/suil/suil.h + lib/pkgconfig/suil-0.pc

### Phase 3: 测试
- [x] 上游测试 `test/headers:headers`：meson test 交叉编译环境默认 SKIP
      （exit 77），本机同为 aarch64 鸿蒙 PC，直接执行测试二进制
      `./build/test/headers/test_headers` → exit 0 PASS（NEEDED libc.so，
      RUNPATH $ORIGIN/../..，链接验证成立）
- [x] 上游测试注册口径：test/headers/meson.build 注册 1 个用例（suite:
      unit）；lint 套件（autoship/reuse/clang-format）默认关闭不注册
- [x] 消费者测试（test_package/test_suil.c）4 项 API 断言：
      suil_init / host_new+set_touch+free 生命周期 / ui_supported(X11,X11)∈{0,1}
      / ui_supported(Gtk,Qt) 不崩溃 → conan create 内实跑 PASS

### Phase 4: Conan 配方（conan create 一次通过）
- [x] conanfile.py：MesonToolchain + PkgConfigDeps + VirtualBuildEnv；
      GUI 后端 feature 全禁用注入 tc.project_options；ar/ranlib 从 profile
      compiler_executables 推导（c-list §6.2 先例，CI worker PATH 无 llvm-ar）
- [x] 依赖：requires lv2/1.18.11-git；tool_requires meson/1.11.0 +
      ninja/1.12.1（均制品仓在库）
- [x] conan create -pr:h/-pr:b=ohos-aarch64 --build=missing：
      主包构建 + test_package 构建 + 实跑全部通过
- [x] 包产物：libsuil-0.so.0.10.26 + symlink 链 + include/suil-0/suil/suil.h
      + lib/pkgconfig/suil-0.pc（package id 0d9469242c68c828165e31882e66247a4c85c086）

### 踩坑记录
1. **test_package 传递依赖 include**：suil.h 递归 `#include
   <lv2/core/lv2.h>`，test_package 需显式 `self.requires("lv2/...")` 才能
   拿到 lv2 头文件路径（CMakeDeps 的 suil-0 target 只带自身 include）。
2. **/tmp 只读**（E002）：nohup 日志改 $HOME 下。
3. **meson test 交叉编译 SKIP**：非失败，用 can_run/本机直跑补验。

### GUI 后端禁用说明（架构决策）
上游 PACKAGING.md 明确：主 Suil 库不依赖任何 GUI 工具包（否则每个 LV2
宿主都会硬依赖 Gtk/Qt），GUI 适配模块是独立 shared_module 按发行版环境
单独打包。OHOS PC 当前无 X11/GTK 窗口系统接入（pkg-config 无 x11/
gtk+-2.0/gtk+-3.0/Qt5Widgets），全部按上游 feature 开关 disabled——
这是上游支持的正规配置路径，非阉割。后续 GUI 框架落地后 GUI 模块可
按同款配方追加（feature 开关改 enabled + 补 requires）。

---

**编译结束**: 2026-09-16 01:00
**最终状态**: success
