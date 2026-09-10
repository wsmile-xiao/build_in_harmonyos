# DRAFT：conan apply_conandata_patches 严格行号与跨版本补丁累计态

> 状态：DRAFT（待主编审核晋升 E 条目）｜作者：B4Q2｜日期：2026-09-09
> 触发实例：connect-proxy/1.105（PR #9036，从 connect/1.106 借补丁实撞）

## 问题

从上游邻近版本借来的补丁（本例：connect/1.106 的两个可移植性补丁用于 connect-proxy 1.105），
`patch -p1 --dry-run` 全部通过，但 `conan create` 在 `apply_conandata_patches` 阶段失败：

```
WARN: .../patches/0001-connect.c.patch: hunk no.1 doesn't match source file at line 256
      expected: b'#define WITH_RESOLVER 1'
      actual  : b''
ERROR: ... ConanException: Failed to apply patch: .../patches/0001-connect.c.patch
```

第二形态：多补丁顺序应用时，基于 pristine 源生成的第 2 个补丁（0002，getpwuid 回退，
hunk 在 @@ -642 区域）在第 1 个补丁（+14 行位移）之后应用，conan 报 0002 的 hunk 不匹配。

## 根因

conan 2.x 的 `apply_conandata_patches` 内置 patcher **按补丁头行号严格取上下文，无 GNU patch
的模糊偏移搜索**。跨版本补丁的行号属于"别的版本的文件"；GNU patch 靠上下文搜索仍能命中，
两者判定可以相反。多补丁时行号还必须基于**累计态**（前序补丁已叠加的位移），基于 pristine
生成的后续补丁天然错位。

## 最小复现

1. pristine 1.105 源 + 1.106 版补丁对：`patch -p1 --dry-run` 两发全过；
2. 同一补丁对进 conandata.yml 跑 `conan create`：
   0001 报 4 处 `hunk no.N doesn't match`，`source file is different`，构建失败。

## 方案（regenerate-cumulative-diff）

1. 取 pristine 源树；依次应用既有补丁得到累计基线；
2. 目标补丁的**改动内容**可在累计基线上用 GNU patch 模糊应用（内容允许借自邻近版本）；
3. **最终入库的补丁文件**必须由
   `diff -u --label a/<f> --label b/<f> 基线/文件 结果/文件` 重新生成，
   行号基于该补丁被应用时的累计态；
4. 可应用性判据用 `conan create`（或 patch-ng），**不用** GNU patch dry-run。

本例修正后（0001 基于 pristine、0002 基于累计态），conan create 两补丁全部干净应用，
G2/W3 通过（PR #9036 当前 HEAD）。

## 反例与禁止

- 禁止以 `patch --dry-run` 通过作为 conan 补丁可应用性的最终判据（fuzz 掩盖错位）。
- 若不想维护累计行号，可将全部改动合成单补丁（pristine 生成），顺序应用天然满足；
  代价是丢失 patch_type 分类语义。

## 查重

- E279：讲"零上下文补丁块 + patch-ng/GNU 行为分歧"——本条是"全上下文补丁 + 跨版本基线 +
  多补丁累计态"，触发面不同；
- E282：多源码包子目录根错位——不同根因；
- E248：单补丁文件内 hunk 排序（Makefile.am/Makefile.in）——不同层；
- E254：toybox patch 的 --dry-run new-file 差异——不同工具差异面。
  以上均未覆盖"跨版本借补丁 + 严格 patcher + 累计态"组合，故立新条目。

## 验证证据

- 失败日志：connect-proxy W3/finish conan-create.log（WARN hunk no.1..4 / ConanException）；
- 修正后：regenerated patches → conan create G2 PASS（verify4.log）→ W3 通过；
- 复现/校验命令：`patch -p1 --dry-run`（初筛）+ `conan create`（终判）。
