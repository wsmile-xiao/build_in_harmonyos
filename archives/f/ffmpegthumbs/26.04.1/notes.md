## 编译记录

### 兼容层修改 (OpenHarmony 适配)

**问题**: ffmpegthumbs 26.04.1 是 KDE Plasma 6 缩略图插件，在 OpenHarmony 平台编译时遇到以下依赖和 API 差异问题：

1. **KIOGui 不可用**: ThumbnailCreator/ThumbnailResult 接口在 KF6 中属于 KIOGui 库，但 OpenHarmony 预编译的 KF6KIO 只提供了 KIOCore。创建了 compat/KIO/compat shim 提供 ThumbnailCreator/ThumbnailResult 接口定义。
2. **FFmpeg 版本差异**: 要求 AVCODEC >= 60.30 (FFmpeg 6.x)，但已安装 FFmpeg 4.x (AVCODEC 58.134.100)。降低版本要求到 58，并添加 compat/ffmpeg_compat.h 处理 API 差异。
3. **FFmpeg API 差异**: AV_FRAME_FLAG_KEY (FFmpeg 6.x 新增)、AV_FRAME_FLAG_INTERLACED (6.x 新增)、nb_coded_side_data/coded_side_data (6.x 新增)。使用条件编译和替代 API 处理。
4. **PIC 不兼容**: FFmpeg 静态库无 -fPIC，无法链接到共享模块。改为构建 STATIC 插件。
5. **测试禁用**: tests/ 需要 KIOGui，已条件禁用。

**修改的文件**:
- CMakeLists.txt (FFmpeg版本要求、compat include、去掉KIOGui、STATIC构建)
- compat/KIO/thumbcreator.h (兼容头文件)
- compat/KIO/thumbnailresult.h (兼容头文件)
- compat/ffmpeg_compat.h (FFmpeg API兼容宏)
- ffmpegthumbnailer.h (include路径改为compat)
- ffmpegthumbnailer/moviedecoder.cpp (FFmpeg API兼容代码)

**make check**: 无测试目标（测试已禁用，需要 KIOGui）
---

**编译结束**: 2026-05-30 11:59
**最终状态**: built
---

**编译结束**: 2026-05-30 14:53
**最终状态**: built
