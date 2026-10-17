/*
 * ecvt(3) compatibility shim for OpenHarmony / HarmonyOS PC — 声明部分。
 *
 * libvisam/isdecimal.c 直接调用 ecvt()，但 OHOS 的 musl libc 不提供该函数，
 * 也没有任何头文件声明它（Linux/glibc 是在 stdlib.h 里声明的）。缺少声明会
 * 触发 -Wimplicit-function-declaration 与 -Wint-to-pointer-cast。
 * conanfile.py 通过 configure 的 CPPFLAGS="-include <本文件>" 在编译各源文件
 * 之前注入此声明；定义在 ohos-ecvt-shim.c。
 */
#ifndef OHOS_ECVT_SHIM_H
#define OHOS_ECVT_SHIM_H

char *ecvt (double value, int ndigits, int *decpt, int *sign);

#endif /* OHOS_ECVT_SHIM_H */
