/* Consumer test for the libf2c2 package.
 *
 * f2c translates Fortran into C that calls this run time instead of emitting
 * the intrinsic functions and the I/O code inline, so the test drives the
 * library the way translated code does: through the f2c.h ABI, including the
 * cilist / olist / cllist descriptor structs and the do_lio() list-directed
 * path that sits behind every Fortran READ and WRITE statement.
 *
 * Every call below goes through libf2c; no assertion is satisfied by a
 * locally re-implemented helper.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "f2c.h"

/* Declarations follow the definitions in the sources of this package
 * (s_cmp.c, s_copy.c, i_indx.c, d_prod.c, pow_dd.c, d_lg10.c, i_nint.c,
 * d_sign.c, uninit.c, open.c, close.c, wsle.c, lread.c, dolio.c). */
extern integer s_cmp(char *a0, char *b0, ftnlen la, ftnlen lb);
extern void s_copy(register char *a, register char *b, ftnlen la, ftnlen lb);
extern integer i_indx(char *a, char *b, ftnlen la, ftnlen lb);
extern double d_prod(real *x, real *y);
extern double pow_dd(doublereal *ap, doublereal *bp);
extern double d_lg10(doublereal *x);
extern integer i_nint(real *x);
extern double d_sign(doublereal *a, doublereal *b);
extern void _uninit_f2c(void *x, int type, long len);
extern integer f_open(olist *a);
extern integer f_clos(cllist *a);
extern integer s_wsle(cilist *a);
extern integer e_wsle(void);
extern integer s_rsle(cilist *a);
extern integer e_rsle(void);
extern integer do_lio(ftnint *type, ftnint *number, char *ptr, ftnlen len);

/* f2c's internal type codes for do_lio(), as used by generated code. */
#define TYLONG 3
#define TYREAL 4
#define TYDREAL 5

#define TEST_FILE "libf2c2_consumer_test.dat"

static int failures;

static void
check(int condition, const char *what)
{
	if (condition) {
		printf("ok   - %s\n", what);
		return;
	}
	printf("FAIL - %s\n", what);
	failures++;
}

static int
check_close(double got, double want, const char *what)
{
	double delta = got - want;
	if (delta < 0)
		delta = -delta;
	return delta <= 1e-12 * (want < 0 ? -want : want) + 1e-12
		? (check(1, what), 0)
		: (printf("FAIL - %s (got %.17g, want %.17g)\n", what, got, want),
		   failures++, 0);
}

/* Fortran descriptor blocks, initialized the way f2c initializes them for
 * OPEN(UNIT=17, FILE=..., STATUS='UNKNOWN'), a list-directed WRITE/READ on
 * that unit, and CLOSE(UNIT=17). */
static olist open_desc = {
	0,                                    /* oerr   */
	17,                                   /* ounit  */
	TEST_FILE,                            /* ofnm   */
	(ftnlen)(sizeof(TEST_FILE) - 1),      /* ofnmlen */
	"unknown",                            /* osta   */
	"sequential",                         /* oacc   */
	"formatted",                          /* ofm    */
	0,                                    /* orl    */
	0                                     /* oblnk  */
};
static olist reopen_desc = {
	0, 17, TEST_FILE, (ftnlen)(sizeof(TEST_FILE) - 1),
	"old", "sequential", "formatted", 0, 0
};
static cilist io_desc = {0, 17, 0, 0, 0};
static cllist close_desc = {0, 17, "keep"};

static void
test_intrinsics(void)
{
	real two_and_a_half = 2.5f;
	real four = 4.0f;
	real rounding = 2.6f;
	real negative_rounding = -2.6f;
	doublereal base = 2.0;
	doublereal exponent = 10.0;
	doublereal thousand = 1000.0;
	doublereal magnitude = 3.0;
	doublereal sign_source = -2.0;

	check_close(d_prod(&two_and_a_half, &four), 10.0,
		    "d_prod (REAL*REAL -> DOUBLE PRECISION)");
	check_close(pow_dd(&base, &exponent), 1024.0, "pow_dd (integer power)");
	check_close(d_lg10(&thousand), 3.0, "d_lg10 (base-10 logarithm)");
	check(i_nint(&rounding) == 3, "i_nint rounds 2.6 up to 3");
	check(i_nint(&negative_rounding) == -3, "i_nint rounds -2.6 down to -3");
	check_close(d_sign(&magnitude, &sign_source), -3.0,
		    "d_sign copies the sign of the second argument");
}

static void
test_string_runtime(void)
{
	char left[11];
	char right[11];

	check(s_cmp("abc", "abc", 3, 3) == 0, "s_cmp reports equal strings");
	check(s_cmp("abc", "abd", 3, 3) < 0, "s_cmp orders abc before abd");
	check(s_cmp("abc", "abc  ", 3, 5) == 0,
	      "s_cmp blank-pads the shorter Fortran string");
	check(i_indx("hello world", "world", 11, 5) == 7,
	      "i_indx returns the 1-based position of a substring");
	check(i_indx("hello world", "xyz", 11, 3) == 0,
	      "i_indx returns 0 when the substring is absent");

	memset(left, '#', sizeof(left));
	memset(right, '#', sizeof(right));
	s_copy(left, "short", 10, 5);
	check(memcmp(left, "short     ", 10) == 0,
	      "s_copy blank-pads to the destination length");
	s_copy(right, "0123456789", 5, 10);
	check(memcmp(right, "01234", 5) == 0, "s_copy truncates long sources");
}

static void
test_trapuv_helper(void)
{
	real real_value = 1.0f;
	doublereal double_value = 1.0;

	/* _uninit_f2c is the run-time half of f2c's -trapuv: initializing an
	 * uninitialised variable to NaN is what makes such a variable
	 * detectable. It is also the one translation unit that needed the
	 * fpu_control.h portability patch. */
	_uninit_f2c(&real_value, TYREAL, 1);
	check(real_value != real_value, "_uninit_f2c marks a REAL as NaN");
	_uninit_f2c(&double_value, TYDREAL, 1);
	check(double_value != double_value,
	      "_uninit_f2c marks a DOUBLE PRECISION as NaN");
}

static void
test_list_directed_io(void)
{
	real written_real = -1.25f;
	integer written_integer = -12345;
	real read_real = 0.0f;
	integer read_integer = 0;
	ftnint tyreal = TYREAL;
	ftnint tylong = TYLONG;
	ftnint one = 1;

	if (f_open(&open_desc) != 0) {
		printf("FAIL - f_open could not create %s\n", TEST_FILE);
		failures++;
		return;
	}
	check(s_wsle(&io_desc) == 0, "s_wsle starts a list-directed record");
	check(do_lio(&tyreal, &one, (char *)&written_real, (ftnlen)sizeof(real)) == 0,
	      "do_lio writes a REAL through the run time");
	check(do_lio(&tylong, &one, (char *)&written_integer,
		     (ftnlen)sizeof(integer)) == 0,
	      "do_lio writes an INTEGER through the run time");
	check(e_wsle() == 0, "e_wsle terminates the record");
	check(f_clos(&close_desc) == 0, "f_clos closes and keeps the file");

	if (f_open(&reopen_desc) != 0) {
		printf("FAIL - f_open could not reopen %s\n", TEST_FILE);
		failures++;
		return;
	}
	check(s_rsle(&io_desc) == 0, "s_rsle starts a list-directed read");
	check(do_lio(&tyreal, &one, (char *)&read_real, (ftnlen)sizeof(real)) == 0,
	      "do_lio reads a REAL back through the run time");
	check(do_lio(&tylong, &one, (char *)&read_integer,
		     (ftnlen)sizeof(integer)) == 0,
	      "do_lio reads an INTEGER back through the run time");
	check(e_rsle() == 0, "e_rsle ends the list-directed read");
	check(f_clos(&close_desc) == 0, "f_clos closes the reopened file");

	check_close((double)read_real, -1.25, "the REAL survived the round trip");
	check(read_integer == written_integer,
	      "the INTEGER survived the round trip");
	remove(TEST_FILE);
}

int
main(void)
{
	test_intrinsics();
	test_string_runtime();
	test_trapuv_helper();
	test_list_directed_io();

	if (failures) {
		printf("\n%d check(s) failed\n", failures);
		return 1;
	}
	printf("\nall checks passed\n");
	return 0;
}
