# PlutoVG

> 用 C 编写的独立 2D 矢量图形库。

## 简介

PlutoVG 提供路径填充、描边、渐变与纹理绘制、文字、裁剪、合成和图像输出等 2D 光栅化能力。库本身不依赖外部三方库，源码同时提供 CMake 与 Meson 构建描述。

## OHOS 适配要点

- 使用 Conan CMakeToolchain 在 HarmonyOS arm64/clang 15 上原生构建。
- 配方默认构建静态库；可通过 `shared` 选项显式切换共享库。
- 上游仓库未提供独立测试套件，官方示例 `smiley` 和 Conan 消费者测试用于验证实际渲染 API。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| C 标准库、libm、pthread | 系统 | CMake 按平台自动探测 |

## 功能验证

```bash
conan create archives/p/plutovg/1.3.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 参考

- [官方源码仓库](https://github.com/sammycage/plutovg)
- [v1.3.3 标签](https://github.com/sammycage/plutovg/releases/tag/v1.3.3)
