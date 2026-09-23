/*
 * Upstream test suite driven through the public API of the installed package.
 *
 * libpfm4 exposes the validation of its PMU event tables as public API:
 * tests/validate.c calls pfm_pmu_validate() for every PMU and classifies the
 * result (PFM_SUCCESS -> Passed, PFM_ERR_NOTSUPP -> N/A, anything else ->
 * Failed).  This test drives exactly the same entry point for every PMU, so
 * the upstream test cases are re-run against the library a consumer links
 * against (i.e. against the packaged artefacts, not against the build tree).
 *
 * tests/validate.c sets LIBPFM_ENCODE_INACTIVE=1 before pfm_initialize() so
 * that PMUs which are not present on the host (all architecture specific
 * tables, e.g. the ARMv8 ones) are validated as well; the same is done here.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <perfmon/pfmlib.h>

int main(void)
{
	pfm_pmu_info_t pinfo;
	pfm_pmu_t pmu;
	int ret, passed = 0, na = 0, failed = 0;

	/* same as tests/validate.c */
	if (setenv("LIBPFM_ENCODE_INACTIVE", "1", 1) != 0)
		perror("setenv(LIBPFM_ENCODE_INACTIVE)");

	ret = pfm_initialize();
	if (ret != PFM_SUCCESS) {
		printf("FAIL - pfm_initialize() -> %s\n", pfm_strerror(ret));
		return 1;
	}

	printf("upstream event table validation (libpfm4 %#x):\n",
	       pfm_get_version());

	pfm_for_all_pmus(pmu) {
		memset(&pinfo, 0, sizeof(pinfo));
		pinfo.size = sizeof(pinfo);
		ret = pfm_get_pmu_info(pmu, &pinfo);
		if (ret != PFM_SUCCESS)
			continue;

		printf("\tchecking %s (%d events): ", pinfo.name, pinfo.nevents);
		fflush(stdout);

		ret = pfm_pmu_validate(pmu, stdout);
		if (ret == PFM_SUCCESS) {
			printf("Passed\n");
			passed++;
		} else if (ret == PFM_ERR_NOTSUPP) {
			printf("N/A\n");
			na++;
		} else {
			printf("Failed (%s)\n", pfm_strerror(ret));
			failed++;
		}
	}

	pfm_terminate();

	printf("upstream event table validation: %d passed, %d N/A, %d failed\n",
	       passed, na, failed);
	if (failed || passed == 0)
		return 1;
	return 0;
}
