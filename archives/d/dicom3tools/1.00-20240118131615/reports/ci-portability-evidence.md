# CI #44678 失败分诊与可移植性修复 — 原始输出留档

> 本文件记录 PR !9618 首次 CI 失败的真实根因与修复验证。
> `BEGIN/END VERBATIM CAPTURE` 标记之间的内容与源文件**逐字节相同**。
> 复核：`sed -n '/^<!-- BEGIN VERBATIM CAPTURE ci-portability.txt -->$/,/^<!-- END VERBATIM CAPTURE ci-portability.txt -->$/p' reports/ci-portability-evidence.md | sed '1d;$d' | sha256sum`

| 属性 | 值 |
| --- | --- |
| 原始文件 | `ci-portability.txt` |
| 字节数 | 3423 |
| 行数 | 89 |
| sha256 | `a9df71c6fdc906aa9f11fe983e9dea6b971d1cd9ea35f0c5f3c0b09501b863c9` |
| 采集命令 | 见块内各命令块（设备实测，`/system/bin/toybox` 与 GNU coreutils 对比） |
| 采集时间 | 2026-09-12（设备本地时间） |
| 采信轮提交 | `48813722e1ccb489db358f51e973a6376ced5c03` |

<!-- BEGIN VERBATIM CAPTURE ci-portability.txt -->
# CI 可移植性缺陷：obsolescent sort 键语法 —— 原始验证输出

> 采集时间：2026-09-12（设备本地时间）
> 目的：证实 CI #44678 的真实根因并验证修复，而不是依赖推断。

## 1. CI 原始报错（PR !9618 构建 #44678 的评论原文）

```
gawk -f ../support/modtype.awk <../standard/module.tpl | _POSIX2_VERSION=199209 sort -b +1 -2 +0 -1 >modtype.txt
sort: Unknown option '2' (see "sort --help")
make[2]: *** [Makefile:192: modtype.txt] Error 2
```

紧接着的级联报错（**与真正原因无关**）：

```
../.././libsrc/include/dctool/elmconst.h:2:2: error: #endif without #if
dcdisp.cc:103:38: error: use of undeclared identifier 'OverlayRows_GROUP'
ge9800mdt.cc:57:35: error: use of undeclared identifier 'AcquisitionTime_GROUP'
make[2]: *** No rule to make target '../.././libsrc/lib/libdctl.a', needed by 'ancreate'.  Stop.
```

## 2. 设备上复现 CI 的确切报错（用设备自带的 toybox）

```
$ printf 'b 2\na 1\n' | /system/bin/toybox sort -b +1 -2 +0 -1
sort: Unknown option '2' (see "sort --help")          ← 与 CI 逐字相同

$ printf 'a\nb\n' | /system/bin/toybox xargs -L 1 echo
xargs: Unknown option 'L' (see "xargs --help")        ← 第二处同类问题
```

现代语法在 toybox 上正常：

```
$ printf 'b 2\na 1\nc 1\n' | /system/bin/toybox sort -b -k2,2 -k1,1
a 1
c 1
b 2

$ printf 'a\nb\n' | /system/bin/toybox xargs -n 1 echo
a
b
```

## 3. 为什么设备一直没发现

```
$ for t in sort xargs sed cat head tail; do ls /data/service/hnp/bin/$t; done
  → 全部不存在（hnp 只提供 gawk / grep / egrep / clang 等）
$ command -v sort
  → /storage/Users/currentUser/usr/local/bin/sort  （GNU coreutils 9.10，接受 +N -M）
```

即：设备与 CI 都从「系统」取这些工具，但设备装的是 GNU coreutils，
CI worker 落到 OHOS 基础系统的 **toybox**。属 §11.1「设备全绿 ≠ CI 绿」。

## 4. 语法等价的逐字节验证

```
$ _POSIX2_VERSION=199209 sort -b +1 -2 +0 -1 < modtype 输入   # GNU 旧语法参考
$ busybox sort -b -k2,2 -k1,1 < 同一输入                     # 新语法
$ cmp                                                       → 逐字节一致（2591 行）

$ elmdict/*.tpl 全部 18 个文件：GNU `-b -n +0 -1 +4 -5` vs busybox `-b -k1,1n -k5,5n`
  → 18/18 逐字节一致
```

## 5. 全量构建验证（toybox userland）

| 项 | 结果 |
| --- | --- |
| 垫片 | `sort xargs sed cat head tail tr uniq wc cut expr basename dirname date od` 全部指向 `/system/bin/toybox` |
| 修复前（toybox + 旧语法） | `make modtype.txt` → `rc=2`、输出 0 行、报错与 CI 相同 |
| 修复后（toybox + 新语法） | 全量原生构建 **NATIVE BUILD OK**，`error:|Error [0-9]` 计数 **0** |
| 关键产物 | `modtype.txt` 2591 行、`elmdict.tpl` 17182 行、`elmconst.h` 10331 行 |

## 6. 输出等价性（改动不改变产物）

CI 模拟构建（toybox 工具 + 6 补丁）与 Conan 构建（GNU 工具 + 5 补丁）
产出的三个受影响文件**逐字节相同**：

```
$ cmp <conan>/libsrc/docs/modtype.txt                        <ci-sim>/... → 一致
$ cmp <conan>/libsrc/standard/elmdict.tpl                    <ci-sim>/... → 一致
$ cmp <conan>/libsrc/include/dctool/elmconst.h               <ci-sim>/... → 一致
```

CI 上的 `elmconst.h` 是 **2 行**（只剩 `#endif`），修复后为 **10331 行**。
<!-- END VERBATIM CAPTURE ci-portability.txt -->
