# DRAFT-ohos-std-ranges-for-each：OHOS clang/libc++ 缺 C++20 Ranges → std::ranges::for_each 不可用

> Contributor: SnowTT | Status: Draft | Updated: 2026-09-06
> Source: ausweisapp 2.5.4 HarmonyOS PC adaptation（PR #7912）
> 对应：knowledge/drafts/DRAFT-ohos-std-ranges-for-each.kv

## 现象

以 C++20 编译、使用 `std::ranges::for_each` 的 C++ 源码在 OHOS 工具链下
编译期报 Ranges 命名空间/算法不存在：

```text
error: 'std::ranges::for_each' is not a member of 'std::ranges'
   (或 no member named 'ranges' in namespace 'std')
```

AusweisApp 2.5.4 的 `src/ui/dev/UiPluginDev.cpp` 用
`std::ranges::for_each(platformFiles, ...)` 对文件列表做前缀拼接，
在 OHOS clang/libc++ 下编译失败。

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条目增量（差异化） |
|----------|----------|--------|----------------------|
| E032 | graph | musl 头文件缺 `DIR`/`opendir`/`readdir` 声明（`_GNU_SOURCE`/`_BSD_SOURCE` 宏） | C 头文件/宏声明层，修法为加 cflags |
| E292 | graph | Arrow 大型数据处理库测试分层迁移与环境补齐；`std::ranges::equal` 仅是其一串错误签名中的 token，**不涉及 Ranges 缺失的修复** | 本条目沉淀"OHOS libc++ 缺 Ranges 算法 → range-for 等价改写"这一独立修复知识 |

`std::ranges::for_each` 全库查重（index.tsv + graph 542 条 + drafts 83 条）
0 命中，属真增量；E032 是 C 头文件声明缺失，E292 是测试迁移条目，均非
C++20 Ranges 库缺失的适配修复知识。

## Root Cause

OHOS 交叉工具链的 clang/libc++ 不提供（或裁剪了）C++20 Ranges 库实现，
`<algorithm>` 等头文件中 `std::ranges` 命名空间缺失或其成员算法不可用。
项目以 `-std=c++20` 编译时，Ranges API 在编译期不可见——这是 **libc++
头文件/实现缺功能**，而非项目 include 路径或 `-std` 级别问题。

## Recommended Solution

1. **主方案**：用标准 range-for 循环替换 `std::ranges::for_each`
   （`for_each` 语义与 range-for 一一对应，等价改写最简单）：

   ```cpp
   // 原（依赖 C++20 Ranges）:
   std::ranges::for_each(platformFiles, [&](QString& s) {
       s.prepend(QStringLiteral("/"));
       s.prepend(selector);
   });

   // 改（等价 range-for）:
   for (QString& s : platformFiles)
   {
       s.prepend(QStringLiteral("/"));
       s.prepend(selector);
   }
   ```

   可在 conanfile.py `source()` 中对源码文件做等价改写后写回，避免维护
   独立补丁。

2. **回退方案**：若项目大量依赖视图/管道等复杂 Ranges 语义无法逐处改写，
   评估升级/更换 OHOS 工具链 libc++ 实现；改动面大、受 SDK 版本约束，
   一般作为回退。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| ausweisapp/2.5.4 | `UiPluginDev.cpp` 用 `std::ranges::for_each` | OHOS libc++ 编译失败 |
| ausweisapp/2.5.4 | 改写为 range-for 循环 | 编译通过（配合 PCSC/LINUX 修复，PR #7912 进展） |

## 测试覆盖边界

- 覆盖：`std::ranges::for_each` 调用点改写后的编译期正确性（遍历语义一致）。
- 未覆盖：视图/管道等更复杂 Ranges 语义的等价改写；`std::ranges` 其余
  算法在 OHOS 的可用性需逐点验证。
