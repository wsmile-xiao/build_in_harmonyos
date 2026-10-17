/*
 * HarmonyOS (aarch64) specific checks for the packaged libpfm4.
 *
 * 1. 64-bit ABI size constants
 *
 *    The OHOS sysroot is musl based and does not ship <bits/wordsize.h>, so
 *    __WORDSIZE is undefined there.  Upstream derived the public ABI size
 *    constants (PFM_*_ABI0) from __WORDSIZE, which silently produced the
 *    32-bit values on this platform while the library itself exported the
 *    64-bit structures.  A consumer that follows the documented pattern
 *
 *        pfm_pmu_info_t info;
 *        info.size = PFM_PMU_INFO_ABI0;
 *
 *    then passed a size the library rejected.  patches/0001 and 0002 make the
 *    selection independent of glibc; the checks below fail as soon as the
 *    constants and the real structures diverge again.
 *
 * 2. perf_event support
 *
 *    The kernel interface of HarmonyOS is the Linux one, but uname(1) reports
 *    "HarmonyOS" and upstream builds its perf_events PMU (pfmlib_perf_event.c,
 *    pfmlib_perf_event_pmu.c, pfmlib_perf_event_raw.c) only for SYS=Linux.
 *    Without SYS=Linux the generic perf_events PMU and its PERF_COUNT_*
 *    events do not exist at all, which is what this section checks.
 *
 * 3. perf_event_open()
 *
 *    Checked for information only: the syscall is expected to fail with
 *    EPERM/EACCES unless the process holds CAP_PERFMON/CAP_SYS_ADMIN, which
 *    is not a property of the package.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>

#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>

static int failures;

#define CHECK(cond, ...)                                                      \
	do {                                                                   \
		if (cond) {                                                    \
			printf("ok   - ");                                     \
		} else {                                                       \
			failures++;                                            \
			printf("FAIL - ");                                     \
		}                                                              \
		printf(__VA_ARGS__);                                           \
		printf("\n");                                                  \
	} while (0)

/* PERF_COUNT_HW_CPU_CYCLES of the Linux perf_event ABI */
#define OHOS_HW_CPU_CYCLES 0

int main(void)
{
	pfm_event_info_t einfo;
	struct perf_event_attr attr;
	pfm_perf_encode_arg_t arg;
	uint64_t *codes = NULL;
	char *fstr = NULL;
	int ret, idx, count = 0;

	/* ---- 1. exported ABI vs. the size constants ---------------------- */
	CHECK(PFM_PMU_INFO_ABI0 == sizeof(pfm_pmu_info_t),
	      "PFM_PMU_INFO_ABI0 (%d) == sizeof(pfm_pmu_info_t) (%zu)",
	      PFM_PMU_INFO_ABI0, sizeof(pfm_pmu_info_t));
	CHECK(PFM_EVENT_INFO_ABI0 == sizeof(pfm_event_info_t),
	      "PFM_EVENT_INFO_ABI0 (%d) == sizeof(pfm_event_info_t) (%zu)",
	      PFM_EVENT_INFO_ABI0, sizeof(pfm_event_info_t));
	CHECK(PFM_ATTR_INFO_ABI0 == sizeof(pfm_event_attr_info_t),
	      "PFM_ATTR_INFO_ABI0 (%d) == sizeof(pfm_event_attr_info_t) (%zu)",
	      PFM_ATTR_INFO_ABI0, sizeof(pfm_event_attr_info_t));
	CHECK(PFM_RAW_ENCODE_ABI0 == sizeof(pfm_pmu_encode_arg_t),
	      "PFM_RAW_ENCODE_ABI0 (%d) == sizeof(pfm_pmu_encode_arg_t) (%zu)",
	      PFM_RAW_ENCODE_ABI0, sizeof(pfm_pmu_encode_arg_t));
	CHECK(PFM_PERF_ENCODE_ABI0 == sizeof(pfm_perf_encode_arg_t),
	      "PFM_PERF_ENCODE_ABI0 (%d) == sizeof(pfm_perf_encode_arg_t) (%zu)",
	      PFM_PERF_ENCODE_ABI0, sizeof(pfm_perf_encode_arg_t));

	ret = pfm_initialize();
	CHECK(ret == PFM_SUCCESS, "pfm_initialize() -> %s", pfm_strerror(ret));
	if (ret != PFM_SUCCESS)
		return 1;

	/* ---- 2. the perf_events PMU is part of this build ---------------- */
	idx = pfm_find_event("PERF_COUNT_HW_CPU_CYCLES");
	CHECK(idx != -1, "pfm_find_event(\"PERF_COUNT_HW_CPU_CYCLES\") -> %d", idx);
	if (idx != -1) {
		memset(&einfo, 0, sizeof(einfo));
		einfo.size = sizeof(einfo);
		ret = pfm_get_event_info(idx, PFM_OS_NONE, &einfo);
		CHECK(ret == PFM_SUCCESS && einfo.name[0],
		      "pfm_get_event_info() -> \"%s\" of PMU %s",
		      ret == PFM_SUCCESS ? einfo.name : "?", "perf");

		ret = pfm_get_event_encoding("PERF_COUNT_HW_CPU_CYCLES",
					     PFM_PLM0 | PFM_PLM3, &fstr, &idx,
					     &codes, &count);
		CHECK(ret == PFM_SUCCESS && count > 0,
		      "pfm_get_event_encoding(\"PERF_COUNT_HW_CPU_CYCLES\") -> "
		      "%s, %d code(s) [%s]",
		      pfm_strerror(ret), count, fstr ? fstr : "-");
		if (codes)
			free(codes);
		if (fstr)
			free(fstr);
	}

	/* ---- 3. perf_event_open() - information only --------------------- */
	memset(&attr, 0, sizeof(attr));
	attr.type = 0; /* PERF_TYPE_HARDWARE */
	attr.config = OHOS_HW_CPU_CYCLES;
	attr.size = sizeof(attr);
	attr.disabled = 1;
#ifdef __NR_perf_event_open
	errno = 0;
	ret = (int)syscall(__NR_perf_event_open, &attr, 0, -1, -1, 0);
	if (ret < 0)
		printf("note - perf_event_open(type=%u config=%llu): %s "
		       "(expected without CAP_PERFMON)\n",
		       attr.type, (unsigned long long)attr.config, strerror(errno));
	else {
		printf("note - perf_event_open(type=%u config=%llu): fd %d\n",
		       attr.type, (unsigned long long)attr.config, ret);
		close(ret);
	}
#else
	printf("note - __NR_perf_event_open is not available on this platform\n");
#endif

	pfm_terminate();
	printf("HarmonyOS specific test: %s\n", failures ? "FAILED" : "passed");
	return failures ? 1 : 0;
}
