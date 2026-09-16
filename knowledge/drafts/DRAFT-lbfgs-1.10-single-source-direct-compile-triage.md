# lbfgs 1.10：上古 autotools 单源库无 dist tarball → 直编可行性三要素判定

## 场景

liblbfgs（chokkan/liblbfgs）只发 git tag，无 dist tarball；`configure.in`
是 `AC_PREREQ(2.59)`、`AC_INIT` 无参数的上古 autotools，`autogen.sh`
依赖 autoconf/automake/libtool，OHOS 沙箱不具备。ctemplate 路线（手工
合成 config.h + 重放 configure）对本库是纯负担——因为三个关键事实不同。

## 直编可行性三要素（全部满足才放弃 configure 重建）

1. **config.h 引用有 `HAVE_CONFIG_H` 守护**
   `lib/lbfgs.c:64-66`：
   ```c
   #ifdef  HAVE_CONFIG_H
   #include <config.h>
   #endif/*HAVE_CONFIG_H*/
   ```
   直编不定义该宏即跳过，**无需合成 config.h**。
   反例：ctemplate `statemachine.h:37` 无条件 `#include <config.h>`，
   必须合成（见 DRAFT-ctemplate-2.4-no-pregen-configure-manual-autotools）。
   判定命令：`grep -rn 'config.h' lib/ include/ | grep -v HAVE_CONFIG_H` 应为空。

2. **平台特性走编译期宏探测，而非 configure 探测结果**
   SSE 优化头：
   ```c
   #if defined(USE_SSE) && defined(__SSE2__) && LBFGS_FLOAT == 64
   #include "arithmetic_sse_double.h"
   #else
   #include "arithmetic_ansi.h"
   #endif
   ```
   aarch64 无 `__SSE__` → 自动落纯 ANSI 路径，**无需裁剪源码、无需
   configure 的 AC_CHECK_HEADERS(xmmintrin.h) 结果**。

3. **编译单元单一，无 codegen/BUILT_SOURCES**
   库本体只有 `lib/lbfgs.c`；无 `.h.in` 模板、无生成头。
   反例：ctemplate 需要 generate_fsm.py 生成 3 个 fsm 头。

## 落地

```python
self.run(f"{cc} -O2 -fPIC -Iinclude -c lib/lbfgs.c -o lbfgs.o")
self.run("ar rcs liblbfgs.a lbfgs.o")
# 层1 上游测试：sample/sample.c 是 automake 唯一接入的测试程序
self.run(f"{cc} -O2 -Iinclude sample/sample.c liblbfgs.a -lm -o sample")
self.run("./sample")
```

`package_info` 勿忘 `system_libs = ["m"]`——configure.in 的
`AC_CHECK_LIB(m, fabs)` 表明 lbfgs.c 用 fabs/sqrt，静态库不携带链接信息。

## 测试诚实性（rule4）

上游**无测试套件**（无 tests/、无 make check 目标）；`sample/sample.c`
是 automake 唯一接入的可执行验证程序（`noinst_PROGRAMS=sample`），
100 维 Rosenbrock 实跑收敛但只打印不断言；`sample.cpp` 为 EXTRA_DIST
未接入构建。上游测试数记 **1**，MANIFEST.yml 如实声明；test_package
另加 12 条消费者断言（Rosenbrock 收敛 + OWL-QN L1 软阈值解 + 鸿蒙特有的
入参错误路径返回负错误码，见 rule12）。
