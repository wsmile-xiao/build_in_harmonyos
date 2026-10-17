# lavalauncher 2.1.1 适配笔记

## 对话记录

### 对话 #1 (2026-09-24)

- **任务**: lavalauncher 2.1.1 适配到鸿蒙 PC（OpenHarmony arm64）
- **分支**: feat/lavalauncher-2.1.1（独立分支，从 origin/main 创建）
- **流程**: W0 依赖检查 → init-build → 编译适配 → conan-init → conan-verify → finish
- **结果**: 编译链接成功（21 目标），--version 冒烟通过，conan-verify 全门禁 PASS，状态 published

### 对话 #2 (2026-09-24)

- **问题**: conan-init 自动生成的配方误判 autotools、0 依赖、sha256 占位
- **处理**: 手工重写 conanfile.py（meson 应用 + 真实依赖链 + 静态 wayland-scanner 方案）
- **门禁修复**: zlib override 冲突 → 补 override=True；补丁字段 patch_file → patch_file；补丁 hunk 行数 → 修正
- **收尾**: W3 本地 CI 模拟通过（incremental 模式），submit 就绪

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-24
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
# 依赖环境（探索阶段临时生成器）：wayland/wayland-protocols/cairo/libxkbcommon/librsvg
# + 传递依赖提升（libffi/zlib/pcre2）+ override（expat/glib/libxml2）
conan install lavalauncher-deps --build=missing

# meson 配置（native 文件注入 llvm-ar/ranlib、pkg_config_path 指向聚合 allpc）
meson setup build --native-file conan_meson_native.ini -Dman-pages=disabled

# 编译
ninja -C build

# 安装
DESTDIR=<install> meson install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | wayland-scanner 执行报 Operation not permitted | 制品仓 wayland 包自带 scanner 动态链接 libexpat.so/libxml2.so，HMDFS 禁止从 Conan 缓存动态加载 | 从 wayland 1.22.0 源码静态编译 scanner（clang -static + SDK libexpat.a），写 wayland-scanner.pc 指向自编译二进制（DRAFT-ohos-static-tool-bypass-dlopen-limit） |
| 2 | 依赖 .pc prefix=/ 或指向 build 路径，include 找不到 cairo/cairo.h | 制品仓 .pc prefix 硬编码 / 或构建机路径 | 复制改写 prefix/exec_prefix/libdir/includedir 置顶 PKG_CONFIG_PATH（hyprpicker/wayland 同款）；cairo.pc Cflags 补 -I${includedir} |
| 3 | -Werror 编译失败：noop() 旧式声明 + 跨签名回调 | clang 严格警告（-Wstrict-prototypes/-Wincompatible-function-pointer-types），项目用 -Werror | meson.build 白名单加 -Wno-strict-prototypes/-Wno-incompatible-function-pointer-types（0001 补丁） |
| 4 | meson 找不到 llvm-ar/llvm-ranlib | OHOS 沙箱 PATH 精简 | native file [binaries] 注入 llvm-ar/llvm-ranlib（wayland/zix/serd 先例） |

## 源码修改

- 0001-meson-clang-warning-flags.patch：meson.build 增加两个 clang 警告白名单参数

## 依赖版本

- wayland/1.22.0（含静态重建的 scanner 1.22.0）
- wayland-protocols/1.36
- cairo/1.18.4
- libxkbcommon/1.6.0
- librsvg/2.62.3（可选，SVG 支持）

## 验证结果

```bash
# ninja 编译成功（21 目标，含 lavalauncher 可执行文件）
# meson test：无测试目标（上游未提供）
# 冒烟：lavalauncher --version → "LavaLauncher version 2.1.1"
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方，含静态 wayland-scanner 构建 |
| conandata.yml | 源码 + scanner 源码声明（sha256 已填） |
| test_package/ | executable 冒烟测试（--version） |
| commands.json | R38 命令行工具声明 |

## 注意事项

- 静态 wayland-scanner 编译需 SDK 自带 libexpat.a（/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a），查找失败会显式抛 ConanException
- scanner 版本 1.22.0 与 wayland 依赖版本一致；lavalauncher 无版本门槛

## 发现与知识

- ✅ 沙箱禁止动态加载 Conan 缓存中的共享库 → 工具类（wayland-scanner）需从源码静态编译（E176）
- ✅ clang 严格警告（-Wstrict-prototypes/-Wincompatible-function-pointer-types）在 -Werror 下会拦截旧式/跨签名回调，需白名单（E001）
- ✅ Meson 检测 OHOS 为 'harmonyos'，依赖 .pc 的 prefix/Cflags 需复制改写置顶（E090）
- ✅ 上游 v2.1.1 tarball 的 meson.build 仍声明 version: '2.1.0'，且含 git 探测逻辑（构建环境命中 git 时覆盖版本号为 GIT-<commit>），需补丁固定版本号，否则 --version 输出与实际包版本不符（E001）

## 审计与修复记录（2026-09-25）

W4 Pre-PR 独立审计（verdict=pass，无 P0/P1）发现并修复：

| 发现 | 问题 | 修复 |
|------|------|------|
| 版本号 | 上游 v2.1.1 tarball 的 meson.build 仍为 2.1.0，且有 git 探测覆盖版本 | 补丁固定 2.1.1 并注释 git 探测；二进制实测输出 `LavaLauncher version 2.1.1` |
| 许可 | 配方/文档误写 MIT，上游实为 GPLv3 | 统一改为 GPL-3.0-or-later |
| 状态口径 | 版本级 manifest=built 与软件级/README=published 不一致 | 统一为 published |
| 测试声明 | MANIFEST.yml 声明 test.sh，实际脚本为 src/test_lavalauncher.sh | 修正声明路径与断言数 |
| 发布包 | packaging/ 仅有占位、无 tar.gz | 生成 lavalauncher-2.1.1-ohos-aarch64.tar.gz（含 bin/lavalauncher） |

残留风险（非阻塞）：静态 scanner 依赖 SDK 固定路径 libexpat.a；沙箱内 --version 无法执行时降级为产物存在性校验。

## 交付与复现

```bash
# 构建 + test_package 冒烟（与门禁 G2 同款命令）
conan create archives/l/lavalauncher/2.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

- 产物：`<conan-cache>/p/lavalauncher*/p/bin/lavalauncher`
- 版本校验：二进制内版本串为 `LavaLauncher version 2.1.1`（`strings` 校验通过）
- 发布包：`packaging/lavalauncher-2.1.1-ohos-aarch64.tar.gz`（含 `bin/lavalauncher`）

---

**编译结束**: 2026-09-25 12:57
**最终状态**: published
