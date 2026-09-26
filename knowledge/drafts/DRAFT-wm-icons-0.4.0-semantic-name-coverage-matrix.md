# 图标资源包的核心断言是「语义名清单 × 实现集」的**覆盖率矩阵**，不是文件数：所有集合的并集必须覆盖全部标准名，且完整集必须实现全部名字

**来源**：`wm-icons 0.4.0` 适配（路径 B 知识库扩展）
**日期**：2026-09-19
**状态**：DRAFT ｜ 上游用例 N=0，本包新增断言 18/18

## 根因

1) 这类资源包的价值不是"某个目录里有多少文件"，而是**语义名 → 图标文件**的映射：
   窗口管理器按 `window-close`/`calculator` 这样的语义名取图；
2) 31 个集合（不同尺寸/风格）各自实现这份清单的一（部分）子集，**少一个语义名**
   就等于那一类图标在整个系统里没有实现（取图为空）；
3) "目录里有 83 个文件"这类断言完全发现不了 —— 它不知道"应该有哪些名字"。
   实测 wm-icons 0.4.0：`icons/names.lst` 84 个标准名、31 个集合、文件总数 2069，
   其中 `16x16-kde` 单个集合就完整实现了全部 84 个名字。

## 修法（可复用）

自检按"矩阵"写：① 清单存在、名字数、无重复、不带扩展名；② 所有集合的并集覆盖全部
标准名；③ 至少有一个完整集实现全部名字；④ 逐文件校验本体（PNG 魔数 / XPM 头）；
⑤ 每个集合的文件数与上游逐字一致。

## 判定 / 验证命令

```
ls <pkg>/share/wm-icons/icons/names.lst                     # 清单存在且 84 行
grep -c '/\* XPM \*/' <pkg>/share/wm-icons/icons/16x16-kde/*  # 完整集实现数
python3 test_package/test_wm_icons.py <package_folder>         # 覆盖率矩阵断言
```

## 与已有条目的边界

相似条目：[E255, DRAFT-debian-archive-keyring-2025.1-verify-binary-assets-without-external-tools]

`E255` 是数据包通用方法但未涉及"清单 × 多实现"结构；`DRAFT-debian-archive-keyring-…`
处理二进制资产的结构自解析，本条处理**语义名覆盖率**，判据不同。

## 覆盖范围

所有图标/字体类资源包（wm-icons、papirus-icon、adwaita-icon、pop-icon…）
以及任何"一份清单 + 多份实现"的资源包（locale、mime、schema）。
