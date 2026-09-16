# blur 1.1.3 适配笔记

> 上游：https://github.com/sonald/blur-effect （deepin 离屏高斯模糊工具，tag 1.1.3）
> 产物：`blur_image` 命令行工具（OpenGL ES 3.0 离屏渲染）

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-09
- 编译器: clang/clang++ 15（设备原生构建，非交叉）
- 状态: built

## R51 上游测试清点（上游 N=0 证据）

| 清点方法 | 结果 |
|---|---|
| CMakeLists.txt 全文 grep `enable_testing\|add_test\|make check\|check:` | 无任何匹配 |
| 源码树 `ls tests test` | 目录不存在 |
| 上游仅 2 个源文件：src/blur_image.cc（960 行主程序）、src/main.cc（473 行 demo，BUILD_DEMO=off 不构建） | 无测试代码 |

**结论：上游 1.1.3 无任何测试用例（N=0），适配后补全鸿蒙侧测试（test_package + smoke）。**

## 编译步骤

```bash
# 依赖环境（conan 私有 prefix，R49）
conan install --requires=gdk-pixbuf/2.44.6.1 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -g PkgConfigDeps
source conanbuild.sh

# 构建
cd <src> && mkdir build && cd build
PKG_CONFIG_PATH=<deps-dir> cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -j4
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游依赖 libdrm/gbm/pkg-config egl/glesv2 全缺失 | OHOS 无 /dev/dri、无 libgbm；系统 EGL/GLESv3 无 .pc 文件 | 源码改 EGL_DEFAULT_DISPLAY + pbuffer surface（替代 GBM/DRM 路径）；EGL/GLESv3 直接链系统库（-lEGL -lGLESv3，裸 clang 默认 sysroot 可见，实测先例本任务 egl_probe） |
| 2 | `cmake_minimum_required(VERSION 2.8.11)` 被 cmake 4.1.2 拒绝 | cmake 4.x 移除 <3.5 兼容 | 补丁升到 3.10（同上游 PR#7 / nixpkgs cmake-4.patch 方向） |
| 3 | 链接错误 `unable to find library -lwebp/-lglib-2.0/...` | pkg_check_modules 只在 CMake 目标属性带 libdir，裸 `target_link_libraries(${DEPS2_LIBRARIES})` 不注入 `-L` | CMakeLists 补 `link_directories(${DEPS2_LIBRARY_DIRS})` |
| 4 | `getopt` 不识别 `blur_image test.png -o out.png`（infile 在前） | musl getopt 无 GNU 参数重排（glibc 扩展） | 选项前置调用即可（`blur_image -o out.png test.png`），未改源码 |
| 5 | shader 编译错误 P0005 `#version must be on the first line` | 上游 `R"(\n#version` 字面量带前导换行；Linux Mesa 容忍，OpenHarmony GLES 严格 | 7 处 shader 改 `R"(#version` 贴起始 |
| 6 | shader 编译错误 L0002 `No matching function for call to 'texture2D'` | GLSL ES 3.00 已废弃 texture2D（ES 1.00 函数）；Mesa 宽松接受，OHOS 严格 | `#define texpick texture2D` → `#define texpick texture`（2 处） |

## 源码修改（2 个补丁，全部 portability，均无 __OHOS__ 宏）

1. **0001-CMakeLists.txt.patch**（构建系统）：
   - cmake_minimum_required 2.8.11 → 3.10（cmake 4.x 拒绝 <3.5，同上游 PR#7 / nixpkgs cmake-4.patch 方向）
   - DEPS2 移除 libdrm/gbm/egl/glesv2（OHOS 无 DRM 渲染节点；EGL/GLESv3 直链平台库）
   - target_link_libraries 补 `EGL GLESv3`；补 link_directories(${DEPS2_LIBRARY_DIRS})（pkg_check_modules 裸取 LIBRARIES 不注入 -L）
2. **0002-src-blur_image.cc.patch**（EGL pbuffer 替代 GBM/DRM + GLES 严格性）：
   - 删 gbm.h/DRM 设备探测（is_device_viable/choose_best_card/open_best_device 等 ~110 行）、ctx 的 fd/gbm 字段、getopt 'd' 选项
   - setup_context() 重写：eglGetDisplay(EGL_DEFAULT_DISPLAY) + EGL_PBUFFER_BIT + eglCreatePbufferSurface(**按 ctx.width/ctx.height 创建**——W4 审计 P1 修复：曾硬编码 64x64 导致大图回读越界 UB，256x256 回归用例已入 test_package）
   - shader 7 处 `R"(\n#version` → `R"(#version`（P0005：#version 必须首行）
   - 2 处 `#define texpick texture2D` → `texture`（L0002：GLSL ES 3.00 废弃 texture2D）

## 依赖版本

| 依赖 | 版本 | 来源 |
|---|---|---|
| gdk-pixbuf | 2.44.6.1 | conan ohpcd（传递 glib/2.84.0.1、libpng、libjpeg-turbo、libtiff、libwebp、zstd、zlib） |
| EGL / GLESv3 | 系统 1.4 / 3.0 | OpenHarmony 平台库（/system/lib64/libEGL.so、libGLESv3.so；SDK sysroot 头文件，裸 clang 默认可见） |
| glm | 不需要 | 仅 BUILD_DEMO=on 时（glew/glfw3 亦然，OHOS 无 X11，demo 永不构建） |

## 验证结果

```bash
# 1. EGL 能力探针（设备实测）
egl_probe → eglInitialize OK 1.4, vendor=OpenHarmony, surfaceless_ctx=1,
            pbuffer makeCurrent=1, glReadPixels rgba=(51,102,153,255) PASS

# 2. blur_image 端到端冒烟（真实渲染管线）
$ blur_image -o out.png -r 11 -p 2 test.png
outfile: out.png, infile: test.png, r: 11, p: 2, l: 1, s: 1
image has alpha
N = 24, sum = 1.67772e+07
sizes[0] = 104, strides[0] = 16
total ubo size = 1680
new_path: out.png
exit=0   # out.png 8318 字节（输入 256x256 渐变图 147936 字节，模糊后显著变小=有效模糊）

# 3. musl getopt 行为（记录，非阻塞）
选项必须置于位置参数前：blur_image -o out.png test.png ✅
```

## 注意事项

- **命令行调用**：musl getopt 无 GNU 重排，`-o` 等选项必须放在输入文件路径之前（usage 已是此序，上游文档同样示例前置）。
- **渲染设备**：OHOS 上走 EGL 默认显示（软件/平台渲染），`-d drmdev` 选项已随 GBM 路径移除。
- **BUILD_DEMO**：依赖 glew/glfw3（X11 窗口系统），OHOS 永远关闭，勿在配方中开启。
- **系统 EGL 链接**：OHOS 适配版 conan 的 clang 默认 sysroot 含 EGL/GLES3 头与 stub 库，无需额外 include/lib 注入；CI 同环境可复现。
- **test_package 二进制 fixture**：GitCode PR `.diff` 端点不携带二进制补丁数据（"Binary files ... differ" 占位行），CI checkout-pr 的 `git apply` 对 PR 内二进制文件必失败（PR #9334 首轮 CI 实测）。fixture 一律 base64 文本随仓（`*.png.b64`），test.sh 运行时 `base64 -d` 解码到 `$TMPDIR` 再用。上游 main 现有包无任何真实二进制 test fixture（acf-skins 的 corrupt.png 实为 16 字节文本），与本结论一致。
---

**编译结束**: 2026-09-09 19:37
**最终状态**: built
