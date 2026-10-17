# DRAFT-mdetect-0.5.2.6-on-exit-gnu-only-c-libc：OHOS/musl libc 无 GNU 扩展 on_exit() —— 头文件无声明 + 链接 undefined symbol: on_exit

> Contributor: 主理-1 | Status: Draft | Updated: 2026-09-30
> Source: mdetect 0.5.2.6 适配（任务 8750）本地 conan create 通过、CI 待验
> 对应：`knowledge/drafts/DRAFT-mdetect-0.5.2.6-on-exit-gnu-only-c-libc.kv`

## 现象

Debian orig tarball `mdetect_0.5.2.6.tar.xz` 的 `mdetect.c` 在退出路径注册清理回调：

```c
on_exit(restore_serial_settings, (void *)dev);
```

在 OHOS PC（aarch64，musl C 库，clang-15/lld）上**编译通过、链接失败**：

```console
p.c:2:24: warning: call to undeclared function 'on_exit'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
ld.lld: error: undefined symbol: on_exit
>>> referenced by probe_onexit.c
>>>               /storage/Users/currentUser/probe_onexit-949cec.o:(main)
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
```

关键特征两条，缺一即不是本条：

1. 头文件**没有** `on_exit` 声明 ⇒ 先出 `-Wimplicit-function-declaration` 警告；
2. 链接期 `ld.lld: error: undefined symbol: on_exit`，**没有** `Operation not permitted` / `Error 126` 之类签名或执行权限字样（与 ELF 签名族 E318/E486/E511 区分）。

## 根因

`on_exit(void (*function)(int, void *), void *arg)` 是 **glibc/GNU C 库扩展**：注册退出回调时把
`exit()` 的 `status` 与调用方传入的 `arg` 一并回传。POSIX 只标准化了
`atexit(void (*)(void))`，**没有参数**。

OHOS PC 的 C 库基于 musl：

```console
$ nm -D /lib/ld-musl-aarch64.so.1 | grep -w on_exit
（空）
```

即「头文件不声明 + 动态库无符号」，于是编译阶段只报警告、链接阶段报 undefined symbol。
这与平台签名、执行权限、工具链版本都无关，是纯 **libc API 差异**（glibc 扩展族）。

## 推荐方案（本包采用，已验证）

把 `on_exit(cb, arg)` 改成 `atexit(cb_wrapper)`：因为 `atexit` 的回调不带参数，用**文件级静态变量**
承载原 `arg`，回调签名从 `void cb(int status, void *arg)` 改成 `void cb_wrapper(void)`。

before（`mdetect.c`，上游原样）：

```c
static void restore_serial_settings(int status, void *dev);   /* 原签名带 status/arg */
...
on_exit(restore_serial_settings, (void *)dev);
```

after（`archives/m/mdetect/0.5.2.6/patches/0001-mdetect.c.patch`）：

```c
static void restore_serial_settings_atexit(void);
static struct device *atexit_devices = NULL;    /* 承载原第 2 个参数 */
...
atexit_devices = dev;
atexit(restore_serial_settings_atexit);
```

约束：

- 回调内**不使用** `status` 参数时，该改法语义完全等价（本例就是）；
- 只落源文件补丁，**不加 `__OHOS__` 宏、不加 stub、不动 libc**（R6/R8、PF5）；
- 多注册点或必须用 `status` 时，退到 fallback：源码内自建 `on_exit` shim（`atexit` + 静态槽位），
  但要先证明 `status` 不被依赖。

验证：

- 负例探针（改前）：`clang p.c -o p` → `ld.lld: error: undefined symbol: on_exit`，exit=1；
  符号面 `nm -D /lib/ld-musl-aarch64.so.1 | grep -w on_exit` 为空。
- 正例（改后）：`ohc-run.py conan-verify mdetect 0.5.2.6` → **Verdict PASS**（G2 conan create 通过），
  产物 `mdetect`：ELF shared object, 64-bit LSB arm64, `/lib/ld-musl-aarch64.so.1`，63936 B。
- 端到端：`CI_PACKAGES="archives/m/mdetect/0.5.2.6" zsh ci/conan/build_and_test.sh` → conan create passed。

## 与同族条目的区分（查重结论）

| 条目 | 签名 | 解法 | 是否重复 |
|------|------|------|----------|
| 本条 | `undefined symbol: on_exit` + implicit declaration 警告 | `atexit()` + 文件级静态承载参数 | — |
| E020 | `_IO_FILE` / `struct __FILE` 不完整定义 | `source-patch`（opaque 封装） | 否（签名、解法均不同） |
| E026 | `__thread` / TLS glibc 扩展 | `use-standard-tls` | 否 |
| E029 | bash malloc 与 musl 不兼容 | `configure-disable-feature` | 否 |
| E032 | `_GNU_SOURCE` + `DIR`/`dirent` unknown type | `add-cflags` | 否 |
| E033 | ncurses wide char `_XOPEN_SOURCE_EXTENDED` | `add-cflags` | 否 |

`draft-review` 预审给出 `review-similar → E213`（灰区）：E213 是 `l64a()` 同样缺失于 musl，但**函数不同（l64a vs on_exit）、错误签名不同（`undefined reference to l64a` vs `undefined symbol: on_exit`）、主解法不同（E213 = implement-locally；本条主解法 = 换 POSIX 等价 `atexit()`，本地 shim 仅 fallback）**，故按新增条目申报并写入 `similar_to`。

图谱查重：`knowledge/graph/` 对 `on_exit` **命中 0**（drafts 目录里 4 条命中全是 `verification_exit`
的子串串扰）。⇒ 组合型/条目型均不判重，按 `create` 申报。

## 适用范围与反例

- 适用：OHOS/musl 上编译的 C 源码里出现 `on_exit()` 调用（glibc 扩展族）。
- 反例/解除条件：目标平台换成 glibc（有该符号）时无须改；回调**依赖 `status`** 时不能直接用本条
  主方案，须走 fallback shim 并证明 `status` 语义可近似。
- 风险：`atexit` 与 `on_exit` 的执行顺序在多次注册时按 LIFO 一致，但 `status` 不可得，属能力缩减，
  必须在 notes/PR 里披露。

## 来源

- 事件：mdetect 0.5.2.6 适配（平台任务 8750），A 机 worktree `~/qzy/主理-1-A-mdetect-0.5.2.6`
- 补丁：`archives/m/mdetect/0.5.2.6/patches/0001-mdetect.c.patch`（`conandata.yml` 以 `patch_file` 引用，枚数 1）
- 探针：`~/tmp/uc2/mdetect-A/probe_onexit.c`（负例，exit=1）
