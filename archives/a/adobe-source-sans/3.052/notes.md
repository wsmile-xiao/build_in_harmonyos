# adobe-source-sans 3.052 适配笔记

## 基本信息
- **软件名称**：adobe-source-sans（Source Sans 3）
- **版本**：3.052（上游 tag `3.052R`）
- **构建系统**：无（纯字体数据包，字体由上游预构建）
- **许可证**：SIL Open Font License 1.1（OFL-1.1）
- **上游仓库**：https://github.com/adobe-fonts/source-sans

## 构建说明
- 纯字体数据包：上游发布 3.052R 提供预构建 TTF/OTF/VF/WOFF/WOFF2 字体，无源码编译。
- 本配方安装 **14 个 TTF** 字体到 `share/fonts/SourceSans3/`，同时安装 `LICENSE.md`（OFL-1.1）。
- 无编译步骤（`build()` 为空），`package()` 使用 `conan.tools.files.copy` 拷贝字体。
- 无构建依赖，无运行时依赖（`requirements()` 为空）。

## 源码 URL
- **URL**：https://github.com/adobe-fonts/source-sans/archive/refs/tags/3.052R.tar.gz
- **SHA256**：`21f4e24bbd7b24c31ba13ddb10600db3a61565f20f2ccf2347f4e114e6e34596`
- **说明**：使用上游 GitHub 官方 tag `3.052R` 归档（2023-04-04 发布），包含 LICENSE.md 与全部格式字体。
- 单独发布的 TTF 包 `TTF-source-sans-3.052R.zip`（SHA256 `1b0dd1ec44b39f1dd98bbd153a1a3815f083639874ddee02c842bd601bad3d21`）仅含字体、无许可证文件，故最终采用仓库 tag 归档。

## 上游测试统计
- **上游自动化测试数量**：0（零）
- **依据**：
  - tag 3.052R 归档无 `test/`、`tests/` 目录，无任何测试文件
  - 无测试框架引用（无 pytest / unittest / go test / ctest 等）
  - 无 CI test job（仓库为字体发布仓库，无 .github workflows 测试流水线）
  - 项目为纯字体数据包，发布物即字体文件本身

## 验证结果
- **conan-verify adobe-source-sans 3.052**：见 reports/ 目录
- **test_package**：1 个 test() 方法，45 个断言（14 个文件存在 + 14 个非空 + 14 个 TTF magic + LICENSE 存在 + LICENSE 非空 + 目录文件数=14），全部通过
- **finish adobe-source-sans 3.052 built**：已完成

## 特殊说明
- 数据包类型 `package_type = "application"`，无 `cpp_info`。
- 无需补丁，无需修改上游源码（`patches: {}`）。
- 平台无关（arm64/x86_64 均可安装），无 OHOS 专用代码。
---

**编译结束**: 2026-08-06 10:52
**最终状态**: built
