# nomacs 3.22.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
cmake --build build
cmake --install build DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt6Svg stub 导致 SVG 渲染失败 | OHOS Qt6Svg 无实际实现 | 添加 DkSvgRendererStub.h stub 类 |
| 2 | cmake 构建需要 configure wrapper | 构建脚本期望 ./configure 入口 | 添加 configure wrapper 转换 -D 参数 |
| 3 | QtSvg 链接符号未定义 | OHOS Qt6Svg 为 stub 实现 | 禁用 QtSvg 链接，使用 stub 替代 |
| 4 | 多个源文件引用 QSvgRenderer | stub 不提供实际 vtable | 修改源文件使用 DkSvgRendererStub 替代 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| DkCore/DkSvgRenderer_stub.h | 新增 stub 类替代 QSvgRenderer |
| cmake/UnixBuildTarget.cmake | 禁用 QtSvg 链接 |
| cmake/Utils.cmake | 构建工具链适配 |
| DkCore/DkActionManager.cpp | 使用 stub 替代 QSvgRenderer |
| DkCore/DkBaseViewPort.cpp/h | 同上 |
| DkCore/DkImageStorage.cpp | 同上 |
| DkGui/DkViewPort.cpp | 同上 |
| configure | 新增 cmake configure wrapper |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| Qt5 | 5.15.2 |
| exiv2 | 0.28+ |

---

**编译结束**: 2026-06-01
**最终状态**: built