/*
 * Consumer program for libaccel-config — read-only API only.
 *
 * Calls accfg_new / accfg_get_log_priority / accfg_set_log_priority /
 * accfg_unref.  These functions do not touch sysfs, devices or kernel
 * modules, so the test is safe on hosts without Intel DSA/IAA hardware.
 * Returns 0 on success, 1 on failure.
 */
#include <stdio.h>
#include <syslog.h>
#include <accel-config/libaccel_config.h>

int main(void)
{
	struct accfg_ctx *ctx = NULL;
	int rc;

	rc = accfg_new(&ctx);
	if (rc < 0) {
		fprintf(stderr, "accfg_new failed rc=%d\n", rc);
		return 1;
	}

	printf("accfg_new ok, log_priority=%d\n", accfg_get_log_priority(ctx));
	accfg_set_log_priority(ctx, LOG_DEBUG);
	if (accfg_get_log_priority(ctx) != LOG_DEBUG) {
		fprintf(stderr, "accfg_set_log_priority did not take effect\n");
		accfg_unref(ctx);
		return 1;
	}
	printf("after set log_priority=%d\n", accfg_get_log_priority(ctx));

	accfg_unref(ctx);
	printf("consumer PASS\n");
	return 0;
}
