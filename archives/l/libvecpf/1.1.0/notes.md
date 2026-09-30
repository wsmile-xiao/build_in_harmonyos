# libvecpf 1.1.0 适配笔记（HarmonyOS PC / aarch64 / musl）

## 结论

**适配成功。** 上游自带测试套件在本平台真实构建并执行：`All tests passed (1340 tests)`；
消费者测试（仅调用已安装的公开头文件与库）**14/14** 通过，含内存泄漏与并发安全两项回归。

- 构建方式：上游 autotools（`configure` + `make check`），未替换构建系统
- 产物（`shared` 选项两种取值都支持，且都实测通过）：
  - `shared=True`（默认）：`libvecpf.so.1.0.1` + `libvecpf.so.1` / `libvecpf.so` 符号链接
  - `shared=False`：`libvecpf.a`
  - 公共头：`vecpf.h`、`vecpf-ohos-compat.h`（后者为内部头，被包含时会直接 `#error` 拒绝）
- 补丁：
  - `patches/0001-ohos-musl-printf-hook-compat-layer.patch`（改动 7 个文件，新增 1 个文件）
  - `patches/0002-ohos-build-tmpdir-umask.patch`（改动 4 个文件：`configure` / `config.guess` /
    `Makefile.in` / `ltmain.sh`；仅放宽构建期自建临时目录的 umask，产物不受影响）
  - 两者在 `configure` 与 `Makefile.in` 上重叠，**去重后全树共 10 个文件被改动、1 个文件为新增**；
    必须按上述顺序串行应用（0002 的 `orig` 侧取「pristine + 0001」生成）

> 默认取 `shared=True`：本库的存在意义就是扩展 printf，而**上游的测试程序只在共享配置下存在**
> （`Makefile.am` 用 `TEST_SHARED` 条件门控它）。静态模式同样能构建、能跑测试，只是上游测试会走
> `test_vecpf_static`（libtool `-all-static`）那条路 —— 本平台 sysroot 带 `libc.a`，实测可行。
> 本库与系统库不同名，不受 R26（要求与系统同名库静态）约束。

---

## 一、这个库为什么「看起来」不能适配

libvecpf 的实现方式是**扩展宿主 libc 的 printf**：它通过 glibc 私有的 `<printf.h>` 注册

- 新的转换字符（`d`、`x`、`o`、`u`、`X`、`c`、`f`、`e`、`g`、`a` …）
- 新的长度修饰符（`vl`/`lv`、`vh`/`hv`、`v`、`vv`、`vz`/`zv`）
- 一个自定义实参类型（16 字节向量）

OpenHarmony 用 musl，而 musl 明确不实现这套注册机制：全 sysroot 找不到 `printf.h`；
SDK sysroot 里的 `libc.so` / `libc.a`（**链接桩**）也不导出
`register_printf_type` / `_modifier` / `_specifier`。
（注：该桩把符号表指向同一地址，所以它只能证明**链接层面**拿不到这些符号；
运行时 libc 无法直接读取。不过按 musl 的设计，其 printf 引擎本就不提供这套机制，
再加上头文件缺失，结论一致。）
看上去「唯一的挂载点不存在」，于是很容易直接判为无法适配。

## 二、但真正缺的只是「挂载点」，不是「功能」

关键一步是**量化缺失面**，而不是停留在「头文件/符号不存在」。分两步看，两步都要先 `configure`：

```bash
# 未打补丁的原始树：根本编译不到「看符号」这一步
./configure --build=aarch64-unknown-linux-gnu CC=<ohos-clang> --enable-shared --disable-static
#   → exit 1: configure: error: Building Libvecpf requires a GLIBC printf.h header ...
$SDK/llvm/bin/aarch64-unknown-linux-ohos-clang -c vecpf.c -I. -o vecpf.o
#   → fatal error: 'printf.h' file not found

# 打过补丁的树（config.h 由上面的 configure 生成，缺它会报找不到 config.h）
# 两个补丁按 conandata.yml 的顺序串行应用
patch -p1 < patches/0001-ohos-musl-printf-hook-compat-layer.patch
patch -p1 < patches/0002-ohos-build-tmpdir-umask.patch
$SDK/llvm/bin/aarch64-unknown-linux-ohos-clang -c vecpf.c -I. -o vecpf.o   # 0 error 0 warning
$SDK/llvm/bin/llvm-nm -u vecpf.o
```

打过补丁后的未定义符号表（实测）**全部由 musl 提供**，其中已**没有** `register_printf_*`
—— 它们被兼容层实现为 file-local `static`，在库内部就解决了：

```
abort  fputc  fputs  free  malloc  memcpy  memset  realloc  snprintf  stdout
strchr strcmp strdup strlen strncpy vfprintf vsnprintf
（另有一组 pthread_* / __emutls_*，来自兼容层用于线程局部存储，见踩坑 5）
```

**那么「缺的只是 3 个符号」这个判断是怎么来的？** 在兼容层落地之前，把 `vecpf.c` 拿一个
**只声明、不实现**这三个注册函数的 stub 头文件来编译（相当于兼容层退化成一个空壳），
`llvm-nm -u` 就只剩这 3 个符号 —— 这是判断「缺的是挂载点还是能力」的依据。
现在这个 stub 的角色由 `vecpf-ohos-compat.h` 接手，所以上面那张表里看不到它们了。

再看这三个符号原本怎么被用：

```bash
grep -c 'register_printf_type ('      vecpf.c     # 1
grep -c 'register_printf_modifier ('  vecpf.c     # 1（跑在 6～8 个修饰符的循环里）
grep -c 'register_printf_specifier (' vecpf.c     # 15
```

真正的调用点是 **17 处**（`grep -c 'register_printf_'` 会命中 **22 行**，多出来的 5 行是注释、
函数定义与 `__register_printf_vec();` 这行调用）。这 17 处**全部发生在 `__register_printf_vec()`
一个函数里**，而它只被构造函数 `__libvecpf_init()` 调一次 —— 也就是说这三个符号只在**初始化期**
起作用，不含任何格式化算法。真正的格式化引擎（`vec_printf_d()`、`vec_printf_f()`、
`gen_fmt_str()`，共约 200 行）只通过 `fprintf()` / `fputs()` 输出，完全自洽。

**结论：缺的是 3 个纯注册函数，不是一套能力。** 因此在应用侧重建筑这个挂载点是可行的，
不需要去改 libc。

## 三、四项具体适配

### 1. AltiVec：其实根本没用到

上游 `vecpf.c` 无条件 `#include <altivec.h>`，并用了 PowerPC 专属的 `vector` 关键字。
但实际检查后发现：

```bash
grep -n 'vec_' vecpf.c     # vec_va / vec_ais / vec_printf_d / vec_printf_f —— 全是它自己的函数名
```

**libvecpf 不使用任何 AltiVec 内建函数**，所以删掉 `<altivec.h>` 在语义上没有任何损失。
但**这个删除是必需的，不是「删不删都行」**：clang 自带的 `altivec.h` 在非 PowerPC 目标上
一被包含就 `#error "AltiVec support not enabled"`。
`vector unsigned int` 只用来声明一个 16 字节类型，用 `__attribute__((vector_size(16)))`
可完全等价替换（布局相同），且向量元素始终经由 union 的标量成员访问。

> 教训：**「出现 altivec.h」不等于「依赖 AltiVec」**，必须 grep 内建函数才能定性。

### 2. printf hook：自建兼容层（本次适配的主体）

新增 `vecpf-ohos-compat.h`，向 `vecpf.c` 提供三样东西：

1. glibc `<printf.h>` 中 libvecpf 实际用到的那部分类型定义
   （`struct printf_info`、`printf_function`、`printf_arginfo_size_function`、`printf_type_function`）
2. 三个注册函数的等价实现（修饰符 bit 分配、类型句柄、转换字符登记表）
3. 一个**前端分发器**：单遍扫描格式串，命中向量规格就交给库的引擎，其余交宿主 printf

`vecpf.c` 里改成按 libc 特征宏分流（R8：用 `__GLIBC__`，不用 `__OHOS__`）：

```c
#if defined(__GLIBC__)
#include <printf.h>
#else
#include "vecpf-ohos-compat.h"
#endif
```

`vec_printf_d()` / `vec_printf_f()` 内部的 `fprintf` / `fputs` 由兼容层末尾的宏重定向到
内存输出汇：

```c
#define fprintf vecpf_compat_fprintf
#define fputs   vecpf_compat_fputs
```

**踩坑 1 —— 回调的二级间接**：glibc 的 hook 约定里 `args[i]` 不是「数据指针」而是
「指向数据指针的指针」——引擎内部写的是 `*((void***)args)[0]`。兼容层必须让 `args[0]`
指向一个 `void*` 槽位（该槽位再指向 16 字节数据），否则**段错误**。

**踩坑 2 —— 为什么不用 open_memstream**：本机 libc 实测（可复现），
`open_memstream()` 与 `fmemopen()` 写进去的数据**只有在显式 `fflush()` 之后才是可见的**；
走「写完直接 `fclose()`」这条路径时捕获长度始终为 **0**，并且反复这样用会破坏内存
（循环 5 次后在退出时 SIGSEGV）；`tmpfile()` 直接返回 **NULL**。
为不依赖这些收尾路径的边界行为，这里统一走上面的宏重定向 + 自建缓冲。
（该组 libc 行为差异对所有「需要把 FILE* 输出接进内存」的移植都适用。）

**踩坑 3 —— 前端必须支持长度修饰符**：上游测试用 `%lu` / `%hhx` / `%hhX` 等
逐元素构造期望值，前端若只支持裸转换字符会全盘失败。

**踩坑 4 —— 内部行缓冲会截断超宽字段**：前端与引擎之间最初用 `char tmp[1024]` 承接单次
转换，于是 `%1100vlu` 这类大字段宽度会被**静默截断**（只输出 1023 字符）。已改为：
先用 1024 栈缓冲试，若返回值说明放不下，则按精确长度 `malloc` 重做一次。
`test_package` 里有一条 `%1100vlu` 的回归用例盯着这个行为。

**踩坑 5 —— 输出汇必须是线程局部的，且必须释放**：这是兼容层引入的、上游没有的两个问题
（上游在 glibc 下是引擎直接写调用方的 `FILE*`，库内**没有共享可变状态**）：

- **线程安全**：第一版把输出汇写成进程级 `static` 全局且无锁。并发调用 `vecpf_sprintf`
  会在同一个指针上竞争 `realloc`，直接破坏堆 —— 实测 4 线程 × 20000 次调用必崩
  （`Trace/breakpoint trap`），而同样线程结构改调宿主 `snprintf` 则稳定通过。
  已改为 `_Thread_local`（C11；不支持时回退 `__thread`），每线程一份汇。
- **内存泄漏**：第一版在 `vecpf_vsprintf()` 收尾时只把指针置 `NULL` 而**没有 `free()`**，
  每次调用泄漏约 132 字节 —— 上游测试只调约 1300 次、消费者测试只调十几次，**测试完全看不见**。
  现在统一由 `vecpf_compat_reset()` 负责释放，`asprintf` 路径用 `vecpf_compat_take()`
  把缓冲交给调用方（不释放、也不二次释放）。

两条都加了回归用例：`no leak (200k calls)` 用 `/proc/self/statm` 比对 20 万次调用的 RSS 增长，
`4-thread concurrency` 用 4 线程并发跑同样的格式化并逐次 `strcmp` 比对结果。

**踩坑 6 —— 公开头文件必须带 `extern "C"`**：本库是 C 库，而新增的 6 个入口声明最初
没有链接说明符。用 C 编译没问题（消费者测试是 C），但**任何 C++ 消费者包含 `vecpf.h`
都会链接失败**：

```
ld.lld: error: undefined symbol: vecpf_sprintf(char*, char const*, ...)
>>> did you mean: extern "C" vecpf_sprintf
```

上游的 `vecpf.h` 原本只有类型、没有任何函数声明，所以不存在这个问题 —— 是我引入的。
已给声明加上 `#ifdef __cplusplus extern "C" { ... }` 保护，并新增
`test_package/test_vecpf_cxx.cpp` 专门守护它（C++ 用例 2/2）。

**公开契约的变化（必须如实说明）**：
glibc 上 libvecpf 是**透明**的 —— 链接后 `printf("%vld", v)` 直接可用。
musl 没有 hook 机制，这个「透明」原理上无法保留，因此改为**显式入口**：

```c
vecpf_printf("%vld", v);
vecpf_fprintf(fp, "%vld", v);
vecpf_sprintf(buf, "%vld", v);
vecpf_asprintf(&s, ...)  /* 实为 char *vecpf_asprintf(const char *fmt, ...) */
```

这是本次适配**唯一的行为性改动**；格式串语义、输出文本、返回值约定均与上游一致，
字段宽度也不受内部缓冲限制（`%1100vlu` 这类超宽字段由 `test_package` 回归守护）。

### 3. 构建系统

| 问题 | 原因 | 解决 |
|---|---|---|
| `configure` 直接中止 | 上游在缺 glibc `printf.h` 时 `AC_MSG_ERROR` + `exit 1` | 改成 `AC_MSG_WARN`（`configure.ac` 与生成物 `configure` 同步改，因无 automake 可重生成） |
| `unable to guess system type` | 自带 `config.guess`(2014) 不认识 HarmonyOS（`uname -s` = `HarmonyOS`） | 显式 `--build=aarch64-unknown-linux-gnu`；不传 `--host`，保持本机构建模式 |
| `ChangeLog.md` 规则失败 | 该文件由 `generate-changelog.sh` 从 git 历史生成，发布 tarball 里没有，却列在 `dist_doc_DATA` | 从 `dist_doc_DATA` 移除 |
| `-maltivec` 出现在 CFLAGS | 上游按 PowerPC 设计；clang 在 aarch64 上**接受但静默忽略**该选项 | 用 `case $host_cpu` 把它限定到 PowerPC |
| `config.status: ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery`（部分环境下还会表现为 `could not create Makefile`） | autoconf 生成的 `config.status` 写死 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录。鸿蒙共享卷（hmfs）上新建目录会**继承父目录 setgid 位**，叠加 `umask 077` 后得到 `drwx--S---`（**2700**，group 位被清空）；而该卷上进程**不以记录到的 owner 身份写入，而是靠 group 授权**，group 位为空即 `EACCES` | `patches/0002-ohos-build-tmpdir-umask.patch`：把构建系统自建临时目录的 umask 由 `077`/`0077` 放宽为 `002`/`0002`，覆盖 `configure`、`config.guess`、`Makefile.in`（distcheck DESTDIR）、`ltmain.sh`（`func_mktempdir`） |

> 上述 `config.status` 权限问题**只在真实登录终端下暴露**：沙箱与登录终端的
> owner/group 映射不同，同一份 2700 目录在沙箱里恰好可写，属于**假阴性**。
> 判据是同一构建内 `b/` 为 `drwxrws--x`（**2771**，group 有 `rwx`）→ 写入全部成功，
> 而 `config.status` 自建临时目录为 `2700` → 写入被拒；差别只在一个 mode 位。

> `-maltivec` 还有一处副作用值得记录：它产生的 `-Wunused-command-line-argument` 警告会让
> 后续 `-Werror` 的探测编译失败，从而**意外地**让 `-Werror` 不被追加。修掉 `-maltivec` 后
> `-Werror` 才真正生效 —— 好在兼容层本身在 `-Wall -Werror` 下零警告。

### 4. 测试套件

`test_vecpf.c` 只做了可移植性处理，**格式串、期望值、断言一律未改**：

```c
#define vector __attribute__ ((vector_size (16)))   /* PowerPC 关键字 → 可移植向量扩展 */

#if defined(__GLIBC__)
#define VECPF_TEST_FMT sprintf                      /* glibc：透明 hook 自动生效 */
#else
#define VECPF_TEST_FMT vecpf_sprintf                /* musl：走 libvecpf 显式入口 */
#endif
```

改动只落在两处：

1. 删掉 `#include <altivec.h>`、加 `#define vector ...`（必需，见上）；
2. 把**渲染被测向量**的 **15 处生效调用点** `sprintf (actual_output, …)` 换成
   `VECPF_TEST_FMT (actual_output, …)`。

   （文件里 `actual_output` 一共出现 16 次，另 1 次位于被上游注释掉的
   "Locale printing tests" 块内，属死代码，刻意不动 —— 免得补丁去改注释里的代码。）

**关键点：`gen_cmp_str()` 里构造期望值的 18 处 `sprintf (out_buffer + …)` 一个字没动**，
它们仍然调用宿主 libc 的 `sprintf`。也就是说「期望值」由**独立于被测实现**的宿主 printf 生成，
只有「实际值」经过 libvecpf —— 这仍然是一次有意义的交叉验证。
如果把两侧一起改道，测试就会退化成拿实现验证实现，因此这里刻意只改一侧。

---

## 四、`HAVE_INT128_T` 与 `__VSX__` 两组为什么不在统计内

上游 `configure.ac` 对这两组的探测本身就与 PowerPC 绑定：

```m4
AC_TRY_COMPILE([ ], [ vector __int128_t u = {0}; return 0; ])   # vector 关键字 + glibc 私有 __int128_t
```

在 aarch64/musl 上必然判定为 `no`，于是 `HAVE_INT128_T` 不定义；
`__VSX__` 也不会由 clang 定义。**这正是上游对非 PowerPC 平台的正确行为**，不是适配缺陷。

> 附带发现（与本次适配无关，供上游参考）：若强制打开 `HAVE_INT128_T`，会出现恰好 12 项失败，
> 全部位于 int128 组。根因是上游 `case VDT_int128` 把 **16 字节向量** `vp_u.i` 直接传给了
> 标量转换 `%lu`，变参 ABI 不匹配，读出的是栈上的垃圾值。

---

## 五、验证记录（本机实测）

环境：HarmonyOS PC / aarch64 / OHOS SDK 26.0.0.18 / clang 15.0.4 / conan 2.29.1

```bash
# 1) 上游构建与测试（out-of-tree，脚本化复现）
./configure --build=aarch64-unknown-linux-gnu CC=<ohos-clang> \
            CFLAGS="-O2 -fPIC" --enable-shared --disable-static
make -j1 && make -j1 check
# → Testsuite summary: TOTAL 1 / PASS 1 / FAIL 0 / ERROR 0
# → 测试程序自身输出：All tests passed (1340 tests)

# 2) 端到端打包与消费者测试
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
# → test_package: 14/14 checks passed

# 2b) 鸿蒙平台身份专项验证（test_ohos/run_ohos_test.py，5 项）
python3 test_ohos/run_ohos_test.py "$(conan cache path libvecpf/1.1.0:<pkgid>)"
# → T1 ok: ELF64 AArch64 / T2 ok: musl (no glibc/ld-linux)
# → T3 ok: .codesign section present / T4 ok: no host path leak
# → T5 ok: real consumer run on OHOS toolchain → TEST_OHOS_ALL_PASS
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → configure: exit 0，config.status 生成 Makefile / man/Makefile / config.h
# → make check: Testsuite summary: TOTAL 1 / PASS 1 / FAIL 0
# → test_package: 14/14 checks passed（C++ 侧 0 failure(s)）
```

> 上面第 3 步是**针对真实登录终端才暴露的 `config.status` 权限问题**补做的回归。
> 该问题在 WorkBuddy 沙箱里无法复现（owner/group 映射不同，沙箱对 2700 目录恰好可写），
> 因此不能把沙箱结果当作通过 —— 详见 §3 表格最后一行与其后的说明。

> **网络**：适配早期曾用 Debian pool 的 `deb.debian.org` 作为下载源，实测在本网络
> **可达但不稳定** —— 3 次里 2 次 HTTP 200（386781 字节），1 次传输中途超时；
> `ftp.debian.org` 则完全不可达。
> 为省去重试，本地验证时用了一份独立 `CONAN_HOME`，其 `global.conf` 指向稳定镜像。
>
> **最终 `conandata.yml` 的源已改为上游官方 GitHub tag**（R39 要求源地址必须指向官方正式源）：
> `https://github.com/Libvecpf/libvecpf/archive/refs/tags/v1.1.0.tar.gz`。
> 该 tag 归档与 Debian pool 的 `.orig.tar.gz` **逐字节相同**（均 386781 字节，
> sha256 同为 `33ed7c13af882ea38ab7fa32e72f1e17e611378e74aadfad9c1301ed9a0019e7`，
> 逐成员比对 64 项 size/mode/内容 sha256 差异为 0），故 **sha256 保持不变**、
> 构建产物与测试结论均不受影响。CI 会自动为 GitHub URL 追加镜像 fallback，
> 因此配方里只写官方 URL，不手写镜像前缀。
>
> ⚠️ **本机复现 `conan create` 前，先删掉仓库里的 `test_package/build/`**。
> WorkBuddy 沙箱有一个「一次删除超过 50 个文件需确认」的守卫，conan 每次 create 都会先删掉
> 上一次留下的这个目录（约 59 个条目），于是撞上守卫并报
> `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]` → `ERROR: Exiting with code: 1`。
> 此时包其实已经 build 成功（日志里能看到 `Testsuite summary`），只是没走到
> `Testing the package`。删掉该目录后重跑即 `exit 0`。**CI worker 上没有这套 shim**，
> 且该目录本来就在 `.gitignore` 内。

`-Wall -Werror` 下编译零警告；`libvecpf.so` 的**公开 API 面只有 6 个符号**：

```
vecpf_printf  vecpf_fprintf  vecpf_sprintf  vecpf_vsprintf  vecpf_asprintf  vecpf_vasprintf
```

`llvm-nm -D --defined-only` 会多出 3 行工具链产物：`_init`、`_fini` 与弱符号
`__emutls_get_address`（兼容层用了 `_Thread_local`，见踩坑 5）。
三个 `register_printf_*` 兼容实现刻意保持 file-local，**不出现在导出表里**，不污染全局命名空间。

### 仓库自检（`ci/conan/build_and_test.sh`）

```bash
CI_REPO_ROOT=<repo> CI_PACKAGES=archives/l/libvecpf/1.1.0 CI_BRANCH=feat/libvecpf-1.1.0 \
  zsh ci/conan/build_and_test.sh
```

结果：

```
G0_RESULT=pass        # 知识图谱完整性（540 条）
L0_RESULT=pass        # 质量门禁（目录结构/分支名/test_package 结构/MANIFEST/settings/…）
KC_RESULT=pass        # 知识检查
JC_RESULT=pass        # 无垃圾文件
L1_RESULT=pass        # 上游 make check + test_package 真实执行
L1e: 破坏性负向测试确认 test 真的依赖 libvecpf
L2_RESULT=skip        # 无 bin/（库包）
L4_RESULT=warn        # 见下
L5_RESULT=pass        # lib/ 有产物

━━━ Build Summary ━━━
  Total: 1  Success: 1  Failed: 0
  Pass rate: 100.0% (1/1)
```

> ⚠️ 这份 100% 是在**清空了 `CONAN_HOME` 下遗留构建目录**后取得的。若不清，`conan create`
> 会撞上沙箱的 `safe-delete` 守卫而 `exit 1`，CI 随之报 `L1_RESULT=fail`、
> `Pass rate 0.0%`（L2/L4/L5 全部 skip）。这纯粹是本机沙箱行为，CI worker 上没有。
>
> 另外 `JC_RESULT=pass` 在本机是**空转**的：JC 走 incremental 模式，文件集来自
> `git diff origin/main...HEAD`，而未提交的新包不在其中。真实 PR（pr.diff 模式）下才会覆盖到本包。

**关于 `L4_RESULT=warn`（启发式误报，非实际风险）**：L4 的判据是对补丁目录做
`grep -rlE '(strcpy|sprintf|gets|strcat)\b'`。注意这个正则**没有前置词边界**，所以
`vecpf_sprintf`、`vecpf_fprintf` 这类名字同样会命中；本补丁里共 **38 行**命中
（含 15 行被替换掉的 `- sprintf (actual_output, …)` 与相邻的新增行）。

补丁中**没有任何一处真正调用** `strcpy` / `sprintf` / `gets` / `strcat`：
兼容层里所有格式化输出一律走 `snprintf(buf, sizeof buf, ...)` / `vsnprintf` / `vfprintf`，
目标缓冲区长度都由调用方给出。该检查为启发式 warn，不影响 CI 结论（脚本退出码 0）。

---

**适配结束**: 2026-09-27
**最终状态**: built
---

**编译结束**: 2026-09-28 12:17
**最终状态**: built
