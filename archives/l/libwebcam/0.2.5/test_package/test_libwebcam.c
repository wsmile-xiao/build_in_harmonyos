/*
 * libwebcam test package: verify the library links and its API works.
 * These calls do not require a physical camera.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <webcam.h>

static int failures = 0;

static void check_error_text(CResult code, const char *expected)
{
	char *text = c_get_error_text(code);
	if (!text) {
		fprintf(stderr, "FAIL: c_get_error_text(%u) returned NULL\n", code);
		failures++;
		return;
	}
	if (expected && strcmp(text, expected) != 0) {
		fprintf(stderr, "FAIL: c_get_error_text(%u) = '%s', expected '%s'\n",
			code, text, expected);
		failures++;
	} else {
		printf("PASS: c_get_error_text(%u) = '%s'\n", code, text);
	}
	free(text);
}

int main(void)
{
	/* 1. C_SUCCESS must map to "Success". */
	check_error_text(C_SUCCESS, "Success");

	/* 2. C_INVALID_ARG must map to "Invalid argument". */
	check_error_text(C_INVALID_ARG, "Invalid argument");

	/* 3. C_NOT_IMPLEMENTED must return a non-NULL description. */
	check_error_text(C_NOT_IMPLEMENTED, NULL);

	/* 4. c_cleanup() must be safe to call without any device. */
	c_cleanup();
	printf("PASS: c_cleanup() completed without crash\n");

	if (failures) {
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("All libwebcam smoke checks passed.\n");
	return 0;
}
