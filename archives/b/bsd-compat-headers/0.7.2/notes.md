# bsd-compat-headers 0.7.2 适配笔记

## 编译环境
- 构建系统: custom（纯头文件）
- 编译日期: 2026-04-21（初次适配）；2026-09-01（Conan 配方适配）
- 状态: published

## 编译步骤
纯头文件安装，无需编译。Conan 配方为 header-library 类型，
package() 将 cdefs.h、queue.h、tree.h 安装到 include/sys/ 目录。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误判为 other | 纯头文件无 .c/.cpp 源文件，统计无法判定 | 实际为 C 头文件库，手动创建 Conan 配方 |
| 2 | 无构建系统 | 上游仅提供 .h 文件 | conanfile.py 直接 copy 到 include/sys/ |

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (header-library) |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 消费者测试 (LIST + RB tree) |
---

**编译结束**: 2026-09-04 06:35
**最终状态**: built
