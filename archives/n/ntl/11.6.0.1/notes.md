# ntl 11.6.0.1 编译笔记（HarmonyOS PC · 与 11.6.0 只差一处配置）

## 为什么另起 11.6.0.1

与 `ntl/11.6.0` 的差异只有一处：**`NTL_GMP_LIP=off` → `on`**（并因此新增
`requires gmp/6.3.0.1` 与 `GMP_PREFIX`）。上游源码、版本、其余 configure 参数全同。

### 关掉 GMP 后端会让所有 Python 绑定编不过

NTL 的 `include/NTL/ZZ.h` 里有一段：

```cpp
#ifndef NTL_GMP_LIP
// only defined for the "classic" long integer package, for backward compatability.
inline long digit(const ZZ& a, long k)
   { return _ntl_gdigit(a.rep, k); }
#endif
```

`NTL_GMP_LIP=off` 时这个**向后兼容的遗留函数**会被定义，与 CPython 3.12
`longintrepr.h:43` 的 `typedef uint32_t digit` 撞名。Cython 生成的

```cpp
const digit* digits = __Pyx_PyLong_Digits(x);
```

于是报 `error: reference to 'digit' is ambiguous`——**passagemath-ntl 10.8.7 实撞 380 处**，
整条 wheel 链（flint / m4ri-m4rie / iml / linbox）连坐失败。

排查过程中排除过两条错误方向，一并记下省得后人重走：
- **换 NTL 版本**：11.6.0 已是上游最新 tag，也正是 SageMath 钉的版本，无更新版可换
- **换 Cython 版本**：`__Pyx_PyLong_Digits` 是新版写法，但降到 3.1.4（仍在 pyproject
  允许的 `>=3.1.0,<3.3.0` 内）后二义**仍是 380 处**，假设被证伪

真因是从 NTL 头文件的条件编译定死的。Sage / passagemath 生态一贯用 GMP 后端编 NTL
（更快，且没有这个遗留函数），所以上游从不撞这个错——**这不是鸿蒙平台问题，
是我们制品仓那个 NTL 包的配置与该生态不兼容**。

### 配套的两处

1. `GMP_PREFIX=<gmp package_folder>`：开了 `NTL_GMP_LIP` 不给路径，configure 直接报
   `Error: NTL_GMP_LIP set but GMP not available -- set DEF_PREFIX or GMP_PREFIX`
2. `VirtualRunEnv(scope="build")`：NTL 的 configure 会**编译并运行** `CheckGMP` 探测程序，
   gmp/6.3.0.1 是共享库，不给运行期库路径就报
   `Error loading shared library libgmp.so.10: (needed by ./CheckGMP)`——
   报错说「GMP 不可用」，实为加载器找不到 .so

## 真机验证（2026-08-14，HarmonyOS PC MateBook）

`conan create -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` 通过，test_package 执行。

**GMP 后端确已启用**（判据是 config.h 里该宏不在 `#if 0` 内）：

```
旧 11.6.0    config.h:100  #if 0      #define NTL_GMP_LIP
新 11.6.0.1  config.h:100  #if 1      #define NTL_GMP_LIP
```

**下游实证**：用本包重建 passagemath-ntl，`reference to 'digit' is ambiguous`
从 **380 处降到 0**，wheel 成功产出（16MB）；其后 flint / m4ri-m4rie / iml / linbox
四个 wheel 也全部建成。

> 注：`grep 'inline long digit' ZZ.h` **仍能看到那行**——它被 `#ifndef` 包着，
> 定义宏后在预处理阶段排除，不参与编译。判据要看 config.h 的宏是否生效，
> 或直接看下游是否还报二义，别 grep 头文件原文。
