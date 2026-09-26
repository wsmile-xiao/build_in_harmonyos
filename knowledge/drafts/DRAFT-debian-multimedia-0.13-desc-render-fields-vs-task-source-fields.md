# Debian Blend 成品 `<blend>-tasks.desc` 带 blends-dev 的**渲染期字段**（Relevance/Section/Parent/Key/Test-new-install），与 `tasks/` 源描述不是同一套字段 —— 自检不能拿源字段去校验成品

**来源**：`debian-multimedia 0.13` 适配（路径 B 知识库扩展）
**日期**：2026-09-19
**状态**：DRAFT ｜ 上游用例 N=0，本包新增断言 13/13

## 根因

1) `tasks/<name>` 是**源描述**，字段只有 Task/Description/Depends/Recommends…；
2) 成品 `<blend>-tasks.desc` 是 blends-dev 渲染后的结果，除 Task/Description 外还带
   Relevance/Section/Parent/Key/Test-new-install 这些**渲染期生成**的字段。
   实测 debian-multimedia 0.13：成品 `Section:` 27 处、`Parent:` 26 处、`Key:` 26 处、
   `Test-new-install:` 25 处，而 tasks/ 里这些字段一处都没有；
3) 反向也成立：`Depends:` 在 tasks/ 里出现 909 次，在成品里是 0 次
   —— blends-dev 把它展开成了 metapackage 的依赖列表。
4) 所以"源与成品字段可以互推"是错的：自检写错方向要么假失败（拿源字段要求成品），
   要么假通过（只数 Task 段数）。

## 修法（可复用）

自检按"形态"分两组：(a) 对成品 `.desc` 断言渲染期字段（Section/Parent/Key/Description 齐全）
与 Task 段数；(b) 对 `tasks/` 断言源字段（Task/Description）与文件集合。
不要用源字段校验成品，也不要用成品字段要求源。

## 判定 / 验证命令

```
grep -c '^Section:' <blend>-tasks.desc      # 成品有
grep -c '^Section:' tasks/*                # 源没有
grep -c '^Depends:' tasks/*                # 源有
grep -c '^Depends:' <blend>-tasks.desc     # 成品没有
```

## 与已有条目的边界

相似条目：[E255, DRAFT-debian-med-3.9.0-blend-tasks-desc-and-copy-src-pitfall, DRAFT-debian-gis-0.0.22-blend-family-batch-adaptation]

`DRAFT-debian-med-…` 讲的是成品与源的**集合**是包含关系；`DRAFT-debian-gis-…` 讲的是
同构包族批量适配的工程方法。本条讲**字段层面**的形态差异（渲染期字段只在成品里、
依赖字段只在源里），三者判据与修法互不重叠。

## 覆盖范围

所有 Debian Pure Blend 数据包（debian-multimedia/-med/-gis/-junior/-hamradio…）
以及任何"源 + 渲染成品"两形态并存的数据包（desktop entry、mime 数据库、图标缓存）。
