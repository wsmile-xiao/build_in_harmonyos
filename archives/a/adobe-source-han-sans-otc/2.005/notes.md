# Adobe Source Han Sans OTC 2.005 适配笔记

## 编译环境
- 软件: Adobe Source Han Sans OTC (思源黑体 OpenType Collection 合集)
- 版本: 2.005R
- 构建系统: custom（纯数据包，无需编译）
- 编译日期: 2026-08-05
- 状态: built（待 CI 验证通过后改回 published）

## 概述
纯字体数据包，无需编译。Conan recipe 从 GitHub Releases 下载 OTC 字体文件并安装到 fonts/ 目录。OTC (OpenType Collection) 一个文件内含 CN/TW/HK/JP/KR 全部语言资源。

## 编译步骤
1. Conan source 阶段: 从 GitHub Releases 下载 `03_SourceHanSansOTC.zip`
2. Conan package 阶段: 解压后自动收集所有 `.otf`/`.ttf`/`.otc`/`.ttc` 字体文件并安装到 fonts/ 目录

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无 | 字体包为纯数据包，无编译步骤，无适配问题 | — |

## 验证结果
- 字体文件格式: OTC (OpenType Collection) / OTF (OpenType/CFF)
- 字重: 7 个 (ExtraLight, Light, Normal, Regular, Medium, Bold, Heavy)
- 覆盖范围: 简体中文、繁体中文(台湾/香港)、日文、韩文及拉丁字符

## 交付物
| 文件 | 说明 |
|------|------|
| *.otc | OTC 字体文件（含多语言），安装到系统字体目录即可使用 |

## 注意事项
1. 鸿蒙系统字体目录通常为 `/system/fonts/` 或 `/data/fonts/`
2. 安装后需刷新字体缓存
3. 许可证: SIL Open Font License 1.1 (OFL-1.1)
4. 零运行时依赖，仅需系统字体渲染器支持 OTC/OTF 格式

---

**适配结束**: 2026-08-05
**最终状态**: built
