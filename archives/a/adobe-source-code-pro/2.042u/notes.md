# adobe-source-code-pro 2.042u 适配笔记

## 基本信息
- **软件名称**：adobe-source-code-pro
- **版本**：2.042u（对应官方 Upright fonts version 2.042，release tag `2.042R-u/1.062R-i/1.026R-vf`）
- **构建系统**：custom（纯字体数据包，无需编译）
- **许可证**：OFL-1.1（LICENSE.md，SIL Open Font License 1.1）
- **上游仓库**：https://github.com/adobe-fonts/source-code-pro

## 构建说明
- 纯字体数据包：上游已预构建 TTF/OTF/VF/WOFF/WOFF2，无编译、无构建依赖、无运行时依赖。
- 本版本为 upright 2.042，仅安装 7 个 upright TTF 到 `share/fonts/SourceCodePro/`：
  Black / Bold / ExtraLight / Light / Medium / Regular / Semibold。
- italic 面（*It.ttf）属于独立的 1.062 版本，不装入 2.042u 包。
- 同时安装 LICENSE.md（OFL-1.1）到字体目录。
- 数据包类型 `package_type = "application"`，无 `cpp_info`。

## 源码 URL
- **当前 URL**：https://github.com/adobe-fonts/source-code-pro/archive/refs/tags/2.042R-u%2F1.062R-i%2F1.026R-vf.tar.gz
- **SHA256**：19d2c07eff0d91927c47a482c38e591ba855664fc65440006fb65d0157841249
- **官方 release 资产**：TTF-source-code-pro-2.042R-u_1.062R-i.zip（sha256 0c85bac90d15c040b82939aa92bc8404420fccc02e37bbcb9c93a7f21abb52c6）
- **说明**：优先使用官方 GitHub URL；tag 名含斜杠，采用 %2F 编码形式，已验证可下载（HTTP 200）。

## 上游测试统计
- **上游自动化测试数量**：0（零）
- **依据**：
  - 归档无 test/ 或 tests/ 目录
  - 无 Makefile/CMakeLists.txt/meson.build 等构建系统（纯字体资源包）
  - 无 CI test job

## 验证结果
- **test_package**：1 个 test() 方法，7 个 upright TTF 文件的存在性、数量、非空、TTF magic（0x00010000）、sha256 基线全部校验。
- **conan-verify adobe-source-code-pro 2.042u**：见 reports/conan-verify-report.md。

## 特殊说明
- 无需补丁，无需修改上游源码。
- 使用 `conan.tools.files.copy` 安装字体文件，遵循 Conan 2 API。
---

**编译结束**: 2026-08-06 17:09
**最终状态**: built
