/* SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only */
/* test_package/test_ohos.c — lcrq/0.3.1 鸿蒙特有测试 (rule12)
 *
 * 验证 lcrq Conan 包产物在 HarmonyOS PC (aarch64) 真实运行时上可用：
 *   [R1] OHOS musl 运行时：/lib/ld-musl-aarch64.so.1 存在（HarmonyOS PC
 *        的动态加载器，是 OHOS 运行时区别于常规 Linux 发行版的标志）
 *   [R2] OHOS PC 平台：uname().machine = "aarch64" 且 LP64
 *        （sizeof(void*) = 8，与 musl ELF64 加载器一致）
 *   [R3] 真实业务流：独立于 test.c 参数（F=4096, T=32）的完整
 *        rq_init -> rq_encode -> rq_symbol -> rq_decode 回环，证明包产物
 *        在 OHOS 运行时上真实可执行（musl 内存语义、4K 页、aarch64 指令）
 *
 * 任一断言失败 → 非零退出；无 skip、无静默通过。
 */

#define _GNU_SOURCE /* getauxval */

#include <lcrq.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/utsname.h>
#include <unistd.h>

/* 独立于 test.c 的参数组合（F=1024/T=16），覆盖另一组 K/KP 派生路径 */
#define F 4096UL /* transfer length (bytes) */
#define T 32     /* symbol size (bytes)  */

#define OHOS_MUSL_LOADER "/lib/ld-musl-aarch64.so.1"

static int fail(const char *what)
{
	fprintf(stderr, "[test_ohos] FAIL: %s\n", what);
	return 1;
}

int main(void)
{
	rq_t *rq;
	rq_oti_t oti = 0;
	rq_scheme_t scheme = 0;
	uint8_t *data = NULL, *enc = NULL, *dec = NULL;
	uint32_t *esi = NULL;
	uint16_t KP;
	uint32_t nesi;
	int rc = 1;

	/* [R1] OHOS musl 动态加载器存在 —— 本测试二进制自身就由它加载
	 * （PT_INTERP），无法通过上一步骤的 exec 时它必然已存在；此处
	 * 显式断言将其固化为可读的测试证据。 */
	if (access(OHOS_MUSL_LOADER, F_OK)) return fail("OHOS musl loader " OHOS_MUSL_LOADER " not accessible");

	/* [R2] OHOS PC 平台断言（本运行时 auxv 不提供 AT_PLATFORM——2026-09-20
	 * 实测 getauxval(AT_PLATFORM)=0，故不做 getauxval 断言，见报告） */
	{
		struct utsname un;
		if (uname(&un)) return fail("uname failed");
		if (strcmp(un.machine, "aarch64")) {
			fprintf(stderr, "[test_ohos] FAIL: uname.machine='%s'\n", un.machine);
			return 1;
		}
	}
	if (sizeof(void *) != 8) return fail("not LP64 (sizeof(void*) != 8)");

	/* [R3] 真实 RaptorQ 编码-解码回环（F=4096/T=32） */
	rq = rq_init(F, T);
	if (!rq) return fail("rq_init");

	if (rq_F(rq) != F || rq_T(rq) != T) {
		fprintf(stderr, "[test_ohos] FAIL: rq_F/rq_T mismatch (F=%lu, T=%u)\n",
				(unsigned long)F, T);
		goto err;
	}
	if (rq_oti(rq, &oti, &scheme)) {
		fprintf(stderr, "[test_ohos] FAIL: rq_oti\n");
		goto err;
	}
	if (rq_oti_F(oti) != F || rq_oti_T(oti) != T) {
		fprintf(stderr, "[test_ohos] FAIL: OTI roundtrip mismatch\n");
		goto err;
	}

	data = malloc(F);
	if (!data) goto err;
	/* 与 test.c 不同的填充模式（PRNG 风格，避免同构数据掩盖位级错误） */
	srand(0x0501);
	for (uint64_t i = 0; i < F; i++) data[i] = (uint8_t)(rand() >> 13);

	if (rq_encode(rq, data, F)) {
		fprintf(stderr, "[test_ohos] FAIL: rq_encode\n");
		goto err;
	}

	KP = rq_KP(rq);
	nesi = (uint32_t)KP + RQ_OVERHEAD;
	enc = calloc(nesi, T);
	esi = calloc(nesi, sizeof(uint32_t));
	if (!enc || !esi) goto err;
	{
		rq_pid_t pid = 0;
		for (uint32_t i = 0; i < nesi; i++) {
			uint8_t sym[T];
			rq_symbol(rq, &pid, sym, RQ_RAND);
			memcpy(enc + (size_t)i * T, sym, T);
			esi[i] = rq_pid2esi(pid);
		}
	}

	dec = calloc(KP, T);
	if (!dec) goto err;
	if (rq_decode(rq, dec, enc, esi, nesi)) {
		fprintf(stderr, "[test_ohos] FAIL: rq_decode\n");
		goto err;
	}
	if (memcmp(dec, data, F)) {
		fprintf(stderr, "[test_ohos] FAIL: decode roundtrip mismatch\n");
		goto err;
	}

	printf("[test_ohos] ALL OHOS-SPECIFIC CHECKS PASSED "
			"(musl loader, uname.machine=aarch64, LP64, "
			"RaptorQ roundtrip F=%lu T=%u KP=%u)\n",
			(unsigned long)F, T, KP);
	rc = 0;
err:
	free(dec);
	free(esi);
	free(enc);
	free(data);
	rq_free(rq);
	return rc;
}
