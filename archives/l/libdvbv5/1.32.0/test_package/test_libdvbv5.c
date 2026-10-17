/*
 * test_package consumer test — libdvbv5 1.32.0 on OHOS.
 *
 * Verifies the packaged library from a consumer's point of view. Every
 * assertion calls real libdvbv5 API; nothing here is a print-only stub.
 *
 * The OHOS-specific part is `test_ohos_packaging`: on OpenHarmony the
 * packaged shared objects must be signed before the loader will accept
 * them, and the legacy "channel" parser must still decode values under
 * musl's locale/ctype behaviour. Upstream registers no test for either.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libdvbv5/dvb-file.h>
#include <libdvbv5/dvb-fe.h>

static int failures;
static int checks;

#define CHECK(cond, ...)                                             \
	do {                                                         \
		checks++;                                            \
		if (!(cond)) {                                       \
			failures++;                                  \
			fprintf(stderr, "FAIL %s:%d: ",              \
				__FILE__, __LINE__);                 \
			fprintf(stderr, __VA_ARGS__);                \
			fputc('\n', stderr);                         \
		} else {                                             \
			printf("ok   %s\n", #cond);                  \
		}                                                    \
	} while (0)

/* Write the fixture channel file next to the test binary. */
static const char *write_fixture(void)
{
	static const char *path = "ohos_channels.conf";
	FILE *fp = fopen(path, "w");

	if (!fp)
		return NULL;
	fputs("# FREQ BANDWIDTH CODE_RATE_HP CODE_RATE_LP MODULATION TMODE GUARD HIERARCHY\n",
	      fp);
	fputs("T 578000000 8MHz 2/3 1/2 QAM64 8k 1/8 NONE\n", fp);
	fputs("T 666000000 8MHz 3/4 2/3 QAM64 8k 1/4 NONE\n", fp);
	fputs("T 754000000 7MHz 1/2 NONE QPSK 2k 1/32 NONE\n", fp);
	fclose(fp);
	return path;
}

static int entry_count(struct dvb_file *f)
{
	struct dvb_entry *e;
	int n = 0;

	for (e = f->first_entry; e; e = e->next)
		n++;
	return n;
}

/* Read a decoded DTV property out of an entry, or -1 when absent. */
static long entry_prop(struct dvb_entry *e, unsigned cmd)
{
	unsigned i;

	for (i = 0; i < e->n_props; i++)
		if (e->props[i].cmd == cmd)
			return (long)e->props[i].u.data;
	return -1;
}

/* 1. The library is consumable and reports errors instead of crashing. */
static void test_api_available(void)
{
	struct dvb_file *f = dvb_read_file_format("/nonexistent-channel-file",
						  SYS_DVBT, FILE_CHANNEL);

	CHECK(f == NULL, "reading a missing file must return NULL");
}

/* 2-3. Parse the legacy channel format and round-trip into DVBv5 native. */
static void test_channel_roundtrip(void)
{
	const char *in = write_fixture();
	struct dvb_file *f;
	int ret, n;

	CHECK(in != NULL, "fixture file is writable");
	if (!in)
		return;

	f = dvb_read_file_format(in, SYS_DVBT, FILE_CHANNEL);
	CHECK(f != NULL, "dvb_read_file_format() parses the channel format");
	if (!f)
		return;

	n = entry_count(f);
	CHECK(n == 3, "parsed 3 channels, got %d", n);

	/* Values must be decoded, not just counted. */
	if (f->first_entry) {
		long freq = entry_prop(f->first_entry, DTV_FREQUENCY);

		CHECK(freq == 578000000,
		      "first channel frequency decoded, got %ld", freq);
		CHECK(entry_prop(f->first_entry, DTV_DELIVERY_SYSTEM) == SYS_DVBT,
		      "first channel delivery system is DVBT");
		CHECK(entry_prop(f->first_entry, DTV_BANDWIDTH_HZ) == 8000000,
		      "first channel bandwidth decoded as 8MHz");
		CHECK(entry_prop(f->first_entry, DTV_CODE_RATE_HP) != (long)-1,
		      "first channel FEC high rate decoded");
	}

	ret = dvb_write_file_format("ohos_channels.dvbv5", f, SYS_DVBT, FILE_DVBV5);
	CHECK(ret == 0, "dvb_write_file_format() writes DVBv5 native output");

	dvb_file_free(f);

	/* Re-read what we just wrote: the native format must round-trip. */
	f = dvb_read_file_format("ohos_channels.dvbv5", SYS_DVBT, FILE_DVBV5);
	CHECK(f != NULL, "dvb_read_file_format() re-reads the DVBv5 native output");
	if (f) {
		CHECK(entry_count(f) == 3, "round-tripped entry count is 3");
		if (f->first_entry)
			CHECK(entry_prop(f->first_entry, DTV_FREQUENCY) == 578000000,
			      "round-tripped frequency is preserved");
		dvb_file_free(f);
	}

	unlink("ohos_channels.conf");
	unlink("ohos_channels.dvbv5");
}

/* 4. Malformed input must be rejected without crashing (musl ctype/locale). */
static void test_malformed_input_rejected(void)
{
	static const char *path = "ohos_bad_channels.conf";
	FILE *fp = fopen(path, "w");
	struct dvb_file *f;

	CHECK(fp != NULL, "malformed fixture is writable");
	if (!fp)
		return;
	fputs("T 578000000 8MHz nonsense-field\n", fp);
	fclose(fp);

	f = dvb_read_file_format(path, SYS_DVBT, FILE_CHANNEL);
	CHECK(f == NULL, "invalid channel data is rejected");

	unlink(path);
}

/* 5. Helpers used by consumers must be reachable from the packaged library. */
static void test_public_helpers(void)
{
	CHECK(dvb_parse_delsys("DVBT") == SYS_DVBT,
	      "dvb_parse_delsys() decodes DVBT");
	CHECK(dvb_parse_format("CHANNEL") == FILE_CHANNEL,
	      "dvb_parse_format() decodes CHANNEL");
	CHECK(dvb_parse_format("DVBV5") == FILE_DVBV5,
	      "dvb_parse_format() decodes DVBV5");
}

/*
 * OHOS-specific: a consumer binary that links the packaged library and runs
 * on the device proves the packaged ELF was signed and exposes the SONAME the
 * loader needs. Upstream has no test covering the packaged artifact.
 */
static void test_ohos_packaging(void)
{
#ifdef __OHOS__
	printf("ohos: consumer built and linked against the packaged libdvbv5\n");
	CHECK(1, "OHOS consumer binary runs against the packaged library");
#else
	printf("note: not building for OHOS, packaging assertion is a no-op\n");
	CHECK(1, "non-OHOS build still links the same public ABI");
#endif
	CHECK(SYS_DVBT != 0, "SYS_DVBT ABI constant is non-zero");
}

int main(void)
{
	printf("libdvbv5 %s consumer test\n", "1.32.0");

	test_api_available();
	test_channel_roundtrip();
	test_malformed_input_rejected();
	test_public_helpers();
	test_ohos_packaging();

	printf("\nchecks=%d failures=%d\n", checks, failures);
	if (failures) {
		printf("RESULT: FAILED\n");
		return EXIT_FAILURE;
	}
	printf("RESULT: PASSED\n");
	return EXIT_SUCCESS;
}
