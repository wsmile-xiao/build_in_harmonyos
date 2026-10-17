# PlutoSVG

> 用 C 编写的小型高效 SVG 渲染库。

## 简介

PlutoSVG 解析并渲染 SVG 文档（含 OpenType 字体内嵌 SVG），底层 2D 光栅化由
plutovg 提供。库为纯 C99 实现，源码同时提供 CMake 与 Meson 构建描述，本适配
以 CMake 为 Conan 唯一构建入口。

## OHOS 适配要点

- 使用 Conan CMakeToolchain 在 HarmonyOS arm64/clang 15 上原生构建。
- GitHub 源码归档不含 plutovg 子模块内容，配方在 `source()` 中把官方
  plutovg 1.3.3 发布包 vendor 到 `plutovg/`，沿用上游 `add_subdirectory` 回退路径。
- 配方默认构建静态库（`shared=False`）；freetype 集成保持上游默认关闭。
- 上游无独立测试套件；Conan 消费者测试验证版本、加载、几何、渲染与 PNG 输出。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| plutovg（vendored 源码） | 1.3.3 | 官方发布包，随本包源码一起构建 |
| libm | 系统 | CMake 按平台自动探测，`package_info` 声明 |

## 功能验证

```bash
conan create archives/p/plutosvg/0.0.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
conan create archives/p/plutosvg/1.3.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 参考

- [官方源码仓库](https://github.com/sammycage/plutosvg)
- [v0.0.8 发布说明](https://github.com/sammycage/plutosvg/releases/tag/v0.0.8)
- [plutovg 1.3.3](https://github.com/sammycage/plutovg/releases/tag/v1.3.3)
