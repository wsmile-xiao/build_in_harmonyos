# gst-plugins-base 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-17（第二轮：启用 X11/DRM/iso-codes 功能）
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码并解压
2. 应用 meson.build patch（Python 脚本执行修复）
3. 创建 feature 分支 feat/gst-plugins-base-1.28.3
4. 编写 conanfile.py，包含：
   - 依赖：gstreamer/1.28.3, glib2/2.88.0, orc/0.4.42, libogg/1.3.6, libvorbis/1.3.7, opus/1.5.2.1, alsa-lib/1.2.16.1, libx11/6.4.0, libxext/6.4.0, libxv/1.0.13, libxi/6.1.0, libdrm/2.4.133, iso-codes/4.20.1
   - pkg-config wrapper .pc 文件创建（glib2 子包、gstreamer 子包、orc-0.4、ogg、vorbis、vorbisenc、alsa、libdrm）
   - iso-codes 自带 pc 注入 PKG_CONFIG_PATH
   - NLS 禁用 + gettext 宏 stub
   - AR/AS/STRIP/NM/RANLIB 绝对路径 pin
5. conan create 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python 脚本执行失败 | HMDFS/SELinux 环境限制 | Patch meson.build，用 python3 解释器调用脚本 |
| 2 | glib2 子包 .pc 文件缺失 | glib2 conan 包不提供 gobject-2.0.pc 等 | generate() 中创建 wrapper .pc 文件 |
| 3 | gstreamer 子包 .pc 文件缺失 | gstreamer conan 包不提供 gstreamer-1.0.pc 等 | generate() 中创建 wrapper .pc 文件 |
| 4 | orc pkg-config 名称不匹配 | conan 包名 orc，meson 查找 orc-0.4 | 创建 orc-0.4.pc wrapper |
| 5 | ogg/vorbis/alsa pkg-config 名称不匹配 | conan 包名与 meson 查找名不同 | 创建 ogg.pc, vorbis.pc, vorbisenc.pc, alsa.pc wrapper |
| 6 | PR diff 误删 main 已合入的 goaccess 归档 | 前序尝试的 "remove goaccess" 提交删除了 fork 点继承的文件 | 从 merge-base 恢复 archives/g/goaccess，三方 diff 回归单包 |
| 7 | CI G0e 报根目录存在 .branch_init/.ci-marker-v7b 等文件 | CI worker 持久目录的 git index 被历史 AI 会话污染（这些文件从未被分支跟踪） | 分支侧无可修复内容；重试 CI 等待干净 worker |
| 8 | libdrm 双 include 目录 | xf86drm.h 在 include/，drm_fourcc.h 在 include/libdrm/ | wrapper Cflags 同时加 -Iinclude 与 -Iinclude/libdrm |
| 9 | meson 报 iso-codes 缺 domains 变量 | PkgConfigDeps 生成的空壳 iso-codes.pc 遮蔽包自带 pc；且包自带 pc 的 prefix=/ 是构建期路径 | generate() 中覆盖 iso-codes.pc：prefix 指向 conan 包目录 + 完整 domains 列表 |
| 10 | libx11/1.8.13 与 libxext/6.4.0.1 版本冲突 | 制品仓 X11 栈两条版本线（1.x 与 6.x），libxv/libxi 全部钉 libx11/6.4.0+libxext/6.4.0 | 统一使用 6.x 版本线 |
| 11 | XInput2.h 找不到 Xfixes.h | libxi/1.8.3 未声明 libxfixes 依赖 | 改用 libxi/6.1.0（已正确依赖 libxfixes/6.1.0 transitive_headers） |
| 12 | CI worker 上 lld 链接器加载 libxml2.so.16 失败 | OHOS SDK 的 lld 需要 SDK lib 目录下的 libxml2.so.16，LD_LIBRARY_PATH 未包含 | generate() 探测 /data/service/hnp/ohos-sdk.org 下含 libxml2.so.16 的 llvm/lib 目录并注入 LD_LIBRARY_PATH（有 isdir 守卫，SDK 布局不同时静默跳过） |

## 功能启用状态（不裁剪原则）

### 已启用（依赖已发布）
| 功能 | 依赖 | 插件/产物 |
|------|------|----------|
| ogg | libogg/1.3.6 | ogg demuxer/muxer/parser |
| vorbis | libvorbis/1.3.7 | vorbis 编解码 |
| opus | opus/1.5.2.1 | opus 编解码 |
| alsa | alsa-lib/1.2.16.1 | alsasink/alsasrc |
| orc | orc/0.4.42 | liborc 加速（备份 C 代码路径） |
| x11 | libx11/6.4.0 | ximagesink 视频输出 |
| xshm | libxext/6.4.0 | X11 共享内存传输 |
| xvideo | libxv/1.0.13 | xvimagesink 视频输出 |
| xi | libxi/6.1.0 | ximagesink 触摸支持 |
| drm | libdrm/2.4.133 | gstallocators DRM dumb buffer 分配器 |
| iso-codes | iso-codes/4.20.1 | gst-tag 语言名称查找 (iso_639-2) |

### 仍禁用（依赖生态缺口，待专家分析）
| 功能 | 原因 |
|------|------|
| pango | 制品仓 pango/1.56.4 依赖 `glib/2.84.0.1`，而 gstreamer/gst-plugins-base 使用 `glib2/2.88.0`——同图共存两个 glib 包会导致头文件与符号冲突；需先做生态级 glib/glib2 归一 |
| gl | 制品仓无 GL API 库（gl/glesv2/opengl 均未发布；mesa 包仅含 OSMesa 软渲染，egl/1.0.5 仅为 EGL 包装）；需先适配 GLESv2/GL 包装包 |
| theora | libtheora 未在制品仓发布 |
| tremor | tremor 未在制品仓发布（vorbis 已启用，功能等价的整数解码实现缺失） |
| cdparanoia | cdparanoia 未在制品仓发布 |
| libvisual | libvisual 未在制品仓发布 |
| qt5 | qt5 仅用于 QML examples（examples 已禁用），无独立插件价值 |

## 源码修改

- patches/0001-meson.build-python3-scripts.patch: 修复 Python 脚本执行

## 依赖版本

| 依赖 | 版本 |
|------|------|
| gstreamer | 1.28.3 |
| glib2 | 2.88.0 |
| orc | 0.4.42 |
| libogg | 1.3.6 |
| libvorbis | 1.3.7 |
| opus | 1.5.2.1 |
| alsa-lib | 1.2.16.1 |
| libx11 | 6.4.0 |
| libxext | 6.4.0 |
| libxv | 1.0.13 |
| libxi | 6.1.0 |
| libdrm | 2.4.133 |
| iso-codes | 4.20.1 |

## 注意事项

- pango 未启用：glib/glib2 双包冲突（生态问题，非本包可解），见上表
- gl 未启用：无 GL API 库发布（egl/1.0.5 仅 EGL，mesa 仅 OSMesa）
- theora/tremor/cdparanoia/libvisual 未启用：依赖未发布
- 上述禁用项均因依赖生态缺口，非功能裁剪；依赖就绪后可按同模式启用

---

**编译结束**: 2026-09-17
**最终状态**: built
