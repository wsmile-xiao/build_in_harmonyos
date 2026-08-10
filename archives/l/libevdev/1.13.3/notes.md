# libevdev 1.13.3 适配笔记

## 基本信息
- **软件名**: libevdev
- **版本**: 1.13.3
- **构建系统**: Meson
- **上游仓库**: https://gitlab.freedesktop.org/libevdev/libevdev
- **许可证**: MIT
- **描述**: 输入设备事件处理库，libinput 的依赖

## 依赖
| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| kernel headers | - | OHOS SDK sysroot | linux/input.h, linux/input-event-codes.h |
| libm | - | 系统库 | 数学库 |
| librt | - | 系统库 | 实时库 |

## 适配要点

### 1. Meson 平台头文件查找
libevdev 的 meson.build 使用 `host_machine.system()` 查找平台特定的内核头文件：
```
input_h = dir_root / 'include' / 'linux' / host_machine.system() / 'input.h'
```
Meson 在 OHOS 上将 `host_machine.system()` 映射为 `harmonyos`，因此需要创建
`include/linux/harmonyos/` 目录，并软链接 Linux UAPI 头文件（HarmonyOS 使用 Linux 内核）。

在 conanfile.py 的 `build()` 方法中通过 `_create_harmonyos_headers()` 实现。

### 2. AR/RANLIB 工具链
Meson 需要找到 `llvm-ar` 和 `llvm-ranlib`。通过 `_inject_ar_ranlib()` 方法
从 Conan profile 的 `tools.build:compiler_executables` 推导路径并设置环境变量。

### 3. 构建产物
- 库: `libevdev.so.2.3.0` (shared) / `libevdev.a` (static)
- 工具: `libevdev-tweak-device`, `mouse-dpi-tool`, `touchpad-edge-detector`
- 头文件: `libevdev/libevdev.h`, `libevdev/libevdev-uinput.h`
- pkg-config: `libevdev.pc`

### 4. TMPDIR
HarmonyOS `/tmp` 只读 (E002)，需设置 `TMPDIR` 到用户目录。

## 编译命令
```bash
meson setup builddir --prefix=$DEFAULT_PREFIX \
  -Dtests=disabled -Dtools=enabled -Ddocumentation=disabled
ninja -C builddir -j2
DESTDIR=$TEST_PREFIX meson install -C builddir
```

## Conan 配方
```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```
---

**编译结束**: 2026-08-10 06:05
**最终状态**: built
