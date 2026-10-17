# E6342 (draft) — OHOS SDK 26 的 fpos_t 是无 __pos 成员的 union，源码取 fpos_t 内部字段编译失败

> **Contributor**: Awstme | **Status**: DRAFT | **Updated**: 2026-09-13
> **Severity**: 2 (blocking) | **Category**: musl / fpos-t / sdk-header / portability
> **Audience**: 在 OHOS 上适配老 C/C++ 代码（fgetpos/fsetpos 家族）的配方维护者

## 错误特征

```text
lib/HTS_misc.c:251:27: error: no member named '__pos' in 'union _G_fpos64_t'
      return (size_t) pos.__pos;
                      ~~~ ^
1 error generated.
```

字面子串（`|` 分隔，非正则）：

```text
no member named '__pos'|union _G_fpos64_t|__opaque[16]
```

## 触发条件

- 构建系统：任意（本例为 autotools，实际由 clang 直接编译时即触发）
- 阶段：compilation（configure 已通过，编译期暴露）
- 平台：HarmonyOS PC，OHOS SDK 26.0.0.18 sysroot，clang 15.0.4（aarch64-unknown-linux-ohos）
- 场景：上游代码为兼容 glibc/Apple/Windows，写了 `fgetpos()` + 取 `fpos_t` 内部整数成员
  （glibc 是 `pos.__pos`）的分支；OHOS 的 `fpos_t` 没有该成员

## 根因分析

OHOS SDK 26 的 `sysroot/usr/include/stdio.h` 里：

```c
typedef union _G_fpos64_t {
        char __opaque[16];
        long long __lldata;
        double __align;
} fpos_t;
```

它是一个 16 字节的 **union**（`__opaque`/`__lldata`/`__align`），**没有** `__pos` 成员，
也没有命名整数成员可读；因此任何 `pos.__pos` 形式的上游兼容分支在 OHOS 上都是
**编译期硬错误**（`-Wregister` 那类可降级为警告的诊断不同，这个无法通过加 `-Wno-*` 绕过）。

实测（设备 `$HOME/ws/tmp/open-jtalk-1.11/src/hts_engine_API-1.10`，原始上游文件）：

```console
$ /data/service/hnp/bin/clang -I. -Iinclude -c lib/HTS_misc.c -o /dev/null
lib/HTS_misc.c:251:27: error: no member named '__pos' in 'union _G_fpos64_t'
      return (size_t) pos.__pos;
                      ~~~ ^
1 error generated.

$ grep -A5 'typedef union _G_fpos64_t' \
    /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/stdio.h
typedef union _G_fpos64_t {
        char __opaque[16];
        long long __lldata;
        double __align;
} fpos_t;
```

受影响的真实用例：open_jtalk 1.11 的私有依赖 hts_engine_API 1.10
（`lib/HTS_misc.c` 的 `HTS_ftell()`，见 PR 证据）。

## 与既有条目的差异（E414 不覆盖本模式，且其前提与本 SDK 版本不符）

E414（musl / file-position / calc 1.0 实测）讲的是**运行期**症状，并把平台前提取为：

> 在 HarmonyOS musl libc 上，fpos_t 是 struct { off_t __pos; mbstate_t __state; }

本 SDK 版本（26.0.0.18）的头文件实测是上面那个 **union**，既不是 struct，
也没有 `__pos`。因此：

| 维度 | E414 | 本条目 |
|------|------|--------|
| 暴露阶段 | runtime（`ftell` 返回乱码、seek 全失效） | compilation（编译直接失败） |
| 平台前提 | `struct { off_t __pos; mbstate_t __state; }` | `union _G_fpos64_t { char __opaque[16]; ... }` |
| 修复手法 | `FILEPOS` 改 `off_t`，`fgetpos/fsetpos` → `ftello/fseeko` | `fgetpos + pos.__pos` → `ftell()`（或 `ftello` + `off_t`） |

**可执行反证**（证明 E414 的“struct + __pos”前提在当前 SDK 上不成立，且其
`ftello/fseeko` 修法在本例同样不能照抄——本例代码是**读** `fpos_t` 内部字段，
`ftello` 只解决“不要碰 fpos_t”，并不提供 `pos.__pos` 这个不存在的成员）：

```console
$ grep -c '__opaque' /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/stdio.h
1
$ grep -c '__pos'   /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/stdio.h
0
```

（基线清理：以上命令不依赖任何 `GIT_CONFIG_COUNT` / 交叉编译参数注入，直接读设备
sysroot 头文件，因此结论不受本任务绕行手段污染。）

## 推荐方案

**方法**: source-patch（把读取 fpos_t 内部字段的写法换成标准接口）

```c
/* before */
fpos_t pos;
fgetpos((FILE *) fp->pointer, &pos);
#if defined(_WIN32) || defined(__CYGWIN__) || defined(__APPLE__) || defined(__ANDROID__)
      return (size_t) pos;
#else
      return (size_t) pos.__pos;      /* ← OHOS 无此成员 */
#endif

/* after（与同文件的 HTS_fseek() 用 fseek 保持一致） */
return (size_t) ftell((FILE *) fp->pointer);
```

要点：

1. 该文件既有的 seek 用的是 `fseek()`，因此配套改成 `ftell()` 语义自洽；
   若上游 seek 用 `fseeko()`，对应改成 `ftello()` 并把返回类型改 `off_t`。
2. 不要试图用 `-Wno-*` 压这个诊断：成员不存在是硬错误，不是可降级告警。
3. 若确实需要 `fpos_t` 的“不透明”语义（保存/恢复位置），用 `fgetpos/fsetpos`
   整对象传递即可，不要读取其内部字段。

**验证命令**:

```console
$ /data/service/hnp/bin/clang -I. -Iinclude -c lib/HTS_misc.c -o /dev/null && echo COMPILE_OK
COMPILE_OK
```

## 关键词

fpos_t, __pos, _G_fpos64_t, __opaque, fgetpos, ftell, ftello, musl, HarmonyOS,
OHOS SDK 26, hts_engine_API, open_jtalk, portability

## 元数据

- doc_file: doc/E6342.md
- source_event: open-jtalk 1.11 适配（私有内建 hts_engine_API 1.10）
- similar_to: E414, E011
- draft: true
