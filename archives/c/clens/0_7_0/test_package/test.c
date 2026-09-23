/*
 * Consumer-side test for clens 0_7_0 on OpenHarmony.
 *
 * Exercises every API the trimmed static library actually provides
 * (clens_verstring, clens_version, strtonum, fmt_scaled/scan_scaled,
 * fparseln) and additionally links+runs the OpenBSD-compat symbols that
 * resolve from OHOS libc instead of libclens.a (strlcpy, strlcat,
 * arc4random_uniform, glob). All expected values were captured from real
 * runs of the upstream implementations (see notes.md); failures abort
 * with a non-zero exit code.
 */
#include <errno.h>
#include <glob.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <clens/clens.h>

static int failures = 0;

#define CHECK(cond)                                                          \
	do {                                                                 \
		if (!(cond)) {                                               \
			fprintf(stderr, "FAIL %s:%d: %s\n",                  \
			    __FILE__, __LINE__, #cond);                      \
			failures++;                                          \
		}                                                            \
	} while (0)

#define CHECK_STR(actual, want)                                              \
	do {                                                                 \
		const char *_a = (actual);                                   \
		if (_a == NULL || strcmp(_a, (want)) != 0)                   \
			fprintf(stderr, "FAIL %s:%d: got [%s] want [%s]\n",  \
			    __FILE__, __LINE__,                              \
			    _a ? _a : "NULL", (want)),                       \
			    failures++;                                    \
	} while (0)

static FILE *
tmpstream(char **outpath)
{
	char path[256];
	const char *dir = getenv("TMPDIR");
	snprintf(path, sizeof path, "%s/clens_test_%d.txt",
	    dir ? dir : ".", (int)getpid());
	*outpath = strdup(path);
	return fopen(path, "w+");
}

int
main(void)
{
	/* ---- clens version API ------------------------------------ */
	CHECK_STR(clens_verstring(), "0.7.0");

	int major, minor, patch;
	clens_version(&major, &minor, &patch);
	CHECK(major == 0 && minor == 7 && patch == 0);

	/* ---- strtonum ---------------------------------------------- */
	const char *err = NULL;
	CHECK(strtonum("42", 0, 100, &err) == 42 && err == NULL);
	err = NULL;
	CHECK(strtonum("101", 0, 100, &err) == 0 &&
	    err != NULL && strcmp(err, "too large") == 0);
	err = NULL;
	CHECK(strtonum("abc", 0, 100, &err) == 0 &&
	    err != NULL && strcmp(err, "invalid") == 0);

	/* ---- fmt_scaled / scan_scaled ------------------------------ */
	char buf[FMT_SCALED_STRSIZE];
	CHECK(fmt_scaled(0, buf) == 0);              CHECK_STR(buf, "0B");
	CHECK(fmt_scaled(-123456789LL, buf) == 0);   CHECK_STR(buf, "-118M");
	CHECK(fmt_scaled(2147483648LL, buf) == 0);   CHECK_STR(buf, "2.0G");

	char in[] = "2.0G";
	long long back = 0;
	errno = 0;
	CHECK(scan_scaled(in, &back) == 0 && back == 2147483648LL);
	char bad[] = "xyz";
	errno = 0;
	CHECK(scan_scaled(bad, &back) == -1 && errno == ERANGE);

	/* ---- fparseln: comments skipped, lines and numbers parsed ---- */
	char *path;
	FILE *f = tmpstream(&path);
	CHECK(f != NULL);
	if (f != NULL) {
		fputs("# comment\nfirst line\nsecond\n", f);
		fflush(f);
		rewind(f);
		size_t fl = 0, ln = 0;
		char *line = fparseln(f, &fl, &ln, NULL, 0);
		CHECK_STR(line, "first line"); CHECK(fl == 10); CHECK(ln == 2);
		free(line);
		line = fparseln(f, &fl, &ln, NULL, 0);
		CHECK_STR(line, "second"); CHECK(fl == 6); CHECK(ln == 3);
		free(line);
		line = fparseln(f, &fl, &ln, NULL, 0);
		CHECK(line == NULL);
		free(line);
		fclose(f);

		/* backslash continuation joins physical lines */
		f = fopen(path, "w+");
		fputs("aaa\\\nbbb\n", f);
		fflush(f);
		rewind(f);
		fl = 0; ln = 0;
		line = fparseln(f, &fl, &ln, NULL, 0);
		CHECK_STR(line, "aaabbb"); CHECK(fl == 6);
		free(line);
		fclose(f);
		remove(path);
		free(path);
	}

	/* ---- compat symbols served by OHOS libc (shim TUs trimmed) ---
	 * These come from the platform, not libclens.a: linking and
	 * calling them here documents and verifies the trimming rule. */
	char nb[4];
	CHECK(strlcpy(nb, "abcdef", sizeof nb) == 6);
	CHECK_STR(nb, "abc");
	CHECK(strlcat(nb, "xyz", sizeof nb) == 6);
	CHECK_STR(nb, "abc");

	CHECK(arc4random_uniform(10) < 10);

	glob_t g;
	memset(&g, 0, sizeof g);
	CHECK(glob("/nonexistent-clens-glob-*", 0, NULL, &g) == GLOB_NOMATCH);
	globfree(&g);

	if (failures != 0) {
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("clens test_package: all checks passed\n");
	return 0;
}
