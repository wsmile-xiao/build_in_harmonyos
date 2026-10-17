# DRAFT-motif-2.3.8-musl-no-rindex-xpm-guard：musl 无 rindex 与 XpmI.h 特性宏门控的冲突

> Status: Draft | Updated: 2026-09-13
> Source: motif 2.3.8 HarmonyOS PC 适配（libXm.so.4 链接期定位）
> 对应：knowledge/drafts/DRAFT-motif-2.3.8-musl-no-rindex-xpm-guard.kv
> 关键词：rindex, strrchr, musl, XpmI.h, SVID, libXm, Motif, 遗留字符串函数

## 现象或适配场景

libXm 编译全部通过，链接阶段报：

```text
ld.lld: error: undefined symbol: rindex
>>> referenced by Xpmdata.c:427
>>> referenced by XpmWrFFrI.c:115
clang-15: error: linker command failed with exit code 1
```

同一份源码在 glibc 发行版上可直接构建（上游 CI 即如此）。

## 根因

`rindex(3)` 是 BSD/SVID 时代的 `strrchr` 别名。glibc 的 `<strings.h>` 无条件声明它；
**musl 不提供该遗留符号**。上游 `lib/Xm/XpmI.h` 本有兼容映射，但被特性宏门控：

```c
#if defined(SYSV) || defined(SVR4) || defined(VMS) || defined(WIN32) || defined (_SVID_SOURCE)
# include <string.h>
# ifndef rindex
#  define rindex strrchr
# endif
#else
# include <strings.h>      /* musl：不声明 rindex */
#endif
```

OHOS/musl 不落进任何分支，使用点因此留下两个未定义符号。

## 修复步骤

在配方 OHOS 分支的 `CPPFLAGS` 追加一个宏定义即可，零补丁、零源码改动：

```python
environment.append("CPPFLAGS", "-Drindex=strrchr")
```

先做"缺口唯一性"核对，避免误判（本包实测未定义符号表中只有 `rindex` 一个真实缺口）：

```bash
llvm-nm -D --undefined-only libXm.so.4 | grep -E '^ *U ' | sort -u
```

## 验证方式

- 加宏前：`ld.lld: error: undefined symbol: rindex`；加宏后：链接通过。
- `conan create` 全链路绿：`assertions=18 failures=0`，`libXm.so.4.0.4` 生成，
  `dlopen("libXm.so.4")` 解析 Xm/Xt 入口点 7/7 OK。

## 适用范围和安全边界

适用于所有在 musl/OHOS 上构建、含 Xpm 源码或同类"特性宏门控的遗留函数映射"的库
（Motif/libXm、独立 libXpm 及其分支）。边界：宏定义只做符号别名，不得借此夹带行为
修改；`-D_SVID_SOURCE` 是副作用更大的备选，仅在宏定义方式覆盖不全时才用。
