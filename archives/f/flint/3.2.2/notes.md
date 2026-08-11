# flint 3.2.2 编译笔记（HarmonyOS PC · 标准 Conan autotools）

## 定位
- 产出 libflint.so 等 1 个库，供链接与 dlopen。

## 关键适配
- package() 显式重签 ELF：链接后若再改字节（strip/抹 RUNPATH 等）链接期自签即失效，dlopen 报 Permission denied
- 删除 lib/*.la：其中烤死 libdir 绝对路径，会把下游 libtool 引到 //lib/ 死路
- 修 configure 的 umask 077→022（HMDFS E011）

## 关键适配（续）
- `flint_cv_check_cpu_set_t=no`：FLINT 探测 cpu_set_t 用的是 `AC_COMPILE_IFELSE`，
  **只编译不链接**。OHOS 的 musl 在头里声明了 `pthread_getaffinity_np`、也有
  `cpu_set_t`/`CPU_ZERO`，所以探测通过；但 libc 里没有这个符号，直到消费方链接、
  `--no-allow-shlib-undefined` 生效时才报 undefined reference。预置 autoconf 的
  cache 变量即可关掉，无需打源码补丁。
- `--include-dirs include`：头装在 `include/flint/`，但 `.pc` 的 Cflags 是
  `-I${includedir}`（下游写 `<flint/fmpz.h>`）。若按自动探测填成 `include/flint`，
  本包三道检查全绿、下游一编就找不到头。
- `--make-jobs 20`：近 2000 个源文件，串行不可接受（设备 20 核）。

## 状态
built —— 真机 `conan create -pr ohos-native --update` rc=0（2026-08-10 20:03）。

### 真机证据
- test_package：**16 条真实断言全通过**，分布在四条依赖轴上
  （ulong_extras 压 FLINT 自身 / fmpz 大数压 GMP / fmpq+fmpz_poly 压代数层 /
  arb 压 MPFR）。样例：25! 的 26 位十进制展开、C(50,25)=126410606437752、
  2^61-1 素性、(x+1)^2 系数、pi=3.1415926535897932385。
- SONAME：`libflint.so.20`，软链三层齐全（`libflint.so` → `.so.20` → `.so.20.0.1`）。
  这正是 symengine 所需的那个 soname。
- 代码签名：`.codesign` 节存在（第 38 节）。
- 导出函数 16538 个。

### 已知特性（不是缺陷，但消费方需知情）
gmp/mpfr 在制品仓是**静态**包，被整体链进 `libflint.so`：
- 好处：`DT_NEEDED` 只剩 `libc.so`，部署自包含；
- 代价：libflint.so 重导出了 416 个 `__gmp*` 与 223 个 `mpfr_*` 符号。
  下游若同时动态链接另一份 libgmp，运行期会有两份 GMP 代码共存
  （符号插入使先加载者胜出）。默认分配器一致时通常无害，
  但调用过 `mp_set_memory_functions` 的场景需留意。
