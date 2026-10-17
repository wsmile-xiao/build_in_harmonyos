/* maloc/1.5 test_package: real assertions against the shipped libmaloc.
 * 1) header identity  : <maloc/maloc.h> is found and preprocesses (includedir
 *    evidence: src/aaa_inc/maloc/Makefile.am:52 "includedir = /include/maloc")
 * 2) header constants : values asserted below are read from the same upstream
 *    headers that are installed (vio.h "#define VPORTNUMBER 14916").
 * 3) symbol/link      : Vio_start() is called; it is the first maloc call made
 *    by the upstream tool itself (tools/main.c:83 "Vio_start();").
 * 4) behaviour        : VNULL sentinel must be usable as the "no object" value
 *    that upstream compares against (tools/main.c:86 "VNULL==(inSock=Vio_ctor(...))").
 */
#include <maloc/maloc.h>

#include <stdio.h>
#include <stdlib.h>

static int failures = 0;

static void expect(const char *what, int ok)
{
	printf("[test] %-46s %s\n", what, ok ? "PASS" : "FAIL");
	if (!ok)
		failures++;
}

int main(void)
{
	/* (2) compile-time: constant shipped in the installed vio.h */
	_Static_assert(VPORTNUMBER == 14916, "VPORTNUMBER differs from upstream vio.h");

	/* (4) run-time: the sentinel every maloc constructor compares against */
	expect("VNULL sentinel is the zero pointer", VNULL == 0);

	/* (3) link + run: start the Vio communication layer, as tools/main.c does */
	Vio_start();
	expect("Vio_start() returned without aborting", 1);

	if (failures) {
		printf("maloc test_package: %d assertion(s) FAILED\n", failures);
		return EXIT_FAILURE;
	}
	printf("maloc test_package: all assertions passed (3 checks)\n");
	return EXIT_SUCCESS;
}
