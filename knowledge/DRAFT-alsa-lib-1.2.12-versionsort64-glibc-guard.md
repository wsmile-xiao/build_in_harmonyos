# alsa-lib 1.2.12：OHOS musl 缺 glibc-only `versionsort64` — `__GLIBC__` 门控回落 `alphasort64`

> 草稿（DRAFT）— 来自 alsa-lib 1.2.12（任务 `alsa-lib-1.2.12-r01-pc2-3-20260930T175745Z`）
> HarmonyOS PC（aarch64）第一轮适配的真实编译日志。
> 与 `.kv` 同 stem 配对：`knowledge/DRAFT-alsa-lib-1.2.12-versionsort64-glibc-guard.kv`

## 问题

`make` 编译 alsa-lib 1.2.12 时，两个文件中同一类错误：

```text
parser.c:2936:56: error: use of undeclared identifier 'versionsort64'
        err = scandir64(filename, &namelist, filename_filter, SORTFUNC);
                                                              ^
parser.c:2932:18: note: expanded from macro 'SORTFUNC'
#define SORTFUNC        versionsort64
```

- 出错文件：`src/conf.c:4143` 与 `src/ucm/parser.c:2932`（两处同一 `SORTFUNC` 分支）
- `make_rc=2`（日志 `tmp/alsa-lib-bootstrap/make-native.log`）

## 根因

上游用“排除名单”选择版本化排序函数：

```c
#if defined(_GNU_SOURCE) && !defined(__NetBSD__) && !defined(__FreeBSD__) \
    && !defined(__OpenBSD__) && !defined(__DragonFly__) \
    && !defined(__sun) && !defined(__ANDROID__)
#define SORTFUNC        versionsort64
#else
#define SORTFUNC        alphasort64
#endif
```

- `versionsort64` 是 **glibc-only** 扩展；`scandir64` / `alphasort64` 是 LFS 门面（musl 也有）
- OHOS 真机为 **musl libc**，但 `_GNU_SOURCE` 在 clang 下默认满足 → 名单条件成立 → 选中
  `versionsort64` → 未声明
- 排除名单只覆盖 BSD 系 / sun / Android，**不覆盖 musl/OHOS**

## 修复（最小补丁，勿用平台宏）

在名单条件中追加 `&& defined(__GLIBC__)`：

```c
#if defined(_GNU_SOURCE) && defined(__GLIBC__) && !defined(__NetBSD__) \
    && !defined(__FreeBSD__) && !defined(__OpenBSD__) \
    && !defined(__DragonFly__) && !defined(__sun) && !defined(__ANDROID__)
#define SORTFUNC        versionsort64
#else
#define SORTFUNC        alphasort64
#endif
```

- musl 不定义 `__GLIBC__` → 自动走 `alphasort64` 回落
- 判定语义是 **libc 族**而非平台 → 不引入 `__OHOS__` 宏，规避平台宏闸
  （PF5/R8：patches 默认禁止平台宏；libc 探针属既有例外口径）
- alsa-lib 1.2.12 两处同改：`src/conf.c`、`src/ucm/parser.c`

回退方案：不便改多处时，可在 configure.ac 加
`AC_CHECK_FUNCS([versionsort64])` 并用 `HAVE_VERSIONSORT64` 门控调用处
（与 pthread_cancel 先例 E085/E127 家族同法）。

## 验证

| 步骤 | 结果 |
|---|---|
| 修复前 `make -j2` | rc=2：`undeclared identifier 'versionsort64'`（两文件同错） |
| 修复后 `make -j2` | **rc=0** |
| 修复后 `make check` | **rc=0**（上游 Automake 2/2 PASS：config、midi_event） |
| conan create（配方 G2） | PASS（全库链完成） |

日志：`tmp/alsa-lib-bootstrap/make-native.log`（修复前）、
`make-native2.log` / `make-check-native2.log`（修复后）。

## 适用边界 / 反例

- 适用：任何在 `_GNU_SOURCE` 下用 glibc-only 排序/扫描函数的 C 库在 musl/OHOS 上的适配
- 反例：若上游已用 `__ANDROID__`/musl 探测或有运行时探测，则无需此补丁；
  纯 glibc 目标平台（正规 Linux 发行版）不受影响、也不应被此门控削弱功能