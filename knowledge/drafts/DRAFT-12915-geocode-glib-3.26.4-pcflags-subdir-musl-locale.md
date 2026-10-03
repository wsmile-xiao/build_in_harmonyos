# DRAFT-12915 — PkgConfigDeps .pc Cflags 版本化 include 子目录补丁 + musl 无 locale 库的 g_test 豁免

> 草稿状态：pending-editor-review（拟提升编号由主编确认，草稿以 PR 号命名占位）
> 来源：geocode-glib 3.26.4 适配 PR #12915（j669539，鸡屁股队）

## 错误特征

```
fatal error: 'libsoup/soup.h' file not found        # .pc 单 -I 解析不到版本化子目录
'setlocale (LC_ALL, "en_GB.UTF-8")' should not be NULL   # musl 无 locale 数据库，g_test 断言中止
```

## 触发条件

- 依赖：GNOME 系 meson 库经 conan PkgConfigDeps 消费（libsoup-3.0 等），上游布局为
  `include/<pkg>-<ver>/<pkg>/xxx.h` 多级 + 消费者 `#include <pkg/xxx.h>`
- 测试：上游测试调 `setlocale(LC_ALL, "<locale>.UTF-8")` 且 g_test 断言非 NULL
- 环境：OHOS musl（无 locale 数据库）交叉构建

## 根因分析

1. **PkgConfigDeps .pc 的 Cflags 只写 `-I"${includedir}"`**：GNOME 系库上游把头文件
   装在版本化子目录（include/libsoup-3.0/libsoup/soup.h），单 -I 时
   `#include <libsoup/soup.h>` 找不到。这不是个别包问题——libsoup/gtk/geocode-glib
   等 GNOME 家族全是这个布局。
2. **musl 无 locale 数据库**：glibc 环境 setlocale 非空返回，musl 的 setlocale 对
   任何非 "C"/"POSIX" 名返回 NULL。g_test 框架的 `g_assert(setlocale(...) != NULL)`
   直接中止进程——是数据缺失而非行为差异，无法修补绕开，只能环境限制豁免。

## 解决方案

### 1) .pc Cflags 双路径补丁（build() 内幂等替换）

见 .kv 内代码块：定位生成的 libsoup-3.0.pc，把
`Cflags: -I"${includedir}"` 替换为 `-I"${includedir}/libsoup-3.0" -I"${includedir}"`。

### 2) locale 类测试豁免申报模式

断言原文+源码行号逐项在案（geocode-glib.c:419/:506/:701/:752），其余上游用例
以 OHOS 原生 ELF 直跑保真跑覆盖（LD_LIBRARY_PATH 注入依赖 libdir，libshumate 先例）。

## 降级方案（fallback）

- cpp_info.includedirs 指版本化基目录（消费者 -I 自带子目录）；
- 宿主环境跑测试二进制并显式声明平台差异。

## 红线

- 豁免必须附断言原文与行号（审核核验"环境限制"定性是否成立）；
- .pc 补丁幂等（重复 build 不叠加替换）。

## 实证

- verify_builds: #12915（CI passed / AI review passed / approved；上游 24/28 真跑
  [geo-uri 4/4、geocode-glib 10/10、mock-backend 10/10] + test_package 8/8）

## 与现有知识的关系（查重结论）

- **E348**（forwarding pc，graphene glib 模块别名）：讲 glib-2.0.pc 转发别名，
  未覆盖 Cflags 版本化子目录补丁——本条增量；
- **E023**（locale collation 测试跳过）：讲排序行为差异的单测试跳过，本条是
  musl setlocale NULL 断言中止（数据缺失级）+ g_test 框架交互，根因与处置不同；
- **E443/E545**：glib 工具 native launcher 与 NINJA pin——本条作复用声明，不重复申报；
- .pc Cflags 子目录 / setlocale NULL：图谱 grep **零命中**。
