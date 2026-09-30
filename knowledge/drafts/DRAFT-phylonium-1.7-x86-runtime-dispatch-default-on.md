# DRAFT-phylonium-1.7-x86-runtime-dispatch-default-on

上游把 x86 SIMD/AVX512 开关默认 enable 且无 CPU 探测，分发层用 x86-only 内建函数，交叉到 aarch64-OHOS 编译期必挂

## 可复现症状（真机逐字签名）

HarmonyOS PC（aarch64-OHOS，clang-15）上按上游默认值 configure 后 `make -j1` 第一条真实错误：

```
revseqcmp.c:39:2: error: use of unknown builtin '__builtin_cpu_init' [-Wimplicit-function-declaration]
revseqcmp.c:41:6: error: use of unknown builtin '__builtin_cpu_supports' [-Wimplicit-function-declaration]
2 errors generated.
make[2]: *** [Makefile:472: revseqcmp.o] Error 1
```

注意签名层次：**不是** `-msse2/-mavx2/-mavx512bw` 之类编译选项不被支持，而是
`__builtin_cpu_init` / `__builtin_cpu_supports` 这两个内建函数在 aarch64 target 上根本不存在。
按"-m\* 选项问题"去猜会走偏（本条最初就是这么写的，真机把它否掉了）。

## 根因

`configure.ac` 的两个 `AC_ARG_ENABLE`（`x86simd`、`avx512`）**默认值都是 enabled，且没有任何
CPU 或三元组自动探测**；configure 直接把宏写进 `config.h`：

```
#define ENABLE_AVX512 1
#define ENABLE_X86_SIMD 1
```

于是 `libs/Makefile.am`、`src/Makefile.am`、`test/Makefile.am` 三处条件段把带 SSE2/AVX2/AVX-512
目标码的分发层拉进**默认**构建，而分发层在普通 `.c` 里调用 x86 专用运行期内建函数做 CPU 判断。

## 最小复现（不需完整配方）

1. 解包官方 tag 件 `v1.7`，`autoreconf -fi -Im4`（tag 件无预生成 configure）。
2. `env -u CONFIG_SHELL SHELL=/bin/sh ./configure --build=aarch64-unknown-linux-gnu`
   （带上依赖的 `CPPFLAGS/LDFLAGS/LIBS`，否则会先死在别的检查上——这是有效对照的前提）。
3. `grep -E '^#define ENABLE_(X86_SIMD|AVX512)' config.h` ⇒ 两宏均为 1，即默认状态被坐实。
4. `make -j1` ⇒ 复现上面第一条错误。

## 修复前后对照读数（同机同依赖，只变一个因素）

| 口径 | 改前（默认，不带 disable） | 改后（显式 `--disable-x86simd --disable-avx512`） |
|---|---|---|
| `config.h` 的 ENABLE 宏 | 两项均为 1 | 不定义 |
| 构建 | `make -j1` rc=2，首错见上 | `conan create` rc=0 |
| 上游测试 | 未执行（构建未过） | `make check` 注册 2 项 **2/2 PASS** |

修复做法：在配方的 `configure_args` 追加 `--disable-x86simd` 与 `--disable-avx512`，
**零改上游**。不打补丁删分发层源码，也不在编译参数上动手。

## 适用范围与反例

适用：同时满足两条的上游——一是架构相关 SIMD 开关**默认 enable 且无自动探测**，
二是运行期 CPU 分发代码写在会被默认构建的**公共编译单元**里。序列比对、压缩、图像、
信号处理类小包常见（本赛事池高频形态）。

不适用/反例：上游已用 `AC_CHECK_TARGET`/`__builtin_cpu_*` 之外做了架构守卫，或分发层被独立
可选模块/条件编译天然排除，则不需要本条；若某上游**根本没有** disable 开关，则只能走源码守卫
（见 `.kv` 的 fallback），那属于补丁路径，必须逐项写进补丁说明且不得借此缩小测试分母。

## 查重结论

`经验文档/*.md`、`经验文档/B草稿库/*` 对 `x86simd`、`disable-avx`、`__builtin_cpu_supports`、
`divsufsort` 相关关键词均 **0 命中**；机制表述与既有"三元组/config 老版不识 OHOS"条目族
（E122/E072/E007 一类）**不同层**——那族是 configure 的三元组校验，本条是编译期内建函数缺失，
签名与根因都不重合。判 `create`，非 `hit`。

## 可跨库复用的价值

一条判据加一步操作即可复用：交叉到非 x86 时，先看清失败落在**内建函数**还是**编译选项**这一层，
再决定"关掉上游默认 enable 的架构开关"还是"打补丁加预处理守卫"；前者优先，因为它零改上游、
不引入无效 diff，也不会把分发层连同测试一起删掉。
