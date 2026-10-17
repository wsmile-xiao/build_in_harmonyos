/*
 * compat_reallocarray.c —— reallocarray(3) 的**派生实现**（来源与许可见下）。
 *
 * ── 实现来源（1-d 披露）─────────────────────────────────────────────────────
 * 本文件不是从零手写。实测对账：函数体 10 行里 9 行与 OpenBSD
 * `src/lib/libc/stdlib/reallocarray.c`（`$OpenBSD: reallocarray.c,v 1.3
 * 2015-09-13 08:31:47 guenther Exp $`，Copyright (c) 2008 Otto Moerbeek <otto@drijf.net>，**ISC 许可**）逐字符相同；宏名 `MUL_NO_OVERFLOW` 一致，阈值式
 * `sizeof(size_t) * 8 / 2` 与上游的 `sizeof(size_t) * 4` 数值相同；判定式
 * `(nmemb >= MUL_NO_OVERFLOW || size >= MUL_NO_OVERFLOW) && nmemb > 0 &&
 * SIZE_MAX / nmemb < size` 与上游逐字符相同。与上游的**唯一有意代码偏差**：溢出时
 * errno 由上游的 `ENOMEM` 改为 `ERANGE`（下节实测）。上游另有的
 * `DEF_WEAK(reallocarray);` 未沿用（OHOS musl 不定义 DEF_WEAK，见 notes.md 硬点 b-1）。
 * ISC 允许复制、修改与再分发，条件之一是保留版权声明，故此处按**派生码**署名上游来源
 * 与许可，不作"独立实现"表述。对账读数：
 * `~/tmp/uc2/z75z-rs-fix/E/E3-openbsd-provenance.txt`；本轮（整改轮 2）在同一设备原件上重做的逐行对账读数见 notes.md §7.9。
 *
 * ── 上游原件逐字许可声明（独立成段；从原件逐字符复制，一字未改）──────────────────
 *   来源：OpenBSD src/lib/libc/stdlib/reallocarray.c v1.3（sha256 前缀 813952c9），由主窗从设备上的
 *   原件直接抽取后原样嵌入本注释，非人工转述：
 * Copyright (c) 2008 Otto Moerbeek <otto@drijf.net>
 *
 * Permission to use, copy, modify, and distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 * ── 为什么需要它（OHOS 特有的"运行期有、链接期无"）：
 *   * rs.c:345 调用 reallocarray(elem, newsize, sizeof(*p))；
 *   * OHOS SDK 的 **链接桩** sysroot/usr/lib/aarch64-linux-ohos/libc.so
 *     不导出该符号（实测：只引用它的目标文件链接时
 *     `ld.lld: error: undefined symbol: reallocarray`），sysroot 头里也
 *     没有任何声明；
 *   * 但**运行期** libc（/system/lib/ld-musl-aarch64.so.1）确实导出它
 *     （实测 nm -D 得到 `T reallocarray`）。
 *   ⇒ 缺的只是链接期的定义，不是平台能力。
 *
 * 为什么不改用现成的静态库片段补齐：实测把 `-Wl,-Bstatic -lc -Wl,-Bdynamic`
 * 塞进链接行确实能过链接，但 musl 静态片段与动态 libc 混链会让产物一跑就
 * SIGSEGV（实测 rs 冒烟与 check.t 13 条全部 rc=139 / signal 11），故弃用。
 *
 * ── 溢出行为（B 机本轮实测，不再引手册页推断）──────────────────────────────
 * 同一进程内对两个实现各跑 3 组会溢出的 `nmemb*size`（2^40x2^40、SIZE_MAXx2、
 * 2^32x2^32）与 1 组正常分配（16x8）：
 *   本实现（配方 TU）  溢出 -> 返回 NULL，errno=34 ERANGE（Result not representable）
 *   OHOS musl 运行期   溢出 -> 返回 NULL，errno=12 ENOMEM（Out of memory）
 *   正常分配           两者均返回非 NULL，errno 不变
 * ⇒ 两个实现**只在"溢出返回 NULL"上一致，errno 取值并不一致**；原先此处写的
 *   "与运行期 musl 版本一致"不成立，已删除。musl 侧另有静态佐证：SDK 的 `libc.a`
 *   里 `reallocarray.o` 反汇编为 `bl ___errno_location` + `mov w9, #0xc` +
 *   `str w9, [x8]` + `mov x0, xzr`（0xc=12=ENOMEM；本平台常量实测 ENOMEM=12、
 *   ERANGE=34）。
 * ⇒ **本实现不承诺 errno 取值**：调用点 `rs.c:345` 只用 `p == NULL` 决定控制流，
 *   本文件只是额外链接 TU，上游 rs 源码保持逐字节不动。但需如实记：紧随其后的
 *   `err(1, "no memory")` 会把 `strerror(errno)` 拼进退出文案
 *   （实测两种 errno 分别得到 `no memory: Out of memory` 与
 *   `no memory: Result not representable`），差异只在文案，不影响成败判定与退出码。
 *   把下面的 `ERANGE` 改成 `ENOMEM` 即可与 musl 完全同构；那是行为变更，超出本轮
 *   措辞整改范围，留主理定夺。
 */

#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

/* size_t 半宽阈值：任一因子超过它就有可能让乘积溢出 */
#define MUL_NO_OVERFLOW	((size_t)1 << (sizeof(size_t) * 8 / 2))

void *
reallocarray(void *optr, size_t nmemb, size_t size)
{
	if ((nmemb >= MUL_NO_OVERFLOW || size >= MUL_NO_OVERFLOW) &&
	    nmemb > 0 && SIZE_MAX / nmemb < size) {
		errno = ERANGE;
		return NULL;
	}
	return realloc(optr, size * nmemb);
}
