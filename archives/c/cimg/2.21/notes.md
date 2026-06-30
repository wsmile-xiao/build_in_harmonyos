# cimg 2.21 适配笔记

## 编译环境
- 构建系统: custom (header-only library)
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

CImg 是一个 header-only C++ 图像处理库，主要组件是单个头文件 CImg.h。编译流程：

1. **初始化编译**：使用 ohc-run.py init-build 初始化
2. **源码提取**：从 GitHub 下载 v.221 tarball
3. **嵌套源码处理**：init-build 自动检测 examples 子目录并提升，但遗漏了顶层文件
4. **手动补充**：
   - 从 tarball 提取缺失的 CImg.h、README.md、README.txt、Licence 文件
   - 修改 CMakeLists.txt：cmake_minimum_required VERSION 2.6 → 3.5
   - 修改 CMakeLists.txt：CIMG_H_PATH 从 ${PROJECT_SOURCE_DIR}/.. → ${PROJECT_SOURCE_DIR}
5. **安装流程**：
   - 创建安装目录结构（include, share/doc, share/licenses）
   - 手动复制 CImg.h 到 include/
   - 复制文档和许可证文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本不兼容 | CMakeLists.txt 要求 VERSION 2.6，与 CMake 4.1.2 不兼容 | 修改为 VERSION 3.5 |
| 2 | CImg.h 文件缺失 | init-build 嵌套提升逻辑遗漏顶层文件 | 从 tarball 手动提取并复制 |
| 3 | X11/Xlib.h 找不到 | CImg 默认需要 X11 进行图形显示 | 不编译示例程序，仅安装头文件（header-only 库） |
| 4 | CMake 找不到 CImg.h | CIMG_H_PATH 配置错误 | 修改路径为 ${PROJECT_SOURCE_DIR} |

## 源码修改

### 修改文件列表
1. `CMakeLists.txt`（行 42, 63-65）
   - cmake_minimum_required VERSION 2.6 → 3.5
   - CIMG_H_PATH ${PROJECT_SOURCE_DIR}/.. → ${PROJECT_SOURCE_DIR}

### 修改记录
通过 ohc-run.py track-edit 记录：
- CMakeLists.txt 第 42 行：cmake_minimum_required 版本升级
- CMakeLists.txt 第 63-65 行：CImg.h 路径修正

## 依赖版本

无编译依赖（header-only 库）。可选运行时依赖：
- X11（图形显示，可选）
- libjpeg/libpng/libtiff（图像格式支持，可选）
- OpenCV/FFTW3/Magick++（高级功能，可选）

## 验证结果

Header-only 库验证：
```bash
# 检查头文件完整性
ls -lh ~/usr/local/include/CImg.h
# 结果: 2.7M CImg.h

# 检查文档完整性
ls -lh ~/usr/local/share/doc/cimg/
ls -lh ~/usr/local/share/licenses/cimg/
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| CImg.h | 2.7M | 主头文件 |
| README.md | 3.1K | 项目说明 |
| README.txt | 6.1K | 使用说明 |
| Licence_CeCILL-C_V1-en.txt | 21K | LGPL 兼容许可证 |
| Licence_CeCILL_V2-en.txt | 21K | GPL 兼容许可证 |

## 注意事项

1. **Header-only 特性**：CImg 是 header-only 库，无需编译，只需复制 CImg.h 到 include 目录即可使用
2. **嵌套源码 Bug**：init-build 的嵌套提升逻辑会遗漏顶层文件，需要手动补充
3. **可选依赖**：X11、libjpeg 等为可选依赖，不影响核心功能
4. **许可证选择**：CeCILL-C（LGPL 兼容）允许商业使用，CeCILL（GPL 兼容）要求开源

---
**编译结束**: 2026-06-05 10:53
**最终状态**: built (header-only, manually installed)
---

**编译结束**: 2026-06-05 10:58
**最终状态**: built
