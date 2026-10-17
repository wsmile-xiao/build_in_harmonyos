# coinutils 2.11.13.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-08
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied | HMDFS mktemp -d umask 077 | 替换为 mkdir -p + umask 022 |
| 2 | config.guess 不识别 HarmonyOS | 上游版本旧 | 补丁 0001+0003 |

## 验证结果

测试统计: 总计 10 项, 通过 10, 失败 0, 跳过 0

---

**最终状态**: built
