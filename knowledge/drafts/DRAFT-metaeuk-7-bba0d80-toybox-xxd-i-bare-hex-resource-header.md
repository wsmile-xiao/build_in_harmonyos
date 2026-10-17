# DRAFT-metaeuk-7-bba0d80-toybox-xxd-i-bare-hex-resource-header — toybox xxd -i 只输出裸 hex 体，生成的资源头缺声明与 _len 变量

> **对应结构化数据**：`knowledge/drafts/DRAFT-metaeuk-7-bba0d80-toybox-xxd-i-bare-hex-resource-header.kv`
> **验证实例**：metaeuk 7-bba0d80（OHOS PC aarch64，MMseqs2 内嵌源码随上游 tag 归档）
> **关联 Issue**：#3249（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3249）
> **Status**: DRAFT ｜ **Severity**: 🔴 high ｜ **Updated**: 2026-09-22

## 1. 一句话

OHOS 的 `/usr/bin/xxd` 是 **toybox 实现**：`xxd -i` 只输出裸 hex 数组体，**没有** vim xxd
的 `unsigned char 名[] = {...}` 声明行和 `名_len` 长度变量——一切“构建期用 `xxd -i`
把资源文件内嵌成 C 头文件”的上游（MMseqs2 的 `compile_resource` 是典型）在 OHOS 上
生成的头文件必缺声明，`#include` 它的编译单元连锁报错。

## 2. 症状（逐字，metaeuk conan create 40% 处）

```
build/Release/lib/mmseqs/generated/CovSeqidQscPercMinDiag.lib.h:1:3: error: expected unqualified-id
error: unknown type name 'PrefilteringIndexData'; did you mean 'PrefilteringIndexReader'?
error: use of undeclared identifier 'CovSeqidQscPercMinDiag_lib'
error: use of undeclared identifier 'CovSeqidQscPercMinDiag_lib_len'
```

坑点：连锁报错全部指向**业务头文件**（PrefilteringIndexReader.h / rescorediagonal.cpp），
与真正的病灶（最早生成的 `generated/*.lib.h` 首行）离得很远。

## 3. 根因与最小复现

**输出契约对照（本机实测）：**

```
$ printf 'AB' > t.txt && xxd -i t.txt        # toybox 0.8.12（/usr/bin/xxd）
  0x41, 0x42                                  # ← 只有数据体，没有声明、没有分号、没有 _len

$ perl lib/mmseqs/cmake/xxdi.pl t.txt        # vim xxd -i 的 perl 等价实现
unsigned char _t_txt[] = {
	0x41, 0x42,
};
unsigned int _t_txt_len = 2;                  # ← 完整声明三件套，命名规则与 vim xxd 一致
```

MMseqs2 的 `lib/mmseqs/cmake/MMseqsResourceCompiler.cmake` 用 `xxd -i` 生成资源头，
随后只做一次 `sed 's/unsigned char/static const unsigned char/'`——toybox 输出里
根本没有 `unsigned char` 行可替换，产物就是无名 hex 体。metaeuk 的全部生成头
（PAM30.out.h、*.lib.h、*.sh.h…）实测同形态。

**根因链**：toybox xxd 只覆盖 hex dump 主功能，`-i` 模式省略了声明行与长度变量。

## 4. 修法（已验证）

补丁一行替换（`patches/0001-mmseqs-resource-compiler-toybox-xxd-no-declaration.patch`）：

```cmake
-find_program(XXD_EXECUTABLE xxd)
+set(XXD_EXECUTABLE "")     # 跳过 toybox xxd，走下方 xxdi.pl 兜底分支
```

模块自带兜底分支会 `find_program(perl)` 并改用 `xxdi.pl`（shebang `#!/usr/bin/env perl`，
构建 env PATH 含 `/data/service/hnp/bin/perl`）。`patch --dry-run` PASS。

⚠ **必须清缓存重建**：坏头文件是 `add_custom_command` 的 OUTPUT，只改生成脚本而
DEPENDS 不变时 CMake **不会重新生成**——本机删除该包 conan 缓存构建树
（`$CONAN_HOME/p/b/<pkg_id>`）后干净重建才作数。

## 5. 适用范围 / 反例 / 解除条件

- **适用**：CMake/Make 里出现 `xxd -i`（或 xxdi.pl）生成 `*.h` 的包——MMseqs2 家族
  （metaeuk/seqkit 类）、把 wav/矩阵/脚本内嵌进二进制的工具。
- **反例**：资源头直接提交在源码树里（非构建期生成）的包；上游自己补声明后处理的包。
- **解除条件**：上游改用不依赖 xxd 输出契约的方案（cmake -P 脚本/Python）。

## 6. 查重与新增价值

toybox 族既有条目覆盖 sed/expr（E010）、ash（E043）、install（E098/E182/E188）、
cat 与 GNU cat 的 stdout 差异（E106）——均为“命令缺失/选项不支持/行为差异”，
**没有条目覆盖 `xxd -i` 的输出契约差异**。`DRAFT-ohos-gl-symbols-are-dispatcher-stubs`
等 GL 条目与本条无关。判 create。

## 7. 触发实例与证据

- metaeuk 7-bba0d80（本 PR）：conan-create.log 首错原文 + generated 产物头部 hex 采样；
  `~/tmp/uc2/DS-30-metaeuk/`、`~/tmp/uc2/DS-30/probe-cppflags/t.txt` 对照产物。
