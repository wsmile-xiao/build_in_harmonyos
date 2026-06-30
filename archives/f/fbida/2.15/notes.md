# fbida 2.15 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `meson setup build-meson --prefix=$DEFAULT_PREFIX -Dpng=enabled -Dtiff=enabled -Dgif=disabled -Dwebp=disabled -Dmotif=disabled -Dpdf=disabled`
2. `ninja -C build-meson`
3. `ninja -C build-meson install DESTDIR=$TEST_PREFIX` (staging)
4. `ohc-run.py package fbida 2.15` (预编译包制作)
5. `ninja -C build-meson install` (本地安装)
6. ELF 签名后验证: `exiftran --help` ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson.build 强制依赖 libdrm/libinput/libudev/xkbcommon | OpenHarmony 无 DRM/input 子系统 | 修改 meson.build: `required : false` + `have_fb_deps` 条件判断 |
| 2 | poppler/cairo 强制依赖 | fbi/fbpdf/fbcon 不需要 | `required : false` + 条件构建 |
| 3 | jpeg-version.sh 依赖 cpp | OHOS 无 cpp 命令 | 添加 fallback: 直接输出 "62" |
| 4 | target_machine.system() == 'linux' 检查 | OHOS 不被识别 | 添加 `or target_machine.system() == 'ohos'` |
| 5 | python3 需要 LD_PRELOAD libintl.so.8 | 系统 python3 缺 libintl | 通过 sh wrapper 设置 LD_PRELOAD |

## 可构建的组件
- **exiftran** ✅ (always, needs jpeg+exif+pixman+math)
- **thumbnail.cgi** ✅ (needs only exif)
- **fbi** ❌ (needs DRM+input+udev+xkbcommon+cairo)
- **fbpdf** ❌ (needs DRM+input+poppler+cairo)
- **fbcon** ❌ (needs DRM+input+cairo+glib+tsm+linux)
- **ida** ❌ (needs Motif/X11)
- **kbdtest/vttest** ❌ (needs DRM+input)

## 源码修改

### 0001-meson.build.patch
- Make DRM/input/udev/xkbcommon/cairo/poppler deps optional (`required: false`)
- Add `have_fb_deps` conditional variable
- Wrap fbi/fbpdf/fbcon/kbdtest/vttest builds in `if have_fb_deps` conditionals
- Add `or target_machine.system() == 'ohos'` for SYSTEM_LINUX check
- Add `check: true` to jpeg-version.sh run_command

### 0002-scripts-jpeg-version.sh.patch
- Add fallback for platforms without cpp command
- Default output: "62" (libjpeg-turbo 2.x)

## 依赖版本

| 依赖 | 版本 | 备注 |
|------|------|------|
| libexif | 0.6.25 | pkg-config |
| pixman-1 | 0.46.4 | pkg-config |
| libjpeg | 2.1.5.1 (turbo) | cc.find_library |
| libpng | 1.6.43 | pkg-config |
| libtiff-4 | 4.6.0 | pkg-config |

## 验证结果

```bash
$ exiftran --help
usage: exiftran [ options ] file

transform options:
  -a         automatic (using exif orientation tag)
  -9         rotate by 90 degrees clockwise
  ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fbida-2.15-ohos-aarch64.tar.gz | 2770KB | 预编译包 |
| fbida-2.15-ohos-aarch64-debug.tar.gz | 2038KB | 调试符号包 |
| 0001-meson.build.patch | 229行 | OHOS平台适配 |
| 0002-scripts-jpeg-version.sh.patch | 536字节 | cpp fallback |

## 注意事项

- fbida 构建系统实际是 meson（不是 autotools），init-build 识别错误
- exiftran 是唯一可用的可执行文件（framebuffer 工具需要 DRM/input）
- python3 脚本执行需要 LD_PRELOAD=libintl.so.8 workaround
---

**编译结束**: 2026-05-30 17:31
**最终状态**: built
