# wstroke 2.4.0 适配笔记

## 编译环境
- 构建系统: meson (上游) / 手动 clang 构建 (OHOS 适配)
- 编译日期: 2026-09-18
- 编译器: clang 15 (HarmonyOS PC aarch64, /data/service/hnp/bin/clang)
- 状态: built

## 上游信息
- 上游仓库: https://github.com/dkondor/wstroke
- 上游版本: v2.4.0 (tag 6190af5, peeled f115e237, 2026-08-13)
- 源码: https://github.com/dkondor/wstroke/archive/refs/tags/v2.4.0.tar.gz (sha256 8324efeea450b3bf5670b66f15a2a02ba87654fbd66752b1d57248a23f12da19)
- 许可证: ISC
- 构建系统: meson >=1.0.0, 依赖 wayfire >=0.10.0, wlroots-0.19, wayland-server, cairo, pixman, glibmm-2.4, gtkmm-3.0, gdkmm-3.0, boost-serialization, vala

## 编译步骤

上游标准编译 (Linux Wayfire 环境):
```bash
meson setup build
ninja -C build
sudo ninja -C build install
```

OHOS 适配编译 (HarmonyOS PC aarch64):
- 不使用 meson 直接构建 Wayfire 插件 (wayfire/wlroots 不可用)
- 仅编译可移植核心 `src/stroke.c` + 头文件 `src/stroke.h` (纯 C, 无外部依赖)
- 手动 clang 编译:
  ```bash
  clang -O2 -fPIC -c src/stroke.c -o stroke.o
  llvm-ar rcs libwstroke.a stroke.o
  ```
- 安装: `include/stroke.h` (+ `gesture.h` 可选), `lib/libwstroke.a`, `licenses/LICENSE`

conanfile.py 中 build() 完整复现上述步骤，并通过 `self.conf.get("tools.build:compiler_executables")` 优先使用 HMBS 注入的编译器路径。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Wayfire wlroots 依赖不可用 | OHOS 不使用 Wayfire/wlroots 合成器，wlroots 0.19 需 DRM/KMS | 放弃构建 Wayfire 插件 (shared_module wstroke) 和 GTK 配置工具 wstroke-config，仅构建 stroke 核心静态库 |
| 2 | Vala 编译器缺失 | wstroke-config 的 cellrenderertextish.vala 需 valac | 同上，仅构建 C 核心，跳过 Vala 生成 |
| 3 | gtkmm/gdkmm/boost 缺失 | OHOS 无 GTK 栈，boost-serialization 未发布到 ohpcd | 核心 stroke.c 无需这些依赖；gesture.cc 的 boost 序列化部分本次不构建，仅保留头文件 |
| 4 | 上游无测试套件 | meson.build 无 test() 定义，无 tests/ 目录，NEWS 仅记录功能 | MANIFEST 标记 upstream_tests_exist: false，并提供完整审计 |
| 5 | 源码下载稳定性 | GitHub 直连在 CI 可能超时 | conandata.yml 提供 gh-proxy 镜像 + 官方 URL 双 fallback，CI 自动重试 |

## 源码修改

无补丁。OHOS 适配通过 conanfile.py 构建逻辑实现，未修改上游源码。如需完整 Wayfire 插件，需等待 OHOS 提供 Wayfire/wlroots 移植。

## 依赖版本

- 无运行时依赖 (stroke 核心仅依赖 libc + libm)
- 构建时: clang 15, llvm-ar

## 验证结果

本地验证 (HarmonyOS PC aarch64 预检, conan create):
```bash
conan create archives/w/wstroke/2.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
- 编译: 通过 (stroke.o -> libwstroke.a)
- 上游测试: 无 (0 case, 标记 no_tests)
- test_package: 编译 test_wstroke.cpp 链接 -lwstroke, 运行验证 stroke_alloc/add_point/finish/compare

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libwstroke.a | 静态库 (stroke 核心) |
| include/stroke.h | C API 头文件 |
| include/gesture.h | C++ 手势头文件 (可选, 仅头文件) |
| licenses/LICENSE | ISC 许可证 |

## 注意事项

- 本适配仅提供手势识别算法核心，不提供 Wayfire 插件加载功能。在 OHOS 上无法作为 Wayfire 插件运行。
- 如需完整功能，需移植 Wayfire 合成器及 wlroots 到 OHOS，属高难度挑战 (路径 C)。
- 后续可扩展: 将 gesture.cc 的 boost 序列化部分适配，引入 boost/1.90.0 依赖后构建完整 C++ 手势库。
