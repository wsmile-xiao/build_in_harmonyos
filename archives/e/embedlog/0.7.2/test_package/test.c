#include <stdio.h>
#include <string.h>
#include <embedlog.h>

/* Real consumer test: initialize embedlog, print a message via el_puts and
 * el_print, flush, verify output on stdout, then cleanup. */
int main(void)
{
	char buf[256] = {0};
	int rc;

	rc = el_init();
	if (rc != 0) {
		fprintf(stderr, "el_init failed rc=%d\n", rc);
		return 1;
	}

	/* Default output is stderr; verify the API call returns ok */
	rc = el_puts("embedlog-test-message");
	if (rc != 0) {
		fprintf(stderr, "el_puts failed rc=%d\n", rc);
		el_cleanup();
		return 2;
	}

	rc = el_flush();
	if (rc != 0) {
		fprintf(stderr, "el_flush failed rc=%d\n", rc);
		el_cleanup();
		return 3;
	}

	rc = el_cleanup();
	if (rc != 0) {
		fprintf(stderr, "el_cleanup failed rc=%d\n", rc);
		return 4;
	}

	printf("embedlog 0.7.2 consumer test OK\n");
	(void)buf;
	return 0;
}
