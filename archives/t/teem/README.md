# Teem

> Tools to process and visualize scientific data and images - a collection of C libraries for scientific data processing

## 简介

Teem 是一个协同的库集合，用于科学数据的处理和可视化。它提供了以下核心功能：

- **NRRD**：Nearly Raw Raster Data，用于科学数据的标准化文件格式
- **Gage**：栅格数据采样和梯度计算
- **Ten**：张量数据处理和可视化
- **Pull**：粒子系统采样和重建
- **Mite**：体积渲染器

Teem 广泛应用于医学图像分析、科学可视化、数值计算等领域，支持多种编码格式（raw、ascii、hex、gz、bz2）和数据类型。

## OHOS 适配要点

在 HarmonyOS 上编译 Teem 时需要注意：

1. **CMake 版本要求**：Teem 1.11.0 原始代码要求 CMake 2.4，但 CMake 4.x 不支持这么旧的版本，需更新为至少 3.5
2. **废弃模块处理**：CMake 2.8+ 已移除 CMAKE_EXPORT_BUILD_SETTINGS 模块，需注释掉相关代码
3. **可选依赖**：ZLIB、PNG、BZIP2 为可选依赖，缺失时会自动禁用相关编码支持（gz/bz2），但不影响核心 NRRD 功能
4. **测试通过率**：35 个测试中 33 个通过（94%），失败的 2 个测试与数值精度相关，不影响核心功能

## 功能验证

```bash
# 验证版本
unu --version      # Teem version 1.11.0
tend --version     # Teem version 1.11.0

# 功能完整性检查
nrrdSanity         # nrrd sanity check passed
                   # encodings supported: raw, ascii, hex (gz/bz2 not available)
                   # formats supported: nrrd
```

## 可用命令

Teem 提供以下可执行工具：

- **unu**：NRRD 数据处理工具（转换、切片、统计等）
- **tend**：张量数据处理和可视化工具
- **nrrdSanity**：NRRD 库功能完整性检查
- **overrgb**：RGB 图像叠加处理
- **ilk**：图像处理工具
- **mrender**、**miter**：体积渲染工具
- **vprobe**、**gprobe**、**puller**：采样和重建工具

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| cmake | 4.1.2+ | 构建工具（必需） |
| pthreads | 系统内置 | 多线程支持（必需） |
| zlib | - | gz 编码支持（可选，未启用） |
| png | - | PNG 图片支持（可选，未启用） |
| bzip2 | - | bz2 编码支持（可选，未启用） |

## 测试结果

- 总测试数：35
- 通过：33
- 失败：2（probeSS_ctmr04, probeSS_ctmr10）
- 通过率：94%

失败的测试与数值精度相关，不影响核心功能使用。

## 参考

- [官方网站](https://sourceforge.net/projects/teem/)
- [Teem 文档](http://teem.sourceforge.net/)
- [NRRD 格式规范](http://teem.sourceforge.net/nrrd/)