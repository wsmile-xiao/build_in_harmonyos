# boops 1.0.0 适配笔记

## 编译环境
- 构建系统: make
- 编译日期: 2026-09-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

上游 BOops 使用纯 Makefile，通过 pkg-config 检测依赖（lv2、sndfile、x11、cairo）。
在 HarmonyOS 上采取 DSP-only 策略，避开 X11/cairo GUI 依赖：

```bash
# 1. 配置 PKG_CONFIG_PATH 指向 conan 依赖的 pkgconfig 目录
export PKG_CONFIG_PATH="<lv2>/lib/pkgconfig:<libsndfile>/lib/pkgconfig:$PKG_CONFIG_PATH"
# 2. 仅构建 DSP
make -C BOops-1.8.2 -j1 CC="clang" CXX="clang++" AR="llvm-ar" BOops.so
# 3. 打包到 LV2 bundle
mkdir -p $PREFIX/lib/lv2/BOops.lv2
cp BOops.lv2/BOops.so BOops.lv2/*.ttl LICENSE $PREFIX/lib/lv2/BOops.lv2/
```

实际 conanfile.py 中通过 `self.run(..., env="conanbuild")` 执行上述命令，
并通过 conanbuild_env 脚本自动注入 PKG_CONFIG_PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `check` 目标要求 x11/cairo 导致构建失败 | 上游 Makefile 的 check 需 4 个 pkg-config 包 | 绕过 check，直接构建 `BOops.so` 目标，DSP 仅需 lv2+sndfile |
| 2 | LV2 头文件路径 `lv2/lv2plug.in/ns/lv2core/lv2.h` 找不到 | 上游旧代码使用旧 LV2 路径，新 LV2 1.18+ 使用 `lv2/core/lv2.h` | 在 generate 阶段创建兼容 symlink `lv2plug.in/ns/lv2core -> ../../core` 等 |
| 3 | OHOS 上 `lld` 启动报 `libxml2.so.16` 找不到 | OHOS SDK 的 lld 依赖 libxml2，但不在默认搜索路径 | 参考 dragonfly-reverb 经验，探测 SDK 目录并设置 LD_LIBRARY_PATH |
| 4 | `BOops.lv2` bundle 的 TTL 未自动复制 | 仅构建 DSP 时 Makefile 不执行 BUNDLE 复制逻辑 | 手动复制 `manifest.ttl`、`BOops.ttl`、`LICENSE` 到 BOops.lv2 目录 |

## 源码修改

无补丁。OHOS 适配通过构建选项与环境变量完成，无需修改上游源码。

## 依赖版本

- lv2/1.18.11-git
- libsndfile/1.2.2（其传递依赖如无）

## 验证结果

```bash
# 本地 conan create（HMBS 真机预检）
conan create archives/b/boops/1.0.0 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：conan create 成功，test_package 验证 BOops.lv2 bundle
# 上游无官方测试套件，验证以 test_package 为主：bundle 存在性、ELF 魔数、lv2_descriptor 符号导出
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/lv2/BOops.lv2/BOops.so | DSP 共享库（LV2 插件） |
| lib/lv2/BOops.lv2/manifest.ttl | LV2 manifest |
| lib/lv2/BOops.lv2/BOops.ttl | 插件描述 |

## 注意事项

- GUI (`BOopsGUI.so`) 在 OHOS 上未构建，宿主将回退到通用 LV2 UI 或无 UI 模式。
- 上游 1.8.2 源码标记为 1.0.0 配方版本，实际源码内容为 1.8.2（最新稳定版），因官方无 1.0.0 tag。
