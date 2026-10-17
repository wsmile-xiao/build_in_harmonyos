# ntl 11.6.0.2 — 改出共享库

与 `11.6.0.1` 的差异**只有一处意图**：`SHARED=off` → `SHARED=on`
（`package_type` 随之改为 `shared-library`）。上游源码 URL、sha256、`NTL_GMP_LIP=on`
及其余 configure 参数全同。

## 为什么需要这个版本

sage / passagemath 的 NTL 绑定是**一组各自独立的扩展 `.so`**
（`ntl_ZZ_p` / `ntl_ZZ_pContext` / `ntl_ZZX` …，仅 passagemath-ntl 就 34 个）。
静态链接时**每个 `.so` 各揣一份 NTL 的全局状态**：`ntl_ZZ_pContext` 里设好的模数
上下文，`ntl_ZZ_p` 根本看不见，于是拿未初始化的模数做运算 —— **SIGSEGV**。

实撞（2026-08-14，HarmonyOS PC 真机）：passagemath-ntl 10.8.7，`ZZ_p` 模乘
**三种写法全崩**，而不依赖跨模块状态的 `ZZX` / `GF2X` 一切正常 —— 正是这个机制的指纹。

```
ntl:ZZ_p 模乘(modulus=ntl_ZZ)   CRASH 信号 11
ntl:ZZ_p 模乘(modulus=int)      CRASH 信号 11
ntl:ZZ_p 模乘(显式 context)      CRASH 信号 11
ntl:ZZX 多项式乘法               PASS
```

三种写法并排是为了**分清「真 bug」与「调用方 API 用错」**——全崩才坐实是包的问题。

上游 `passagemath_ntl-10.8.7-cp311-cp311-musllinux_1_2_aarch64.whl` 打包了
`libntl-c04b8675.so.45.0.0`：**动态链接是上游的既定设计**，静态是本仓的偏离。

## 修好了什么（同设备同测试，只换包）

| 用例 | 11.6.0.1（静态） | 11.6.0.2（共享） |
|---|---|---|
| `ZZ_p` 模乘 ×3 种写法 | CRASH ×3 | **PASS ×3** |
| 18 条真算合计 | PASS 13 / CRASH 3 | **PASS 15 / CRASH 0** |

> 余下 2 条非 PASS 是 `ModuleNotFoundError: sage.libs.pari` 一类，
> 即**尚未构建的兄弟发行包**，与本包无关。

产物侧对照（`sage/libs/ntl/ntl_ZZ_p*.so`）：

```
静态版  DT_NEEDED 无 libntl      571,904 字节   wheel 16 MB
共享版  DT_NEEDED libntl.so.45   158,144 字节   wheel 4.2 MB
```

受影响的不止 passagemath-ntl：`passagemath-flint`（4 个扩展）与
`passagemath-linbox`（6 个）同样内嵌 NTL，**三个 wheel 都要用本版重建**才算修干净。

## SHARED=on 才会踩到的三个坑

静态构建根本不建 libtool、也不需要自己解析编译器内建符号，所以这三个此前全藏着。

**1. `config.guess` 认不出 HarmonyOS** → `patches/0002`

`SHARED=on` 时 NTL 会先自建 libtool，而 `DoConfig` 里是**裸 `./configure`**、没有传参口子：

```
UNAME_SYSTEM = "HarmonyOS"
configure: error: cannot guess build type; you must specify one
```

补丁只开一个口子（读 `NTL_LIBTOOL_CONFIG_ARGS`），**不写死平台**——Linux 构建留空、
行为不变；recipe 仅在 `os == OHOS` 时注入 `aarch64-unknown-linux-ohos`
（NTL 自带的 `config.sub` 2024-05-27 版认得 `*-linux-ohos`，已实测）。

**2. `umask 077` 让 config.status 失败**

```
./config.status: ./confXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

报的是权限，实为 umask 太严。处置沿用 conan-packager 生成器里既有的
`fix_umask`（把源码树里所有 `configure` 的 `umask 077` 改成 `022`）。
注意 `libtool-build/configure` 是**构建时**从 `libtool-origin/` 复制的，
所以必须在跑 NTL 的 configure **之前**就改掉整棵源码树。

**3. `libntl.so` 缺 `__udivti3`**

```
Error relocating libntl.so.45: __udivti3: symbol not found
```

128 位除法等**编译器内建函数**在 compiler-rt 里；静态库时由最终可执行文件补上，
共享库则带着未定义符号出厂。

> ⚠️ 两个「看着该管用」的做法**实证无效**，别再试：
> ① `LDFLAGS` 里加 `-rtlib=compiler-rt`（可执行文件的链接行里能看到它，但库没用上）
> ② `LIBTOOL_LINK_FLAGS=-Wc,-rtlib=compiler-rt`（NTL 文档 doc/config.txt:496 给的钩子，
>    确实落进了生成的 makefile:43，照样没用）
>
> 原因：libtool 建共享库时用 **`-nostdlib`** 自己拼全套链接行，
> `-rtlib=` 这类**驱动层选项**在那条命令里不起任何作用。

唯一有效的是把 builtins 归档**当普通文件参数**放上链接行 —— `makefile:397` 的
`$(LDLIBS)` 正在那个位置。路径由 `clang -print-libgcc-file-name` 现取，
不写死 SDK 版本；取不到即 `ConanInvalidConfiguration` 报错，不让它悄悄退化成
一个「装得上、一跑就崩」的包。

不用 `LIBTOOL_LINK_LIBS`：它一旦显式赋值，`NTL_THREADS=on` 时自动加的 `-lpthread`
就被顶掉（doc/config.txt:502-509）。`LDLIBS` 默认值 `-lm` 同理必须带上。

## 质量状态

真机（HarmonyOS PC MateBook）用 CI 的 profile `conan create` 通过，上游 `make check` 通过。

```
libntl.so.45.0.0  3,635,712 字节  + 软链 libntl.so / libntl.so.45
SONAME            libntl.so.45
GMP 后端           config.h:100  #if 1 → #define NTL_GMP_LIP   （未因改 SHARED 丢失）
未解析内建符号      无
```

`11.6.0.1` 保持原样。只用 C 接口、且不跨多个 `.so` 共享 NTL 全局状态的下游不受影响。

## 已知差异（未处理）

上游 wheel 还打包了 `libgf2x.so.3`，即 NTL 构建时开了 `NTL_GF2X_LIB=on`；
本包仍是 `off`。这不影响正确性（`GF2X` 用例通过），仅可能影响 GF(2)[X] 的性能。
本次**刻意不动**——一个版本只改一个变量。
