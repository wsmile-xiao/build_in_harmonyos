/* compat_fixed.c — Allegro 4 fixed-point math compatibility shim for alex4.
 *
 * alex4 (2003) 调用 fsin/fcos/fmul/fdiv（Allegro 4 定点数学函数）。
 * OHOS 版 allegro4.4 头文件被裁剪：alcompat.h 无 fsin→fixsin 等宏映射，
 * liballeg.so 也未导出这些符号 → 链接失败。本文件按 Allegro 4 语义
 * 补全兼容实现（固定点角度：2^24 单位 = 360°；fixed = 16.16 定点）。
 */
#include <stdint.h>
#include <math.h>

typedef int32_t fixed;

#define FIXED_ONE 65536.0
#define FULL_CIRCLE 16777216.0   /* 2^24 fixed units = 360 deg (Allegro 4) */

fixed fsin(fixed x)
{
    double deg = (double)x / FULL_CIRCLE * 360.0;
    return (fixed)(sin(deg * 3.14159265358979323846 / 180.0) * FIXED_ONE);
}

fixed fcos(fixed x)
{
    double deg = (double)x / FULL_CIRCLE * 360.0;
    return (fixed)(cos(deg * 3.14159265358979323846 / 180.0) * FIXED_ONE);
}

fixed fmul(fixed x, fixed y)
{
    return (fixed)(((int64_t)x * y) >> 16);
}

fixed fdiv(fixed x, fixed y)
{
    if (y == 0)
        return (x < 0) ? -0x7FFFFFFF : 0x7FFFFFFF;
    return (fixed)(((int64_t)x << 16) / y);
}
