/* test.c — libpfm 4.13.0 consumer test (HarmonyOS PC / Linux).

   Real consumer of the packaged libpfm: initializes the perfmon library,
   enumerates the supported PMUs and prints the library version. No
   empty-shell test — the public pfm_* API from <perfmon/pfmlib.h> is
   actually called and its return values are checked (R34).
 */
#include <perfmon/pfmlib.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
	pfm_err_t ret = pfm_initialize();
	if (ret != PFM_SUCCESS) {
		printf("FAIL: pfm_initialize() -> %s\n", pfm_strerror(ret));
		return 1;
	}
	printf("PASS: pfm_initialize() succeeded\n");

	int version = pfm_get_version();
	printf("libpfm version: %d\n", version);
	if (version < (4 << 16)) {
		printf("FAIL: unexpected libpfm version %d\n", version);
		return 1;
	}

	/* enumerate PMUs exposed by the library on this target */
	pfm_pmu_info_t info;
	int count = 0;
	pfm_pmu_t pmu;
	pfm_for_all_pmus(pmu) {
		memset(&info, 0, sizeof(info));
		info.size = sizeof(info);
		ret = pfm_get_pmu_info(pmu, &info);
		if (ret != PFM_SUCCESS)
			continue; /* unknown/invalid PMU slot -> skip */
		count++;
		printf("PMU[%d] = %s\n", pmu, info.name ? info.name : "(null)");
	}
	if (count == 0) {
		/* library still initialized fine; zero PMUs is a valid target state */
		printf("note: no PMUs enumerated on this target\n");
	}
	printf("PASS: test_libpfm consumer test completed\n");
	return 0;
}