# dlib

## 简介

dlib是一个现代化的C++工具包，包含机器学习算法、数值优化工具、图像处理工具和网络编程组件。它广泛应用于机器学习、计算机视觉、机器人等领域。

**核心特性**：
- 机器学习算法（SVM、深度学习、聚类等）
- 数值优化工具（优化算法、线性代数）
- 图像处理工具（图像加载/保存、特征提取）
- 网络编程组件（HTTP服务器、客户端）
- 线程池、定时器、日志系统

**项目主页**：https://github.com/davisking/dlib

## 版本历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 19.24.2 | built | 2026-06-02 | 静态库编译，无GUI支持 |

## 编译要点

### 构建系统
- **类型**：CMake
- **配置**：`cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF`

### 特殊选项
- `-DBUILD_SHARED_LIBS=OFF`：编译为静态库（默认）
- `-DDLIB_USE_CUDA=OFF`：禁用CUDA支持（鸿蒙系统无GPU）
- `-DDLIB_USE_FFMPEG=OFF`：禁用FFmpeg支持（可选）

### 已知问题
1. **CMake平台识别**：CMake不识别HarmonyOS系统，需要手动创建Platform/HarmonyOS配置（已忽略警告）
2. **X11 GUI缺失**：无libx11-dev，GUI支持被禁用（不影响核心功能）
3. **NEON支持**：ARM架构已启用NEON优化
4. **内嵌依赖**：内嵌libpng、libjpeg、zlib，无需外部依赖

### 编译依赖
- **必需**：cmake >= 3.8, clang, C++标准库
- **可选**：libx11-dev（GUI支持）, CUDA（GPU加速）, FFMPEG（视频处理）

### 预编译包
- **状态**：未发布（built状态）
- **路径**：无（需要手动打包）

## 使用示例

### CMake集成
```cmake
find_package(dlib REQUIRED)
target_link_libraries(your_target PRIVATE dlib::dlib)
```

### pkg-config集成
```bash
pkg-config --cflags dlib
pkg-config --libs dlib
```

### C++代码示例
```cpp
#include <dlib/image_io.h>
#include <dlib/image_processing.h>

dlib::array2d<dlib::rgb_pixel> img;
dlib::load_image(img, "image.jpg");
// ... 处理图像
```

## 参考资料

- [官方文档](https://dlib.net/)
- [GitHub仓库](https://github.com/davisking/dlib)
- [编译指南](https://github.com/davisking/dlib/blob/master/docs/compile.md)