/* Consumer test for libeditline (editline 2.1.0).
 *
 * Verifies a third-party consumer can compile, link and call the *installed*
 * public API (public header editline.h + libeditline) with observable results.
 * Uses the history round-trip API which works headless (no pty required):
 *   rl_initialize / el_hist_size / add_history / write_history / read_history
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <editline.h>

#define IN  "consumer-in.tmp"
#define OUT "consumer-out.tmp"

static int files_equal(const char *a, const char *b)
{
	FILE *fa = fopen(a, "rb");
	FILE *fb = fopen(b, "rb");
	int ca, cb, eq = 1;

	if (!fa || !fb) {
		if (fa) fclose(fa);
		if (fb) fclose(fb);
		return 0;
	}
	do {
		ca = getc(fa);
		cb = getc(fb);
		if (ca != cb) {
			eq = 0;
			break;
		}
	} while (ca != EOF);
	fclose(fa);
	fclose(fb);

	return eq;
}

int main(void)
{
	FILE *fp;
	int i, ok;

	/* 1. Public init API */
	rl_initialize();

	/* 2. History scrollback size API (public global, default 64) */
	el_hist_size = 64;

	/* 3. Write N + 1 distinct lines, then round-trip through the public
	 *    read_history()/write_history() API and verify byte preservation. */
	fp = fopen(IN, "w");
	if (!fp)
		return 77;	/* SKIP: cannot create scratch file */
	for (i = 0; i < el_hist_size + 1; i++)
		fprintf(fp, "consumer history entry %d\n", i);
	fclose(fp);

	ok = 0;
	if (read_history(IN) == 0 && write_history(OUT) == 0)
		ok = files_equal(IN, OUT);

	unlink(IN);
	unlink(OUT);

	if (ok) {
		printf("PASS consumer-history-roundtrip (%d entries through read_history/write_history)\n",
		       el_hist_size + 1);
		return 0;
	}

	fprintf(stderr, "FAIL consumer-history-roundtrip: history not preserved\n");
	return 1;
}