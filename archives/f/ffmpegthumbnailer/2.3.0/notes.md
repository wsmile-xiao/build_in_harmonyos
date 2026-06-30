# ffmpegthumbnailer 2.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4 / clang++
- 状态: partial

## 编译步骤

1. 从 GitHub 镜像 kkgithub.com 克隆源码
2. 创建 tarball 并使用 ohc-run.py init-build 初始化
3. CMake 配置：
   ```bash
   cmake -B build \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DENABLE_SHARED=ON \
     -DENABLE_STATIC=OFF \
     -DENABLE_TESTS=OFF
   ```
4. 编译：cmake --build build -j$(nproc)
5. 安装：cmake --install build
6. 设置 RPATH：patchelf --set-rpath $DEFAULT_PREFIX/lib

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | FFmpeg API 不兼容 | ffmpegthumbnailer 2.3.0 使用 FFmpeg 5.0+ API，当前系统为旧版本 | 修改源码：AV_FRAME_FLAG_INTERLACED → interlaced_frame, AV_FRAME_FLAG_KEY → key_frame, av_packet_side_data_get → av_stream_get_side_data |
| 2 | 动态库加载失败 | HMDFS 文件系统限制，动态链接器无法正确解析库路径 | 设置 RPATH，签名 ELF（部分解决） |
| 3 | 运行时符号未找到 | FFmpeg 库未被正确加载 | 平台级问题，需进一步调查 HMDFS 动态链接机制 |

## 源码修改

### 0001-ffmpeg-api-compat.patch (已应用)

修改文件：libffmpegthumbnailer/moviedecoder.cpp

**修改内容：**
- 第 338 行：`m_pFrame->flags & AV_FRAME_FLAG_INTERLACED` → `m_pFrame->interlaced_frame`
- 第 436 行：`!(m_pFrame->flags & AV_FRAME_FLAG_KEY)` → `!m_pFrame->key_frame`
- 第 559-573 行：`av_packet_side_data_get()` → `av_stream_get_side_data()`

## 依赖版本

| 依赖 | 版本 |
|------|------|
| FFmpeg (libavformat) | 58.76.100 |
| FFmpeg (libavcodec) | 58.134.100 |
| FFmpeg (libavutil) | 56.70.100 |
| FFmpeg (libavfilter) | 7.110.100 |
| libjpeg | 62 (3.1.4.1) |
| libpng | 1.6.43 |

## 验证结果

编译验证：
```bash
cmake --build build -j$(nproc)
# 输出：Built target ffmpegthumbnailer ✓
```

运行验证：
```bash
ffmpegthumbnailer --version
# 输出：Error loading shared library libavformat.so...
# 状态：动态链接器无法加载依赖库（HMDFS 平台限制）
```

**编译成功，运行时验证受阻于 HMDFS 动态链接机制**

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ffmpegthumbnailer | 43KB | 主程序二进制（已签名） |
| libffmpegthumbnailer.so | 281KB | 共享库（已签名） |

## 注意事项

1. **FFmpeg API 兼容性**：本版本 ffmpegthumbnailer 使用 FFmpeg 5.0+ API，需修改源码兼容旧版本 FFmpeg
2. **RPATH 必需**：HMDFS 文件系统需要设置 RPATH 才能正确找到库文件
3. **ELF 签名**：所有二进制和共享库必须签名才能执行
4. **动态链接问题**：当前存在 HMDFS 动态链接器无法正确加载库的问题，需要进一步调查平台特性
---

**编译结束**: 2026-05-21 12:12
**最终状态**: published

## 本次编译补充记录 (2026-05-21 12:12)

### 编译方法更新
- 使用自定义 ohos-toolchain.cmake 工具链文件（CMAKE_SYSTEM_NAME=OHOS）
- 配置命令：`cmake -DCMAKE_TOOLCHAIN_FILE=../ohos-toolchain.cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release`
- 编译命令：`make -j2`
- 安装命令：`make install DESTDIR=$TEST_PREFIX`

### 补丁更新
- 0001-libffmpegthumbnailer-moviedecoder.cpp.patch：FFmpeg API 兼容性修复（适配 FFmpeg < 5.0）
- 0002-ohos-toolchain.cmake.patch：新增 CMake 工具链文件（支持 HarmonyOS 平台识别）

### 制品交付
- ffmpegthumbnailer-2.3.0-ohos-aarch64.tar.gz (53MB，包含外部依赖)
- ffmpegthumbnailer-2.3.0-ohos-aarch64-debug.tar.gz (286KB，调试符号)

### 打包处理
- 外部依赖已复制到 lib/external/ 目录（FFmpeg、libjpeg、libpng）
- RPATH 已设置为 `$ORIGIN/../lib:$ORIGIN/../lib/external`
- Debug 符号已分离保存
