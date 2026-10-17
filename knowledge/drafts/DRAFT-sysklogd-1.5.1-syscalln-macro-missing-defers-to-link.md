# DRAFT-sysklogd-1.5.1-syscalln-macro-missing-defers-to-link — glibc 内核头宏 `_syscallN()` 在 OHOS musl sysroot 中不存在：clang 把落空的宏降级成警告，失败点后移到**链接期**未定义符号；正解是改调 libc 已有的包装函数（本包 `klogctl()`）

- 包／归档：sysklogd 1.5.1 → `archives/s/sysklogd/1.5.1/`（syslogd + klogd，纯 Makefile，非 Autotools）
- 补丁：`patches/0001-klogd-use-klogctl.patch`（`patch_type: portability`，新增行不含任何平台宏）
- 路径：Path B（知识库扩展）
- 取证机：鸿蒙 PC（HarmonyOS PC，aarch64，`ohos-sdk_26.0.0.18`，clang 15.0.4，target `aarch64-unknown-linux-ohos`）
- 编号：DRAFT-sysklogd-1.5.1（草稿，未取正式 E 槽位）

---

## 1. 现象（真机原文，非预测）

**关键结论先摆出来：这个机制不在编译期炸，而在链接期炸。**

把补丁 0001 回退（`patch -p1 -R`）后，用与配方逐字一致的命令重编 klogd：

```
$ make -j1 CC=/data/service/hnp/bin/clang prefix=/data/storage/el2/base/skl-b0/prefix \
      SKFLAGS="-O2 -DSYSV -Wall" LDFLAGS="" klogd
/data/service/hnp/bin/clang -O2 -DSYSV -Wall -DFSSTND   -c klogd.c
klogd.c:287:15: warning: type specifier missing, defaults to 'int'; ISO C99 and later do not support implicit int [-Wimplicit-int]
_syscall3(int,ksyslog,int, type, char *, buf, int, len);
              ^
              int
   （同一行另有 287:28 / 287:42 / 287:52 / 287:1 共 5 条同型警告，编译步骤 RC=0）
...
/data/service/hnp/bin/clang  -o klogd klogd.o syslog.o pidfile.o ksym.o ksym_mod.o
ld.lld: error: undefined symbol: ksyslog
>>> referenced by klogd.c
>>>               klogd.o:(Terminate)
>>> referenced by klogd.c
>>>               klogd.o:(main)
>>> referenced 4 more times
>>> did you mean: vsyslog
>>> defined in: syslog.o
clang-15: error: linker command failed with exit code 1 (use -v to see invocation)
make: *** [Makefile:86: klogd] Error 1
```

- 编译步 **RC=0**（只有 `-Wimplicit-int` 警告）；
- 失败发生在 **链接步**，未定义符号是 **`ksyslog`** ——它不是任何 libc 的导出符号，而是"本该由 `_syscall3()` 宏展开生成出来的本地存根函数名"。本包对它有 **5 处运行期调用**（行号取自本次对照树 `/data/storage/el2/base/skl-b0` 的已打补丁 `klogd.c`：362 / 548 / 569 / 585 / 951，`type` 参数依次 0 / 8 / 1 / 7 / 2；未打补丁时行号各减约 15，未逐条复核故不给数）；
- lld 顺手给的 `>>> did you mean: vsyslog` 是**诱导项**：它把注意力往"libc 缺 syslog 符号"上带，而那恰好是 E014 的诊断口径（见 §4）。

打回补丁后同一命令：`MAKE_RC=0`，产物 `syslogd` 55744 B + `klogd` 43392 B（与该包正式构建的字节数一致）。

## 2. 根因（三层，每层都有回指证据）

1. **上游写法**（`klogd.c:278-286`，上游 1.5.1 原样）：

   ```c
   #define __LIBRARY__
   #include <linux/unistd.h>
   #if !defined(__GLIBC__)
   # define __NR_ksyslog __NR_syslog
   _syscall3(int,ksyslog,int, type, char *, buf, int, len);
   #else
   #include <sys/klog.h>
   #define ksyslog klogctl
   #endif
   ```

   语义是"只要不是 glibc，就用内核头宏自己拼一个裸 syscall 存根"。历史上游只在 glibc 侧被编译过，`!__GLIBC__` 这条支路依赖的 `_syscallN()` 族宏本就是 glibc 时代 `<linux/unistd.h>` 的产物。

2. **OHOS sysroot 实况**（本次逐条重跑，非引用旧结论）：

   | 检查 | 命令 | 结果 |
   |---|---|---|
   | `_syscallN` 宏族是否存在 | `grep -rn 'define _syscall' $SYSROOT/usr/include` | **0 命中** |
   | 同上（另一写法） | `grep -rn '_syscall3' $SYSROOT/usr/include` | **0 命中** |
   | `__GLIBC__` 是否定义 | `printf '#ifdef __GLIBC__ …' \| clang -E` | 输出 `GLIBC_NO`（不定义）⇒ 必走自造存根支路 |
   | syscall 号 | `grep -rn '__NR_syslog' $SYSROOT/usr/include` | `aarch64-linux-ohos/bits/syscall.h:117` `#define __NR_syslog 116` |
   | libc 包装函数原型 | `grep -n klogctl $SYSROOT/usr/include/sys/klog.h` | 第 8 行 `int klogctl (int, char *, int);` |
   | libc 导出符号 | `nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so \| grep -i klog\|syslog` | `T klogctl` / `T syslog` / `T vsyslog` |

   `$SYSROOT = /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`

3. **失效机理（症状为什么会骗人）**：宏不存在时，`_syscall3(int,ksyslog,…);` 落在文件作用域上被 clang 按"返回类型为隐式 int"的老式声明解析，5 条 `-Wimplicit-int` 警告逐字落在该行的各个类型符上（287:15 / 287:28 / 287:42 / 287:52 / 287:1），编译步骤 RC=0、`.o` 正常产出；而这个存根函数**永远不会有定义** ⇒ 故障点后移到链接期。调用点之所以连"隐式函数声明"警告都不出现，是因为上游在 `klogd.c` 里另有完整原型 `extern int ksyslog(int type, char *buf, int len);`（该行号 338 取自对照树已打补丁的文件，未打补丁时位置略有前移）——于是整条构建日志里关于根因的唯一线索，只剩那 5 条看似无害的隐式 int 警告，以及链接期那个名字不像 libc 符号的未定义符号。

**一句话根因**：缺的是"生成存根代码的宏"，不是"内核能力"也不是"libc 符号"；而报错文本长得却像后者。

## 3. 最小复现（41 行探针，不含三方库代码）

设备侧文件：`/storage/Users/currentUser/tmp/uc2/sysklogd/syscall3-mechanism-probe.c`（日志同名 `.log`）

```c
#include <stdio.h>
#define __LIBRARY__
#include <linux/unistd.h>
#if !defined(USE_WRAPPER)                 /* 上游原样：自造存根 */
#  if !defined(__GLIBC__)
#    define __NR_ksyslog_probe __NR_syslog
_syscall3(int, ksyslog_probe, int, type, char *, buf, int, len);
#  endif
#else                                     /* 补丁处置：用 libc 已有包装 */
#  include <sys/klog.h>
#  define ksyslog_probe klogctl
#endif
int main(void){ char buf[16]; printf("rc=%d\n", ksyslog_probe(3, buf, (int)sizeof(buf))); return 0; }
```

| 臂 | 命令 | 结果 |
|---|---|---|
| A 编译 | `clang -O2 -Wall -c probe.c -o probe.o` | **RC=0**，6 条警告（5×`-Wimplicit-int` + 1×`call to undeclared function 'ksyslog_probe'`） |
| A 链接 | `clang -o probe-link probe.o` | **RC=1**，`ld.lld: error: undefined symbol: ksyslog_probe` |
| B 编译 | `clang -O2 -Wall -DUSE_WRAPPER -c probe.c -o w.o` | **RC=0**，0 警告 |
| B 链接 | `clang -o probe-wrapper w.o` | **RC=0**，产出可执行 ELF |

⇒ 同一份 41 行程序同时闭合"症状"与"解法"，复核人可在 1 分钟内重跑。

## 4. 与既有知识的区别（查重实证 + 引擎实测）

**检索面与读数**（2026-09-23，主检出 `knowledge/` 全量 + `archives/` 语料）：

- 精确 token `_syscall[0-9]` 在 `knowledge/`：**0 命中**（先前宽 grep `_syscall` 的命中全是 `si_syscall`、`missing_syscalls.c` 一类的**子串假阳性**）；
- `klogctl` 在 `knowledge/`：**0 命中**；在 `archives/` 整个语料：**0 命中**；
- 全仓 `archives/` 里出现过 `_syscall[0-9]` 的只有 2 个文件，其中真正处理过该机制的是
  `archives/a/acorn-fdisk/3.0.6/patches/0002-blkio-64bit-lseek-and-errno.patch`——它删掉
  `_syscall5(int,_llseek,…)` 自造存根、改调 libc 的 `lseek()`，**与本条同机制、同处置方向，但没有任何知识条目记录**。
  ⇒ 该机制在仓库里已实际发生 2 次、知识库 0 条，这是本条的新增价值与复用面。

| 条目 | 它的签名／阶段 | 它的解法 | 与本条的实质差异 |
|---|---|---|---|
| **E014** | `undefined reference.*syslog`（链接期，缺的是 **libc 符号 syslog**） | `add-cflags-disable` ⇒ `CFLAGS="-DNO_SYSLOG"` | **前提被本包实测证伪**——`libc.so` 明确导出 `T klogctl`/`T syslog`，`bits/syscall.h` 有 `__NR_syslog`。跑 E014 自己的验证命令即可排除它。照抄即自断 klogd 唯一功能 ⇒ 见 `.kv` 的 `forbid_1`（`conflicts_with`） |
| **E245** | `undefined symbol: vhangup`（libc **既无声明也无导出**，内核 syscall 在） | 自造 `syscall(SYS_vhangup)` shim | **方向相反的姊妹机制**。E245 是"libc 没封装 ⇒ 自己封"；本条是"libc 已封装 ⇒ 别自己封"。分界线是 `nm -D libc.so` 查不查得到包装，故写入 `fallback`（`similar_to`） |
| **E534** | `undefined symbol: gethostid` 等（缺的是 musl 不实现的 **GNU 扩展函数**） | 在 `missing_syscalls.c` 里用弱符号**自己补实现** | 本条缺的不是 libc 函数、且 libc 已有现成包装 ⇒ 解法既不是补实现、也不是禁 applet。依 手册/03 hit 条件②（"同症状但用既有条目没写的另一条解法"按 create 报）判 create |
| **E093** | `getpass` 隐式声明／未定义引用 | 补实现或 `--disable-feature` | 同一族"缺函数"，与本条"缺生成宏 + 故障点后移"无关（是引擎对关键词的误命中） |
| **E246** | 运行期 `SIGSYS`/`SYS_SECCOMP`（seccomp 拦 syscall） | 运行期降级、跳过受限功能 | **阶段不同（运行期 vs 链接期）、签名不同、处置不同**，完全不重叠 |
| E429/E531/E020 | musl 缺 glibc 专有符号／`__GLIBC__` 能力守卫 | 本地 shim／条件守卫 | 那些是"补实现或加守卫"；本条**不加任何平台/能力守卫**，而是把整条自造存根支路替换为 libc 包装（能力守卫写法在此反而是多余的） |

**引擎实测**（在同一 worktree 跑 `scripts/ohc-run.py engine`，用于回答"知识库会不会自己拦下这条"）：

| 查询 | 引擎命中 | 判读 |
|---|---|---|
| `ld.lld: error: undefined symbol: ksyslog referenced by klogd.c` | **E245**（Phase B） | 误——E245 的 rec 会让作者去自造 syscall shim，而 libc 的 `klogctl` 已在 |
| `call to undeclared function ksyslog _syscall3 implicit int` | **E093**（Phase B） | 误——getpass 家族，机制无关 |
| `klogctl syslog klogd musl _syscall3 macro missing` | **E014**（Phase B） | 误——rec 为 `-DNO_SYSLOG`，对本包是自断功能 |

⇒ 三条命中项的推荐方案对本包**全部为反效果或无效**，说明该机制在库里既没被覆盖、还会被现有条目误导。这是"必须入库"的正面理由，而不只是"没查到"。

**仓库 `draft-review` 实跑读数**（2026-09-23，`python3 scripts/ohc-run.py draft-review <本条 id> -p <worktree>`）：
质量预检 `signature ✅ / root_cause ✅ / rec ✅`；相似度 TOP3 = **E123 0.23、E245 0.20、E015 0.18**（阈值 ≥0.55 merge-into / 0.30–0.55 灰区 / <0.30 create），三态建议 **create**。
E123/E015 属 meson＋libintl 链接家族，仅因 `undefined symbol` 词面相近而被排到前面——正是 §4 表格要澄清的那类"表面相似、机制无关"。

**判重结论**：`create`（非 hit、非 none）。四条件自检——①症状无既有条目同形（`_syscall[0-9]` 0 命中）；②解法未被任何条目覆盖（E534 是补实现、E245 是自造 shim、E014 是关功能，本条是"改调已有包装"）；③引用精确（上表逐条给签名与解法差异）；④替代解法等效性已证明（见 §5 末段）。

## 5. 可复用处置（三步）

1. **先定性、别看报错阶段就开方**：跑两条能力核查
   `grep -rn 'define _syscall' $SYSROOT/usr/include`（应为 0，坐实宏族缺失）与
   `nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep <能力名>`（有 ⇒ 排除 E014/E245）。
2. **替换支路，不裁剪功能**：把上游 `#if !defined(__GLIBC__)` 的 `_syscallN()` 支路整段换成上游 glibc 支路已在用的 libc 包装函数——本包即

   ```c
   -#if !defined(__GLIBC__)
   -# define __NR_ksyslog __NR_syslog
   -_syscall3(int,ksyslog,int, type, char *, buf, int, len);
   -#else
   +#include <sys/klog.h>
   +#define ksyslog klogctl
   -#endif
   ```

   `klogctl(int, char *, int)` 与上游 `extern` 声明的 `ksyslog(int, char *, int)` 形参逐一对齐，**调用点一行不改**，5 个调用点全部保留 ⇒ 功能等效性由"同一 `__NR_syslog` 的官方包装 + 签名逐字对齐 + 链接期符号解析成立"三点支撑，不靠声明。
3. **补丁写成无条件形式**：判据是"libc 提供该包装"这一**能力事实**，不是"是不是 HarmonyOS"。因此新增行不含 `__OHOS__`/`__GLIBC__` 一类平台宏，R8/PF5 天然过关，且同一补丁在 musl 发行版与 glibc 上语义同样成立（glibc 也提供 `klogctl`）。

## 6. 适用面与反例

- **适用**：源码里出现 `_syscall0()`…`_syscall6()` 自造裸 syscall 存根的包（2000 年前后 Linux 工具族：sysklogd、util-linux/fdisk 系、busybox 早期分支、各类 kernel-tools 与守护进程）。预扫描判据已写进 `.kv` 的 `prescan_pattern: _syscall[0-9]`。
- **反例 1（走 E245）**：宏族缺失**且** libc 也没有对应包装 ⇒ 只能自己用 `syscall(SYS_xxx)` 写显式 shim。
- **反例 2（走 E534）**：缺的是 musl 不实现的 GNU 扩展**函数**（`gethostid`/`strverscmp`/…）⇒ 弱符号补实现。
- **反例 3（E014）**：只有当 `nm -D libc.so` 确实查不到该能力符号、且内核也不实现该 syscall 时，禁用功能才是正当出口；本包不满足。
- **未验证边界**：若工具链把 `-Wimplicit-int`／`-Wimplicit-function-declaration` 升为错误（更高版本 clang 或显式 `-Werror`），同一根因会在**编译期**现形、签名不同而处置相同——本条只在 clang 15.0.4 上实测，此分支**未验证**，派发时若遇到请补读数。
- **运行期另有限制（不属本条）**：本包里 `klogctl(2)` 的真机可读性受 `CAP_SYSLOG` 与 `/var/run` 不存在等平台事实约束（见归档 `notes.md` §9.4）。本条知识只覆盖到**编译/链接期**的机制与修法，不得据此声称"klogd 内核日志读取已真机验证"。

## 7. 证据清单（绝对路径，全部在鸿蒙 PC 上）

| 证据 | 位置 |
|---|---|
| 补丁回退／打回对照实跑全日志 | `/storage/Users/currentUser/tmp/uc2/sysklogd/b0-report.log`（2026-09-23 20:56，脚本 `b0-control-probe.sh`，副本树 `/data/storage/el2/base/skl-b0`，未改动前任的 `skl-f` 原件） |
| 41 行机制探针与四臂读数 | `/storage/Users/currentUser/tmp/uc2/sysklogd/syscall3-mechanism-probe.c` 与 `syscall3-mechanism-probe.log`（20:59） |
| 正式构建与验证 | `archives/s/sysklogd/1.5.1/reports/{conan-create.log,conan-verify-report.md,w3-local-ci.log}`，`conan-verify` G0–G4 PASS、`MEMCAP[run] peak=126MB rc=0`（`notes.md` §9、§10） |
| 静态前置取证（sysroot 头/宏/符号表） | `archives/s/sysklogd/1.5.1/notes.md`「★ 系统类难点（klogd / 内核日志接口）」小节 |
| 补丁与配方 | `archives/s/sysklogd/1.5.1/patches/0001-klogd-use-klogctl.patch`、`conandata.yml`、`conanfile.py`（分支 `feat/sysklogd-1.5.1`，取证基线 HEAD `b66ab68b409edce7e3b49e2509d7a5705273d26a`） |

**⚠ 对 `notes.md` 的一处更正（必须一并修）**：该文件 §风险清单 K1 与 §7 把症状预测为
「`call to undeclared function '_syscall3'`／编译期直接失败」，并把 G2 的判据写成"仍报 `_syscall3` = 0001 未应用"。
本次对照实测证明该预测**不成立**——编译步 RC=0，只有 `-Wimplicit-int` 警告；真实失败在链接期
`ld.lld: error: undefined symbol: ksyslog`。原预测属"未跑就先写"的推断（K1 自己标着"已定性，报错文本未验证"），
现按真机读数改写；G2 的"未出现"结论不变（补丁确实生效），但判据文字应按本条更正后的签名重写。
