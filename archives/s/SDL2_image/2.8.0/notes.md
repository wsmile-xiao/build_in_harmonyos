# SDL2_image 2.8.0 适配笔记

## 编译环境
- 构建系统: autotools (configure) + cmake (CMakeLists.txt)
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: failed

## 编译步骤

1. **源码获取**: 通过 Git 克隆 SDL_image release-2.8.0 分支
   ```bash
   git clone --depth 1 --branch release-2.8.0 https://github.com/libsdl-org/SDL_image.git SDL2_image-2.8.0
   ```

2. **初始化编译环境**: 使用 ohc-run.py init-build
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build SDL2_image 2.8.0 --url=file://...
   ```

3. **configure 尝试**: 使用 --build=aarch64-ohos-linux 绕过 config.guess 问题
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX --build=aarch64-ohos-linux
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | TMPDIR 权限问题导致临时文件创建失败 | 使用 `--build=aarch64-ohos-linux` 绕过 |
| 2 | **SDL2 依赖缺失** | SDL2_image 需要 SDL2 >= 2.0.9，但 SDL2 未安装 | ⚠️ **阻塞问题：无法下载 SDL2** |
| 3 | 网络连接失败 | GitHub/cdn 连接超时，SSL 证书验证失败 | 无法解决，需要依赖预编译包或离线源码 |

## 依赖版本

### 必需依赖（缺失）
| 依赖 | 所需版本 | 状态 | 说明 |
|------|----------|------|------|
| SDL2 | >= 2.0.9 | ❌ 未安装 | 核心依赖，无法编译 |
| libpng | - | ❌ 未安装 | PNG 图像支持（可选但推荐） |
| libjpeg-turbo | - | ❌ 未安装 | JPEG 图像支持（可选但推荐） |
| libtiff | - | ❌ 未安装 | TIFF 图像支持（可选） |
| libwebp | - | ❌ 未安装 | WebP 图像支持（可选） |

### 可选替代方案
SDL2_image 的 CMake 构建支持 `SDL2IMAGE_BACKEND_STB=ON`，可以使用内置的 stb_image 库处理 JPEG/PNG，避免外部图像库依赖。但仍需要 SDL2。

## 验证结果

编译失败，configure 在检测 SDL2 依赖时报错：
```
checking for sdl2 >= 2.0.9... no
checking for sdl2-config... no
configure: error: *** SDL version 2.0.9 not found!
```

## 交付物

无（编译失败）

## 注意事项

### 关键阻塞
- SDL2 是 SDL2_image 的**必需依赖**，无法绕过
- 网络问题导致无法从 GitHub 下载 SDL2 源码
- cmd-pkgs 预编译包列表无法访问

### 后续建议
1. 等待网络恢复后下载 SDL2 源码或预编译包
2. 先编译 SDL2，然后再编译 SDL2_image
3. 使用 `SDL2IMAGE_BACKEND_STB=ON` (CMake) 避免额外图像库依赖
4. 更新 dependencies.md 添加 SDL2 到编译顺序表

---
**编译结束**: 2026-05-19 20:58
**最终状态**: published
