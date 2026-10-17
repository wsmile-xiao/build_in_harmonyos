# draft-gsmlib-0.8.7-autotools-vpath-top-srcdir-include

## 症状

gsmlib 0.8.7 在 Conan out-of-tree 构建（ohc-run.py conan-verify → conan create，
构建目录 `build-release/<subdir>`）时，gsmlib/apps/tests/ext 四目录编译全部报：

```
fatal error: 'gsmlib/gsm_nls.h' file not found
#include <gsmlib/gsm_nls.h>
```

而同样的源码 in-tree 构建（`./configure && make`，编译目录即源码子目录）不报错。

## 根因

上游各子目录 Makefile.in 声明 `INCLUDES = -I..`。in-tree 构建时子目录编译的
cwd 是源码树内目录，`-I..` 恰好指向源码根，`<gsmlib/...>` 可解析；但
VPATH/out-of-tree 构建（conan 把源码拷贝到 build 目录后在其下创建
`build-release/<subdir>` 编译）时，cwd 是 build 树，`-I..` 只到 build-release，
源码根位于 `$(top_srcdir)`（生成后 Makefile 中为源码绝对路径），因此
`<gsmlib/...>` 头无法解析。这是老 autotools 工程常见假设：INCLUDES 用相对
`..` 隐含 in-tree 构建。

## 方案

对产生自引用头 `#include <lib/...>` 的每个子目录 Makefile.in，把
`INCLUDES = -I..` 改为 `INCLUDES = -I.. -I$(top_srcdir)`。
`$(top_srcdir)` 在 configure 生成的 Makefile 中指向源码根，out-of-tree 构建
下 `<lib/...>` 头即可解析；in-tree 构建不受影响（-I.. 仍可用）。

gsmlib 实现见 archives/g/gsmlib/0.8.7/patches/ 下 0001-apps /
0002-ext / 0003-gsmlib / 0008-tests 四个 Makefile.in 补丁。

## 验证

- 修复前：conan create 在四目录编译均报 `fatal error: 'gsmlib/gsm_nls.h'
  file not found`
- 修复后：`conan-verify gsmlib 0.8.7` G1-G4+L2/L4/L5 全 PASS，四目录全部
  编译通过；test_package 消费者 Passed

## 适用边界 / 反例

- 适用：任何 autotools 多目录工程，其子目录 Makefile 用 `-I..` 且源码含
  `#include <工程名/头文件>` 自引用，且需要 out-of-tree/VPATH/conan 构建。
- 反例：单目录工程或源码用相对 `#include "..."`（无 `<lib/...>` 前缀）不适用。

## 查重差异（七轴）

- exact_duplicate: 无；causal_duplicate: 无；trigger_overlap: 中（与 E217
  的 "fatal error: xxx.h not found" 表面同触发，但 E217 根因是 conan 配方
  安装路径，本候选根因是 autotools INCLUDES 相对路径）；solution_overlap:
  无（E217 改 CMakeLists 安装 include；本候选改 Makefile.in INCLUDES）；
  combination_novelty: 是；boundary_novelty: 是（in-tree 过/out-of-tree 败）；
  test_migration_novelty: 是
- similar_to: E217（头找不到，不同根因）、E075（include 路径环境变量）；
  caused_by: 老 autotools 假设 in-tree 构建；prerequisite_of: 无；
  conflicts_with: 无
