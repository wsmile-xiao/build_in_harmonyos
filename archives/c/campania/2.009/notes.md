# Campania 2.009 适配笔记

## 编译环境
- 软件: Campania
- 版本: 2.009
- 构建系统: custom（纯字体资源包，无需编译）
- 编译日期: 2026-09-06
- 状态: built（本地 Conan/W3 验证通过，尚未上传）

## 概述
Campania 是用于音乐理论罗马数字分析的字体。上游发行包不包含 C/C++ 源码或可执行测试套件，提供 OTF、TTF 和 WOFF 三种字体格式，以及 README 和 SIL Open Font License 1.1 许可证。

## 源码来源
- URL: https://archive.linux.duke.edu/pub/debian/pool/main/c/campania/campania_2.009.orig.tar.gz
- SHA256: 48a2797dc27fc79fc6752567df1262cce77d6bb7677420c17be55b37fb86e7c6
- 原始上游地址 `https://waterlan.home.xs4all.nl/campania/` 已失效并跳转到 404 页面，因此采用 Debian 保存的原始上游源码归档。

## 编译步骤
1. Conan source 阶段下载并校验上游 tar.gz。
2. 跳过编译阶段（纯字体资源包）。
3. Conan package 阶段将 `Campania.otf`、`Campania.ttf`、`Campania.woff` 安装到 `fonts/`。
4. 将 `LICENSE` 和 `README.md` 安装到 `licenses/`。

## 上游测试用例
上游归档没有构建系统、可执行测试脚本或测试目录，故上游测试用例为 0，已在 `test_package/MANIFEST.yml` 中完整声明 `upstream_tests: []`。上游 README 仅描述了 MuseScore 和 LibreOffice 的兼容性，不能伪造为可自动执行的上游测试。

## 补充测试用例
消费者测试 `test_package/test_fonts.py` 覆盖：
1. `fonts/` 目录存在。
2. OTF、TTF、WOFF 三个上游字体文件全部存在且集合精确匹配。
3. 三种字体文件均非空且文件头符合对应格式签名。
4. `licenses/LICENSE` 和 `licenses/README.md` 均已打包且非空。
5. Conan `test()` 通过 `self.run()` 实际执行上述验证脚本。

## 补充测试用例说明
消费者测试已从基础文件存在性检查扩展为 11 项独立验证：
1. 精确验证 OTF、TTF、WOFF 文件集合。
2. 解析 OTF SFNT 目录、必需 OpenType 表和 CFF 轮廓。
3. 解析 TTF SFNT 目录、必需 OpenType 表及 glyf/loca 轮廓。
4. 解析 WOFF 目录、总长度、压缩表和解压长度。
5. 检查 Campania 输入字符的 Unicode cmap 覆盖。
6. 检查 OTF/TTF cmap 码点集合一致性。
7. 检查四个 `.fea` 源文件随包安装。
8. 检查主 `.fea` 文件的 include 关系。
9. 检查 GSUB 的 liga/calt 特性声明。
10. 检查 GPOS 的 kern/symbol_spacing 声明。
11. 检查 LICENSE 和 README.md 完整性。

扩展测试命令：
```bash
python3 test_package/test_fonts.py <fonts-dir> <licenses-dir> <features-dir>
```

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方下载地址返回 HTML | 原 XS4ALL 主页已迁移并返回 404 | 使用 Debian 镜像保存的原始 tar.gz，并记录 SHA256 |
| 2 | 任务语言预检识别为 other | 上游是字体数据包而非 C/C++ 项目 | 按资源包配方模式适配，不执行虚构的 C/C++ 编译 |

## 许可证
SIL Open Font License 1.1（OFL-1.1）。许可证随包安装到 `licenses/LICENSE`。

## 注意事项
- 字体包不声明 C/C++ 库或命令行工具，不创建 `commands.json`。
- 使用方需由系统字体管理器加载 `fonts/` 中的字体文件。
---

**编译结束**: 2026-09-06 19:03
**最终状态**: built
