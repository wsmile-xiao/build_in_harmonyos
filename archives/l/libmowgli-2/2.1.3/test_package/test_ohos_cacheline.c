#include <stdio.h>
#include <stdlib.h>
#include <mowgli.h>

/* mowgli_cacheline_bootstrap() is exported by the static library (patch 0002
 * platform path) but not declared in the public headers; declare it here for
 * this test entry so the OHOS fallback path is explicitly exercised. */
extern void mowgli_cacheline_bootstrap(void);

/*
 * HarmonyOS-specific test: validates the OHOS platform adaptation path of
 * mowgli cache-line probing (patches/0002-src-libmowgli-platform-cacheline.c.patch).
 *
 * On OHOS the libc does not provide the _SC_LEVEL1_DCACHE_LINESIZE sysconf
 * key, so mowgli_cacheline_bootstrap() falls back to cacheline_size = 64
 * instead of failing at runtime. This test invokes that platform bootstrap
 * explicitly and asserts a sane, non-zero cache line size is reported.
 */
int main(void)
{
	size_t cs;

	mowgli_cacheline_bootstrap();
	cs = mowgli_cacheline_size();

	if (cs == 0) {
		fprintf(stderr, "FAIL: mowgli_cacheline_size() returned 0 (OHOS fallback not applied?)\n");
		return 1;
	}

	if (cs % 64 != 0) {
		fprintf(stderr, "FAIL: unexpected cache line size %zu (expected multiple of 64 on aarch64)\n", cs);
		return 1;
	}

	printf("PASS: mowgli_cacheline_size() = %zu (OHOS fallback path)\n", cs);
	return 0;
}