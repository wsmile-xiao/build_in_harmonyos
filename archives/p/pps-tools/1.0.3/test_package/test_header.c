/*
 * test_header.c -- consumer check for the installed PPSAPI header
 *                  (include/sys/timepps.h) shipped by pps-tools 1.0.3.
 *
 * Exercises the public types and the inline PPSAPI wrappers.  Calling
 * time_pps_create() with an invalid descriptor must fail (the header turns the
 * failed PPS_GETPARAMS ioctl into -1 / EOPNOTSUPP); a successful compile and
 * run proves the header and <linux/pps.h> agree on OHOS.
 */
#include <stdio.h>
#include <errno.h>
#include <sys/timepps.h>

int main(void)
{
	pps_handle_t handle = -1;
	pps_params_t params;
	pps_info_t info;
	int caps;
	int rc;

	params.api_version = 0;
	params.mode = PPS_CAPTUREASSERT | PPS_CAPTURECLEAR;
	info.assert_sequence = 0;
	info.clear_sequence = 0;

	rc = time_pps_create(-1, &handle);
	if (rc != -1) {
		fprintf(stderr, "time_pps_create(-1) unexpectedly succeeded\n");
		return 1;
	}

	caps = PPS_CAPTUREASSERT | PPS_CAPTURECLEAR | PPS_TSFMT_TSPEC;
	printf("timepps-ok mode=%d caps=%d seq=%lu\n",
	       params.mode, caps, (unsigned long)info.assert_sequence);
	return 0;
}
