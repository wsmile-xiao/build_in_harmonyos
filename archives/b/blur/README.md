# blur — 离屏高斯模糊图像工具

> deepin blur-effect：基于 OpenGL ES 3.0 的离屏图像高斯模糊命令行工具（`blur_image`），deepin 桌面壁纸模糊所用方案。

## 简介

blur-effect（本仓包名 `blur`）是 deepin 桌面环境的离屏图像模糊工具。它将输入图片载入 GPU 纹理，用 OpenGL ES 3.0 shader 实现高效线性采样高斯模糊（linear-sampling Gaussian blur），支持亮度/饱和度/明度调节与多轮渲染，再经 gdk-pixbuf 编码输出。

上游 1.1.3 的渲染上下文走 Linux GBM+DRM 路径（打开 `/dev/dri/cardN` 建 gbm_surface），deepin/Nix/Debian 均按此打包。

## OHOS 适配要点

- **渲染上下文重写**：HarmonyOS PC 无 `/dev/dri` 渲染节点、无 libgbm——适配改为 `EGL_DEFAULT_DISPLAY` + pbuffer surface（EGL 标准 API，Linux 上同样合法），`-d`（DRM 设备）选项随之移除。
- **平台库直链**：EGL/GLESv3 使用 OpenHarmony 系统库（`/system/lib64/libEGL.so`、`libGLESv3.so`，实测 EGL 1.4 + GLES3 上下文 + pbuffer 回读全通）。
- **GLES 严格模式**：OpenHarmony shader 编译器不接受 `#version` 前导换行与已废弃的 `texture2D`（Linux Mesa 宽松），补丁逐项修正。
- **调用顺序**：musl getopt 无 GNU 参数重排，选项须置于位置参数前：`blur_image -o out.png -r 11 in.png`。
- **BUILD_DEMO 恒关**：demo 依赖 glew/glfw3（X11），OHOS 不构建。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| gdk-pixbuf | 2.44.6.1 | conan 制品仓（传递 glib/libpng/libjpeg-turbo/libtiff/libwebp） |
| EGL / GLESv3 | 系统 | OpenHarmony 平台库 |

## 功能验证

```bash
# /tmp 只读（E002）：输出走 $TMPDIR 或当前目录；musl getopt 选项须前置
blur_image -o "$TMPDIR/out.png" -r 11 -p 2 input.png   # 半径 11、2 轮渲染
```

## 参考

- [源码仓库](https://github.com/sonald/blur-effect)
- [高效高斯模糊算法（linear sampling）](http://rastergrid.com/blog/2010/09/efficient-gaussian-blur-with-linear-sampling/)
