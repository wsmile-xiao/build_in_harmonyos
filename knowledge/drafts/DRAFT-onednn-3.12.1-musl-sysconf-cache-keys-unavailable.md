# OHOS musl 没有任何 `_SC_LEVEL*` 缓存 sysconf 键，且真机无 sysfs cache 拓扑：缓存探测两级数据源同时失效

- draft: true
- contributor_id: iKalous_OscarP
- 触发事件：onednn 3.12.1 适配（分支 `feat/onednn-3.12.1`，任务 #9165）
- 取证环境：HarmonyOS PC 真机，`ohos-sdk@26.0.0.18` 的 clang 15 + OHOS sysroot（musl）

## 错误特征（真机原始日志）

oneDNN 内嵌的 `third_party/xbyak_aarch64/src/util_impl_linux.h` 在
`setCacheHierarchy()` 的兜底分支里无条件写 `sysconf(_SC_LEVEL1_ICACHE_SIZE)`，
在 OHOS 上属于**编译期**失败：

```
neg.c:2:37: error: use of undeclared identifier '_SC_LEVEL1_ICACHE_SIZE'
int main(void){ return (int)sysconf(_SC_LEVEL1_ICACHE_SIZE); }
                                    ^
1 error generated.
```

同一份代码在 glibc 上连编带跑都正常，所以这不是"某个库的怪补丁"，而是 libc
元数据面的差异：报错文本是"宏名不存在"，不是"取值失败"，这一点决定了修法。

## 触发条件

| 维度 | 命中条件 |
|---|---|
| 平台 | OHOS / HarmonyOS PC（musl 系 sysroot，非 glibc） |
| 阶段 | compilation（缺宏）→ runtime（伪造宏则拿到 -1） |
| 工具 | clang、cmake、make 皆同；与构建系统无关 |
| 代码模式 | 任一 `sysconf(_SC_LEVEL*_SIZE)` / `sysconf(_SC_LEVEL*_LINESIZE)`；或"先读 `/sys/devices/system/cpu/cpuN/cache/index*`，再退回 sysconf"的探测函数 |

## 根因分析（实测数字）

真机对同一问题的**两条**常规出路分别验证：

| # | 数据源 | 取数命令 | 实测结果 |
|---|---|---|---|
| 1 | musl confname 表 | `grep -c '^#define _SC_' $SYS/usr/include/unistd.h` | 141 个 `_SC_*`（编号连续到 248） |
| 2 | 其中缓存键 | `grep -c '_SC_LEVEL' $SYS/usr/include/unistd.h` | **0** |
| 3 | 整个 SDK 头树 | `grep -rl '_SC_LEVEL1_ICACHE_SIZE' $SYS/usr/include \| wc -l` | **0 个文件** |
| 4 | 整个 SDK 头树 | `grep -rl '_SC_LEVEL1_DCACHE_LINESIZE' $SYS/usr/include \| wc -l` | **0 个文件** |
| 5 | sysfs 拓扑回退 | `ls -d /sys/devices/system/cpu/cpu*/cache \| wc -l` | **0**（cpu0…cpu19 目录都在，均无 `cache` 子目录） |
| 5b | sysfs 并非整体不可用 | `cat /sys/devices/system/cpu/cpu0/regs/identification/midr_el1` | `0x00000000482fd423`（implementer `0x48` = HiSilicon），能读，但 `cacheInfoDict[2]` 只有 A64FX(`0x46`…) 等两项 → 字典必然 miss |
| 6 | sysconf 本身可用 | `sysconf(_SC_PAGESIZE)` / `sysconf(_SC_NPROCESSORS_ONLN)` | 4096 / 20（接口正常，只是没有这两个键） |
| 7 | 伪造宏名兜底 | `#define _SC_LEVEL1_ICACHE_SIZE 190` 后调用 | `icache=-1 errno=22(EINVAL)`、`linesize=-1 errno=22` |

机制链条：glibc 在 confname 枚举里给了缓存键，musl 没给；xbyak_aarch64 的
`setCacheHierarchy()` 先试 `cacheInfoDict[midr_el1]`（本机 CPU implementer
`0x48` = HiSilicon，字典无此项），再试 `readCacheInfoFromSysDevice()`（第 5 行
= sysfs 无目录），最后落到 `sysconf(_SC_LEVEL*)`（第 2/3 行 = 编译期就没有这个
宏）。**三级探测在 OHOS 上一、二级空、三级不存在**，于是唯一可行解是常量兜底。
第 7 行是本文最要强调的坑：把"编不过"改成"能编过"的宏补齐法，得到的是 -1，
而 -1 会被下游当容量用。

## 解决方案

**推荐（上游可提交形态）**：给探测点加**宏存在性守卫**，glibc 路径逐字保留：

```c
#ifdef _SC_LEVEL1_DCACHE_LINESIZE
    return sysconf(_SC_LEVEL1_DCACHE_LINESIZE);
#else
    return 64;      /* 本机实测常量；行大/容量常量按平台文档取值 */
#endif
```

真机验证：守卫形态的独立探针编译通过并运行
（`pos_build_rc=0` → `l1i=32768 guard_taken=constant`），而同一 sysroot 下无守卫
形态必失败（上文 `neg.c`）。

**回退（配方内最小 diff）**：在 Conan 配方 `source()` 里用 `replace_in_file`
把 sysconf 兜底那 4 行整体换成常量——`archives/o/onednn/3.13`（已合入）与
本 PR 的 `archives/o/onednn/3.12.1/conanfile.py` 即此写法，补丁上下文在
3.12.1 上逐字命中。代价必须写明：这段代码在非 OHOS 平台也不再读真实缓存容量，
属于只在鸿蒙构建产物里成立的降级，不能伪装成可上游化的修复。

**禁止做法（均有实测依据）**

| 做法 | 为什么不行 | 实测 |
|---|---|---|
| `#define _SC_LEVEL1_ICACHE_SIZE 190` 之类补宏 | 编译过了，运行期是 -1/EINVAL，负容量进入分块运算 | 第 7 行：`icache=-1 errno=22` |
| 改读 `/sys/devices/system/cpu/cpu0/cache` | 本平台根本没有该目录树 | 第 5 行：`0` 个目录 |
| 关 JIT / 关测试绕开该分支 | 掩盖平台缺陷，rule4 少报、rule8/9 新增不足 | — |

## 通用性证据（独立于本库）

1. **独立最小语料**：上表 7 组数字全部来自两个 3~10 行的独立 C 文件
   （`neg.c` / `pos.c` / `base.c` / `bogus.c`），只用 OHOS clang + OHOS sysroot，
   不链接、不依赖 oneDNN，任何库都能照抄复现。
2. **第二个库（main 里已合入的独立受害者）**：
   `archives/p/pxr-vt/26.08/patches/0001-arch-fixes-for-ohos.patch` 对
   `Arch_ObtainCacheLineSize()` 用的正是本文推荐的 `#ifdef _SC_LEVEL1_DCACHE_LINESIZE`
   守卫形态；`archives/o/onednn/3.13/conanfile.py` 是回退形态。同一类问题在
   main 里两个互不相关的软件树上各出现一次，说明它是一类而非单库补丁。
   取数：`git grep -l '_SC_LEVEL' <tip> -- archives`。

## 查重反证

main tip `8f56191952c22d8f024ac0ebabaab5b4a52b19c7`：

```
正式条目数  knowledge/graph/E[0-9]{3}.kv              = 540
草稿 .kv 数 knowledge/drafts/*.kv                     = 1316
git grep -ilE '_SC_LEVEL|ICACHE_SIZE|cpu0/cache' <tip> -- knowledge | wc -l = 0
git grep -l  'sysconf' <tip> -- knowledge/graph      = E036.kv, E465.kv(+index.tsv,pre-scan-rules.yaml)
```

即 540 正式 + 1316 草稿里 **0 命中**本机制的任何一个签名。逐条边界：

| 相邻条目 | 它的机制 | 可执行反证 |
|---|---|---|
| E036 | Python `sysconfig.get_platform()` 把含空格的 HongMeng 内核串拼进路径 | `grep -c '_SC_' knowledge/graph/E036.kv` → 0；关键词是 sysconfig/uname，非 confname |
| E465 | worker loader 拒载用户目录 .so，改走 embedded-Python launcher | 签名是 `ctypes.CDLL(None)`/dlopen，与 libc 宏存在性无关 |
| E361 / E365 / E396 | 关键词里含 "topology" 一词被粗筛命中（MPI 分离进程族 / Conan 包身份） | `grep -ilE 'cache\|_SC_\|sysconf' knowledge/graph/E36{1,5}.kv knowledge/graph/E396.kv` → 无 |

与 E137（Perl 把编译器选项塞进 ldflags）也不同：那条是"参数被投递给错误的工具"，
本条是"接口常量在目标 libc 上不存在"。

## 证据

- 分支 `feat/onednn-3.12.1`，配方 `archives/o/onednn/3.12.1/`（conanfile.py 的
  `source()` 内 sysconf 分支替换 + `notes.md` 问题表）
- 真机取证目录 `~/work/psj/onednn121/kb/`（`neg.c` `pos.c` `base.c` `bogus.c`
  及各自产物），CONAN_HOME 独立于共享缓存：`~/work/psj/ch-onednn`
- 探针脚本：`tools/probes/on312_cache_kb.sh`、`tools/probes/on312_cache_kb2.sh`
  （本仓会话侧，非交付物）
