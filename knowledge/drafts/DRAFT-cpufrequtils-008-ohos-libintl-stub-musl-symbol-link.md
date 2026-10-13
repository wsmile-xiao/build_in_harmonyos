# DRAFT-cpufrequtils-008-ohos-libintl-stub-musl-symbol-link — OHOS 空壳 libintl.h × 链接桩不导出 gettext：私有声明头 + 系统 musl 取真符号

> **Contributor**: 链主-cpufrequtils（主理-2 派发）｜**Status**: DRAFT｜**Updated**: 2026-10-06
> **Severity**: 2 ｜ **Category**: compilation / linking / portability / gettext / libintl / ohos
> **Audience**: 无 autoconf、无 glib 的**裸 Makefile / 自研构建** C 包，在 OHOS 上直调 `gettext()`
> **触发实例**: cpufrequtils 008（任务 14913，分支 `feat/cpufrequtils-008`）

## 基本信息

- **来源事件**: cpufrequtils 008 适配，2026-10-06 B 机 `conan create` 首轮实撞
- **来源 commit**: （待提交后回填）
- **作者**: 链主-cpufrequtils（主理-2）

## 错误特征（逐字）

```
utils/info.c:440:9: warning: call to undeclared function 'gettext'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
utils/info.c:242:10: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *' [-Wint-conversion]
make: *** [Makefile:198: cpufreq-info] Error 1
```

只补声明后立刻换到第二阶段：

```
ld.lld: error: undefined symbol: gettext
>>> referenced by info.c
```

关键指纹：**编译期与链接期各卡一次**，两处根因不同；`grep -c gettext` 在
`sysroot/usr/lib/aarch64-linux-ohos/libc.so` 的动态符号表上为 **0**。

## 根因（两层，2026-10-06 现场逐条实测）

| 层 | 实测 |
|---|---|
| ① 头文件层 | `ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/libintl.h` **只有 353 字节**：仅 `#define __USE_GNU_GETTEXT 1`、`#define __GNU_GETTEXT_SUPPORTED_REVISION(major)`、`#define __fa(n)`（且随后 `#undef __fa`），**零函数声明** ⇒ 源码里 `#include <libintl.h>` 后的 `gettext()` / `textdomain()` 全部落成隐式 `int`，clang 15 把 `-Wint-conversion` 判 **error**（不是 warning） |
| ② 链接层 | **链接桩** `sysroot/usr/lib/aarch64-linux-ohos/libc.so`（79424 B）只导出 **1592** 个符号，`llvm-nm -D \| grep -E " (gettext\|dgettext\|textdomain\|bindtextdomain\|ngettext)$"` = **0 命中** ⇒ 只补声明必然 `undefined symbol: gettext` |
| ③ 反转证据 | 设备运行时的系统 musl loader `/lib/ld-musl-aarch64.so.1`（2185824 B，**SONAME `libc.so`**）实测**导出** `gettext`(0x180a1c) `dgettext` `ngettext` `textdomain` `bindtextdomain` ⇒ **"链接桩没有" ≠ "运行时没有"**，只要把 `-L/lib -l:ld-musl-aarch64.so.1` 放进链接行，ld 会把它解析成普通 `libc.so`，`llvm-readelf -d` 的 `NEEDED` **只多不出**（仍只有 `libc.so`） |

## 最小修复（两部分，零 conan 依赖、非桩函数）

1. **声明层** —— 生成一份按 musl 公开 `<libintl.h>` 逐字补齐 9 个函数声明的**私有头**，
   `save()` 到构建私有目录并用 `-I` **前置于 sysroot**：

```python
compat_dir = os.path.join(self.build_folder, "ohos-compat-include")
save(self, os.path.join(compat_dir, "libintl.h"), LIBINTL_HEADER)
cppflags = "-I" + compat_dir
```

2. **符号层** —— 链接行加系统 musl（仅 OHOS）：

```python
if str(self.settings.os) == "OHOS":
    ldflags = "-L/lib -l:ld-musl-aarch64.so.1"
# build(): 'CPPFLAGS="{cpp}" LDFLAGS="{ld}" make V=true NLS=false CC=... cpufreq-info cpufreq-set'
```

两条命令后 `cpufreq-info` / `cpufreq-set` 链接通过，`DT_NEEDED` 只有 `libc.so` + `libcpufreq.so.0`。

## 验证（本包实测）

```
# 头文件层实测
cat $SDK/sysroot/usr/include/libintl.h | wc -c                    # 353
# 链接桩符号实测
llvm-nm -D --defined-only $SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so | wc -l   # 1592
llvm-nm -D --defined-only /lib/ld-musl-aarch64.so.1 | grep -E " (gettext|textdomain)$"
#   0000000000180a1c T gettext   /   0000000000180974 T textdomain
# 最小复现：手写声明 + 系统 musl ⇒ 编译链接运行三段全通
clang g2.c -o g2 -L/lib -l:ld-musl-aarch64.so.1 && ./g2          # hello / cpufrequtils
# 配方侧
conan create archives/c/cpufrequtils/008 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing            # G1-G4 + L2/L4/L5 PASS
```

消费者 21/21 断言 PASS，其中 `cpufreq-info -d` 实打实读出 `dfc_cpu_driver`、
`-l` 读出 `418000 2050000`（`PASS LIMITS_OK 418000-2050000`），证明翻译调用链与
sysfs 读取链在真机上都活着。

## 禁忌

- 不要用 `-Wno-implicit-function-declaration -Wno-int-conversion` 蒙过编译：隐式 `int`
  返回值在 aarch64 上会把 64 位指针截成低 32 位，运行期必崩（比编译期失败更坏）；
- 不要 `#define gettext(x)=(x)` 恒等宏：那是**关掉真符号**，本条的全部价值就在于
  `-L/lib` 这条零依赖的真符号通路（恒等宏另有 linuxinfo/speech-dispatcher 先例，非本条）；
- 不要为此引入 `requires("libintl/0.26.1")`：制品仓该包导出的是 `libintl_gettext` /
  `g_libintl_gettext` **改名符号**，与源码直调的 `gettext` 对不上，还要多背一个运行期依赖；
- 不要改 sysroot、不要在补丁里写 `__OHOS__`（PF5）：本方案**不产生任何补丁文件**。

## 适用范围 / 反例

- **适用**：OHOS 上直调 `gettext()`/`textdomain()` 的 C 包，且**没有** autoconf 探测层、
  **没有** glib 代理层（有那两层的包走各自的既有解法，见查重）。
- **反例**：源码只在 `ENABLE_NLS` 宏内调 gettext（linuxinfo 形态）⇒ 恒等回退更省；
  源码经 glib `gi18n.h` 走 `g_dgettext` ⇒ 走 proxy-libintl（appstream 形态）。
- **解除条件**：若某天 SDK 链接桩补上 gettext 符号，第 2 步可直接删（第 1 步仍需要）。

## 查重与新增价值（2026-10-06 四范围 + drafts 实测）

| 范围 | 命中 |
|---|---|
| `经验文档/适配经验汇总.md` | `gettext`/`libintl` 仅 §5.2 转载的 API 对照表一行（「`gettext()`/libintl 不提供 → 桩函数替代」） |
| `knowledge/graph/index.tsv` | 关键词含 `gettext` 或 `libintl` 的**共 9 行**：E015、E027、E107、E123、E135、E142、E443、E460、E508 —— 主题分别是 configure 缺 `-lintl`、`--disable-nls` 关闭 NLS、GLib 静态 `g_libintl_` 链接、meson proxy-libintl、libintl 签名后加载、`ENABLE_NLS` 链接、gettextize/gnulib bootstrap、GLib proxy-libintl，**无一条**讲"空壳头 + 链接桩与运行时分离" |
| `经验文档/经验库/` | 同上 API 对照表；无对应条目 |
| `经验文档/B草稿库/` | 只有 gnulib gettext FUTEX 死锁一条，机制不同 |

最接近的三份**草稿（非正式条目）**与本条的层次差：

1. `DRAFT-13410-trueprint-libintl-stub-header` —— 同一根因（空壳头），但它把结论写成
   **"OHOS libc has no gettext at all"**，修法是 autoconf 双宏守卫 + 链入
   `replace/libreplace.a`。**本条的 `③ 反转证据` 正是对那句话的修正**：链接桩没有 ≠ 运行时没有，
   系统 musl 有；且本条不依赖 autoconf、不依赖包内自带实现。
2. `DRAFT-appstream-1.2.0-ohos-gettext-proxy-libintl-header` —— 同一根因，修法是**复制 glib
   包内的 proxy libintl.h 并把符号改名成 `g_libintl_*`**；本包不依赖 glib，无法走该路。
3. `archives/l/linuxinfo/4.2.3` 的 `0003-linuxinfo-nls-identity-fallback.patch`（已合入配方，
   非草稿）—— 同一根因，修法是 `ENABLE_NLS` 分支 + **恒等翻译回退**（`--disable-nls` 语义），
   关掉了真符号；本包源码**无条件** include 与调用，没有可挂的宏。

⇒ 依 `AGENTS §6.2⑦` 判 **`create`**（hit 条件 2：症状相同、但既有条目没写这条解法）。
新增价值 = 把「空壳头」「链接桩 1592 符号无 gettext」「系统 musl 有符号」三件事连成一条
**零 conan 依赖、零补丁、非恒等宏**的可执行修法，并修正既有草稿里"libc 完全没有 gettext"的过强结论。

`draft-review` 实跑（2026-10-06，本包 `knowledge/drafts/`）：质量预检 `signature=✅ root_cause=✅ rec=✅`；
相似正式条目 TOP3 = **E081 0.26 / E015 0.25 / E093 0.25**（全部 < 0.30 灰区阈值，更远低于 0.55 并入阈值）
⇒ **预审建议 `create`**。E081/E093 是 musl 缺 glibc 扩展函数族（`secure_getenv`/`getpass`），
E015 是 configure 探到 `libintl.h` 却没加 `-lintl` 的链接配置问题 —— 三条都不是"空壳头 + 链接桩与运行时分离"。
