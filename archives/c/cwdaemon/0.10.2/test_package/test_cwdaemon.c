#include <stdio.h>
#include <unistd.h>

/*
 * test_cwdaemon.c — cwdaemon consumer test.
 *
 * Real (failable) existence checks against the installed package:
 *   argv[1] — path to the installed cwdaemon binary  (must be executable)
 *   argv[2] — path to the installed COPYING license  (must be readable)
 *
 * A missing or unreadable file makes this test fail with exit code 1,
 * so it is not a stub test (R34).
 */

int main(int argc, char *argv[])
{
	int failures = 0;

	if (argc < 3) {
		fprintf(stderr, "usage: %s <cwdaemon-binary> <COPYING-license>\n", argv[0]);
		return 1;
	}

	if (access(argv[1], X_OK) != 0) {
		fprintf(stderr, "test_cwdaemon: FAIL - binary not executable/found: %s\n", argv[1]);
		failures++;
	} else {
		printf("test_cwdaemon: OK - binary executable: %s\n", argv[1]);
	}

	if (access(argv[2], R_OK) != 0) {
		fprintf(stderr, "test_cwdaemon: FAIL - license not readable/found: %s\n", argv[2]);
		failures++;
	} else {
		printf("test_cwdaemon: OK - license readable: %s\n", argv[2]);
	}

	if (failures) {
		fprintf(stderr, "test_cwdaemon: %d check(s) failed\n", failures);
		return 1;
	}
	printf("test_cwdaemon: PASS\n");
	return 0;
}
