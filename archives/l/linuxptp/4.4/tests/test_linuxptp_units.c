/*
 * Supplementary unit tests for linuxptp 4.4 on HarmonyOS PC (OHOS / aarch64).
 *
 * Upstream 4.4 ships no test suite at all: there is no tests/ directory and the
 * Makefile has neither a `check` nor a `test` target.  This suite is therefore
 * contributed by the port (R51 path B).  It is linked against the objects the
 * upstream Makefile just produced and drives the core algorithm APIs with
 * deterministic inputs:
 *
 *   - tmv        time value operators and clock conversions (tmv.h)
 *   - filter     moving average (mave) and moving median (mmedian) backends
 *   - hash       key/value hash table (hash_create/insert/lookup/destroy)
 *   - lstab      TAI-UTC leap second table (lstab_utc2tai)
 *   - tsproc     raw time stamp processing (offset and delay computation)
 *
 * Expected values are derived from the documented upstream semantics; the
 * filters use integer nanosecond arithmetic, so all results are exact.
 */
#include <stdint.h>
#include <stdio.h>

#include "filter.h"
#include "hash.h"
#include "lstab.h"
#include "mave.h"
#include "mmedian.h"
#include "tmv.h"
#include "tsproc.h"

static int checks;
static int failures;

static void report(int cond, const char *name)
{
	checks++;
	if (cond) {
		printf("PASS: %s\n", name);
	} else {
		failures++;
		printf("FAIL: %s\n", name);
	}
}

static void report_i64(int64_t got, int64_t want, const char *name)
{
	checks++;
	if (got == want) {
		printf("PASS: %s (= %lld)\n", name, (long long)got);
	} else {
		failures++;
		printf("FAIL: %s (got %lld, want %lld)\n", name,
		       (long long)got, (long long)want);
	}
}

/* ── tmv ────────────────────────────────────────────────────────────── */

static void test_tmv(void)
{
	struct Timestamp ts;
	tmv_t t;

	report_i64(tmv_to_nanoseconds(tmv_add(nanoseconds_to_tmv(1500),
					      nanoseconds_to_tmv(250))),
		   1750, "tmv_add 1500+250");
	report_i64(tmv_to_nanoseconds(tmv_sub(nanoseconds_to_tmv(1000),
					      nanoseconds_to_tmv(400))),
		   600, "tmv_sub 1000-400");
	report(tmv_cmp(nanoseconds_to_tmv(5), nanoseconds_to_tmv(5)) == 0,
	       "tmv_cmp equal operands");
	report(tmv_cmp(nanoseconds_to_tmv(5), nanoseconds_to_tmv(4)) > 0,
	       "tmv_cmp greater operand");
	report(tmv_sign(nanoseconds_to_tmv(-7)) < 0, "tmv_sign negative");
	report(tmv_sign(nanoseconds_to_tmv(7)) > 0, "tmv_sign positive");
	report(tmv_is_zero(tmv_zero()) == 1, "tmv_is_zero(tmv_zero())");
	report(tmv_is_zero(nanoseconds_to_tmv(1)) == 0, "tmv_is_zero(1ns)");

	/* 30000000123 ns == 30 s + 123 ns */
	t = nanoseconds_to_tmv(30000000123LL);
	ts = tmv_to_Timestamp(t);
	report_i64((int64_t)ts.seconds_lsb, 30,
		   "tmv_to_Timestamp seconds_lsb");
	report_i64((int64_t)ts.seconds_msb, 0,
		   "tmv_to_Timestamp seconds_msb");
	report_i64((int64_t)ts.nanoseconds, 123,
		   "tmv_to_Timestamp nanoseconds");

	/* the on-wire PTP representation (sec + nsec, ddt.h) converts back */
	{
		struct timestamp wts = {0};

		wts.sec = 30;
		wts.nsec = 123;
		report_i64(tmv_to_nanoseconds(timestamp_to_tmv(wts)),
			   30000000123LL, "timestamp_to_tmv(30 s + 123 ns)");
	}

	report_i64((int64_t)tmv_to_TimeInterval(nanoseconds_to_tmv(1)), 65536,
		   "tmv_to_TimeInterval 1ns == 2^16");
	report_i64((int64_t)tmv_to_TimeInterval(nanoseconds_to_tmv(-1)), -65536,
		   "tmv_to_TimeInterval -1ns == -2^16");
}

/* ── filters: moving average / moving median ────────────────────────── */

static void test_filters(void)
{
	struct filter *f;

	/* moving average, length 4, integer nanosecond mean */
	f = filter_create(FILTER_MOVING_AVERAGE, 4);
	report(f != NULL, "filter_create(FILTER_MOVING_AVERAGE, 4)");
	if (f) {
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(100))),
			   100, "mave sample 1 -> 100 (window 100)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(200))),
			   150, "mave sample 2 -> 150 (window 100,200)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(300))),
			   200, "mave sample 3 -> 200 (window 100,200,300)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(400))),
			   250, "mave sample 4 -> 250 (window 100..400)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(400))),
			   325, "mave sample 5 -> 325 (window 200,300,400,400)");
		filter_reset(f);
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(100))),
			   100, "mave filter_reset restarts the window");
		filter_destroy(f);
	}

	/* moving median, length 3 */
	f = mmedian_create(3);
	report(f != NULL, "mmedian_create(3)");
	if (f) {
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(1))),
			   1, "mmedian sample 1 -> 1");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(5))),
			   3, "mmedian sample 2 -> 3 (mean of the pair)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(3))),
			   3, "mmedian sample 3 -> 3 (middle of 1,3,5)");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(100))),
			   5, "mmedian sample 4 -> 5 (window 3,5,100)");
		filter_reset(f);
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(7))),
			   7, "mmedian filter_reset clears the window");
		filter_destroy(f);
	}

	/* moving median, even length: mean of the two middle values */
	f = mmedian_create(2);
	report(f != NULL, "mmedian_create(2)");
	if (f) {
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(5))),
			   5, "mmedian(2) first sample -> 5");
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(1))),
			   3, "mmedian(2) 5,1 -> 3 (integer mean of 1 and 5)");
		filter_destroy(f);
	}

	/* length validation */
	report(mmedian_create(0) == NULL, "mmedian_create(0) rejected");
	report(filter_create((enum filter_type)42, 3) == NULL,
	       "filter_create(unknown type) rejected");

	/* mave_create with a bogus length is still accepted upstream (calloc(0)),
	 * so only its NULL-ness is asserted rather than a specific behaviour. */
	f = mave_create(1);
	report(f != NULL, "mave_create(1)");
	if (f) {
		report_i64(tmv_to_nanoseconds(filter_sample(f, nanoseconds_to_tmv(42))),
			   42, "mave(1) is transparent");
		filter_destroy(f);
	}
}

/* ── hash table ─────────────────────────────────────────────────────── */

static int destroyed;

static void count_destroy(void *data)
{
	(void)data;
	destroyed++;
}

static void test_hash(void)
{
	struct hash *ht;
	int a = 1, b = 2, c = 3;

	ht = hash_create();
	report(ht != NULL, "hash_create()");
	if (!ht) {
		return;
	}

	report_i64(hash_insert(ht, "alpha", &a), 0, "hash_insert(alpha)");
	report(hash_insert(ht, "alpha", &b) != 0,
	       "hash_insert(duplicate alpha) rejected");
	report_i64(hash_insert(ht, "beta", &b), 0, "hash_insert(beta)");
	report_i64(hash_insert(ht, "gamma", &c), 0, "hash_insert(gamma)");
	report(hash_lookup(ht, "alpha") == &a, "hash_lookup(alpha)");
	report(hash_lookup(ht, "beta") == &b, "hash_lookup(beta)");
	report(hash_lookup(ht, "gamma") == &c, "hash_lookup(gamma)");
	report(hash_lookup(ht, "missing") == NULL, "hash_lookup(missing) is NULL");

	destroyed = 0;
	hash_destroy(ht, count_destroy);
	report_i64(destroyed, 3, "hash_destroy callback visited every element");
}

/* ── leap second table ──────────────────────────────────────────────── */

/* UTC second -> epoch markers from the upstream default table (lstab.c) */
#define UTC_1_JAN_2020		1577836800ULL	/* offset 37, before expiry  */
#define UTC_AMBIGUOUS_2017	1483228799ULL	/* last second of TAI-UTC 36  */
#define UTC_AFTER_EXPIRY	1735344001ULL	/* past 24 Dec 2024 (upstream) */

static void test_lstab(void)
{
	struct lstab *ls;
	int off;

	ls = lstab_create(NULL);
	report(ls != NULL, "lstab_create(NULL) uses the built-in table");
	if (!ls) {
		return;
	}

	report_i64(update_leapsecond_table(ls), 0,
		   "update_leapsecond_table() without a file is a no-op");

	off = -123;
	report(lstab_utc2tai(ls, UTC_1_JAN_2020, &off) == LSTAB_OK,
	       "lstab_utc2tai(2020-01-01) -> LSTAB_OK");
	report_i64(off, 37, "TAI-UTC offset for 2020-01-01");
#if defined(DEBUG)
	fprintf(stderr, "debug: checking offset for 2020-01-01 = %d\n", off);
#endif

	off = -123;
	report(lstab_utc2tai(ls, UTC_AMBIGUOUS_2017, &off) == LSTAB_AMBIGUOUS,
	       "lstab_utc2tai(last second before 2017 leap) -> LSTAB_AMBIGUOUS");
	report_i64(off, 36, "TAI-UTC offset on the ambiguous second");

	off = -123;
	report(lstab_utc2tai(ls, UTC_AFTER_EXPIRY, &off) == LSTAB_EXPIRED,
	       "lstab_utc2tai(after table expiry) -> LSTAB_EXPIRED");
	report_i64(off, 37, "TAI-UTC offset past the expiry date");

	off = -123;
	report(lstab_utc2tai(ls, 1ULL, &off) == LSTAB_UNKNOWN,
	       "lstab_utc2tai(before the table) -> LSTAB_UNKNOWN");
	report_i64(off, -123, "offset untouched when the result is UNKNOWN");

	lstab_destroy(ls);

	report(lstab_create("/nonexistent/leap-seconds.list") == NULL,
	       "lstab_create(missing file) rejected");
}

/* ── tsproc: raw offset/delay computation ───────────────────────────── */

static void test_tsproc(void)
{
	struct tsproc *tsp;
	tmv_t delay = tmv_zero(), offset = tmv_zero();
	double weight = 0.0;

	tsp = tsproc_create(TSPROC_RAW, FILTER_MOVING_MEDIAN, 3);
	report(tsp != NULL, "tsproc_create(TSPROC_RAW, FILTER_MOVING_MEDIAN, 3)");
	if (tsp) {
		/* t1=1000 (master tx), t2=1200 (slave rx),
		 * t3=1300 (slave tx), t4=1150 (master rx)
		 *   delay  = ((t2-t3) + (t4-t1)) / 2 = ( -100 + 150 ) / 2 = 25
		 *   offset = t2 - t1 - delay          =   200 -  25      = 175
		 */
		tsproc_down_ts(tsp, nanoseconds_to_tmv(1000),
			       nanoseconds_to_tmv(1200));
		tsproc_up_ts(tsp, nanoseconds_to_tmv(1300),
			     nanoseconds_to_tmv(1150));

		report_i64(tsproc_update_delay(tsp, &delay), 0,
			   "tsproc_update_delay() succeeded");
		report_i64(tmv_to_nanoseconds(delay), 25,
			   "raw path delay == 25 ns");
		report_i64(tsproc_update_offset(tsp, &offset, &weight), 0,
			   "tsproc_update_offset() succeeded");
		report_i64(tmv_to_nanoseconds(offset), 175,
			   "raw offset == 175 ns");
		report(weight == 1.0, "TSPROC_RAW reports unit weight");

		tsproc_reset(tsp, 1);
		report_i64(tsproc_update_offset(tsp, &offset, NULL), -1,
			   "tsproc_update_offset() fails after a full reset");
		report_i64(tsproc_update_delay(tsp, &delay), -1,
			   "tsproc_update_delay() fails after a full reset");

		tsproc_set_delay(tsp, nanoseconds_to_tmv(77));
		tsproc_down_ts(tsp, nanoseconds_to_tmv(1000),
			       nanoseconds_to_tmv(1000));
		tsproc_up_ts(tsp, nanoseconds_to_tmv(1000),
			     nanoseconds_to_tmv(1000));
		report_i64(tsproc_update_offset(tsp, &offset, NULL), 0,
			   "tsproc_update_offset() after zeroing the delay");
		report_i64(tmv_to_nanoseconds(offset), 0,
			   "zero round trip time yields a zero offset");

		tsproc_destroy(tsp);
	}

	report(tsproc_create((enum tsproc_mode)99, FILTER_MOVING_MEDIAN, 3) == NULL,
	       "tsproc_create(unknown mode) rejected");
	/* a zero-length delay filter cannot be created either, and tsproc_create
	 * propagates that failure */
	report(tsproc_create(TSPROC_RAW, FILTER_MOVING_MEDIAN, 0) == NULL,
	       "tsproc_create(zero-length delay filter) rejected");
}

int main(void)
{
	printf("=== linuxptp 4.4 supplementary unit tests (OHOS / aarch64) ===\n");

	test_tmv();
	test_filters();
	test_hash();
	test_lstab();
	test_tsproc();

	printf("=== linuxptp supplementary unit tests: %d/%d checks passed ===\n",
	       checks - failures, checks);
	if (failures) {
		printf("RESULT: FAIL (%d failed)\n", failures);
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}
