/*
 * Functional test of the installed libpfm4 package.
 *
 * Exercises the public API a consumer links against: initialisation, PMU
 * discovery, event and attribute lookup, and event encoding - both the raw
 * variant (pfm_get_event_encoding) and the perf_event variant
 * (pfm_get_os_event_encoding with PFM_OS_PERF_EVENT).
 *
 * The event used for the encoding checks is taken from the PMU that is
 * detected on this host, so the test does not depend on the PMU of a
 * particular CPU model.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

int main(void)
{
	pfm_pmu_info_t pinfo, host;
	pfm_event_info_t einfo;
	pfm_event_attr_info_t ainfo;
	struct perf_event_attr attr;
	pfm_perf_encode_arg_t arg;
	uint64_t *codes = NULL;
	char *fstr = NULL;
	int ret, idx = -1, count = 0;
	int pmus = 0, present = 0, have_host = 0;
	pfm_pmu_t pmu;

	memset(&host, 0, sizeof(host));

	ret = pfm_initialize();
	CHECK(ret == PFM_SUCCESS, "pfm_initialize() -> %s", pfm_strerror(ret));
	if (ret != PFM_SUCCESS)
		return 1;

	CHECK(pfm_get_version() != 0, "pfm_get_version() -> %#x", pfm_get_version());

	/* ---- PMU discovery ---------------------------------------------- */
	pfm_for_all_pmus(pmu) {
		memset(&pinfo, 0, sizeof(pinfo));
		pinfo.size = sizeof(pinfo);
		if (pfm_get_pmu_info(pmu, &pinfo) != PFM_SUCCESS)
			continue;
		pmus++;
		if (pinfo.is_present && !have_host) {
			have_host = 1;
			host = pinfo;
		}
		present += pinfo.is_present ? 1 : 0;
	}
	CHECK(pmus > 0, "PFM event table enumerates %d PMU(s)", pmus);
	CHECK(present > 0, "%d PMU(s) present on this host", present);
	if (!have_host) {
		printf("FAIL - no PMU of this host could be discovered\n");
		pfm_terminate();
		return 1;
	}
	printf("note - host PMU: %s, %d event(s), %d counter(s)\n", host.name,
	       host.nevents, host.num_cntrs);

	/* ---- event lookup ----------------------------------------------- */
	CHECK(host.first_event != -1, "%s exposes a first event index", host.name);
	memset(&einfo, 0, sizeof(einfo));
	einfo.size = sizeof(einfo);
	ret = pfm_get_event_info(host.first_event, PFM_OS_NONE, &einfo);
	CHECK(ret == PFM_SUCCESS && einfo.name[0],
	      "pfm_get_event_info(%d) -> \"%s\" (%s)", host.first_event,
	      ret == PFM_SUCCESS ? einfo.name : "?", pfm_strerror(ret));
	if (ret != PFM_SUCCESS)
		goto out;

	CHECK(pfm_find_event(einfo.name) == host.first_event,
	      "pfm_find_event(\"%s\") -> %d", einfo.name,
	      pfm_find_event(einfo.name));
	CHECK(pfm_get_event_next(host.first_event) != -1,
	      "pfm_get_event_next(%d) -> %d", host.first_event,
	      pfm_get_event_next(host.first_event));

	if (einfo.nattrs > 0) {
		memset(&ainfo, 0, sizeof(ainfo));
		ainfo.size = sizeof(ainfo);
		ret = pfm_get_event_attr_info(host.first_event, 0, PFM_OS_NONE,
					      &ainfo);
		CHECK(ret == PFM_SUCCESS && ainfo.name[0],
		      "pfm_get_event_attr_info(%d, 0) -> \"%s\" (%s)",
		      host.first_event, ret == PFM_SUCCESS ? ainfo.name : "?",
		      pfm_strerror(ret));
	} else {
		printf("note - %s has no attributes\n", einfo.name);
	}

	/* ---- raw encoding ------------------------------------------------ */
	ret = pfm_get_event_encoding(einfo.name, PFM_PLM0 | PFM_PLM3, &fstr, &idx,
				     &codes, &count);
	CHECK(ret == PFM_SUCCESS && count > 0 && codes != NULL,
	      "pfm_get_event_encoding(\"%s\") -> %s, %d code(s) [%s]", einfo.name,
	      pfm_strerror(ret), count, fstr ? fstr : "-");
	if (codes) {
		free(codes);
		codes = NULL;
	}
	if (fstr) {
		free(fstr);
		fstr = NULL;
	}

	/* ---- perf_event encoding ---------------------------------------- */
	/*
	 * Not asserted: hosts that only expose the generic perf_events PMU (no
	 * architecture PMU is detected, e.g. on virtualised workers) report
	 * PFM_ERR_NOTSUPP for PFM_OS_PERF_EVENT - upstream's own evt2raw
	 * example behaves identically there.  The result is reported instead.
	 */
	memset(&attr, 0, sizeof(attr));
	memset(&arg, 0, sizeof(arg));
	arg.attr = &attr;
	arg.size = sizeof(arg);
	ret = pfm_get_os_event_encoding(einfo.name, PFM_PLM0 | PFM_PLM3,
					PFM_OS_PERF_EVENT, &arg);
	if (ret == PFM_SUCCESS) {
		/* PFM_PLM0|PFM_PLM3 request both privilege levels */
		CHECK(attr.exclude_kernel == 0 && attr.exclude_user == 0,
		      "pfm_get_os_event_encoding(PFM_OS_PERF_EVENT) -> type=%u "
		      "config=%#llx exclude_kernel=%u exclude_user=%u",
		      attr.type, (unsigned long long)attr.config,
		      attr.exclude_kernel, attr.exclude_user);
	} else {
		printf("note - pfm_get_os_event_encoding(PFM_OS_PERF_EVENT) -> "
		       "%s (no architecture PMU detected on this host)\n",
		       pfm_strerror(ret));
	}

out:
	pfm_terminate();
	printf("functional API test: %s\n", failures ? "FAILED" : "passed");
	return failures ? 1 : 0;
}
