/*
 * ecvt(3) compatibility shim for OpenHarmony / HarmonyOS PC.
 *
 * 背景：libvisam/isdecimal.c:137（deccvreal）调用 ecvt() 把 double 转成十进制
 * 数字串（double 取 16 位有效数字，float 取 8 位）。ecvt() 是 System V/glibc 的
 * 非标准扩展，OHOS 的 musl libc 不提供，于是 libvisam.so 带未定义符号，链接
 * vcheck/vrecover 时 lld 报：
 *     ld.lld: error: undefined reference due to --no-allow-shlib-undefined: ecvt
 * 本文件按 glibc 语义补上 ecvt()，由 conanfile.py 以 -fPIC 编译后经 configure 的
 * LIBS 交给 libtool，随 libvisam.so 一起导出；上游源码不做任何改动。
 *
 * 语义（与 glibc ecvt(3) 一致）：
 *   - 返回值指向静态缓冲：仅含 ndigits 个 ASCII 数字，无小数点、无正负号；
 *   - *decpt = 小数点在数字串中的位置（首位记 1，值 0.0 时为 1）；
 *   - *sign  = 非 0 表示 value 为负。
 * 数字串用 "%.*e" 生成，正确舍入，与 glibc ecvt 的舍入规则一致。
 */
#include <stdio.h>
#include <stdlib.h>

#include "ohos-ecvt-shim.h"

#define ECVT_SHIM_MAXDIGITS  64
#define ECVT_SHIM_BUFSIZE    (ECVT_SHIM_MAXDIGITS + 1)

static char ecvt_shim_buffer[ECVT_SHIM_BUFSIZE];

char *
ecvt (double value, int ndigits, int *decpt, int *sign)
{
	char  work[ECVT_SHIM_BUFSIZE + 32];
	char *p;
	char *q;
	int   exponent;
	int   negative;

	if (ndigits < 1) {
		ndigits = 1;
	}
	if (ndigits > ECVT_SHIM_MAXDIGITS) {
		ndigits = ECVT_SHIM_MAXDIGITS;
	}

	negative = (value < 0.0);
	if (negative) {
		value = -value;
	}

	/* "%.*e" 产出 1 位整数位 + (ndigits-1) 位小数位，恰好 ndigits 位有效数字，
	   且为正确舍入值。 */
	snprintf (work, sizeof (work), "%.*e", ndigits - 1, value);

	/* work 形如 "d.ddddd" + "e[+-]XX"；抽出数字位并取十进制指数。 */
	q = ecvt_shim_buffer;
	exponent = 0;
	for (p = work; *p != '\0'; p++) {
		if (*p >= '0' && *p <= '9') {
			if ((int) (q - ecvt_shim_buffer) < ndigits) {
				*q++ = *p;
			}
		} else if (*p == 'e' || *p == 'E') {
			exponent = (int) strtol (p + 1, NULL, 10);
			break;
		}
	}
	while ((int) (q - ecvt_shim_buffer) < ndigits) {
		*q++ = '0';
	}
	*q = '\0';

	*decpt = exponent + 1;
	if (sign != NULL) {
		*sign = negative;
	}

	return ecvt_shim_buffer;
}
