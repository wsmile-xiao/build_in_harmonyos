/**
 * test_snaphu.c — consumer-driven end-to-end verification for snaphu 2.0.7.
 *
 * snaphu is a CLI application (there is no library to link against), so this
 * driver receives the path of the installed `snaphu` executable as argv[1]
 * and drives the real binary:
 *
 *   1. `snaphu -hv`              -> exit 0, version banner and usage text
 *   2. all-zero 16x16 phase grid -> known answer: every unwrapped sample is
 *                                   exactly 0 and the output is R*C*4 bytes
 *   3. wrapped ramp 16x16        -> exit 0, same artefact size, all samples
 *                                   finite, output differs from the wrapped
 *                                   input and is not a constant field, and
 *                                   the run reports "Program snaphu done"
 *
 * Exit code is 0 only when every assertion passes.
 */
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define ROWS 16
#define COLS 16
#define NCELL (ROWS * COLS)

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int g_checks;
static int g_failures;

static void check(int ok, const char *what)
{
	g_checks++;
	if (ok) {
		printf("ok   %d - %s\n", g_checks, what);
	}
	else {
		g_failures++;
		printf("FAIL %d - %s\n", g_checks, what);
	}
}

static long file_size(const char *path)
{
	struct stat st;

	return stat(path, &st) == 0 ? (long)st.st_size : -1;
}

static int read_text(const char *path, char *buf, size_t cap)
{
	FILE *f = fopen(path, "rb");
	size_t n;

	if (!f)
		return -1;

	n = fread(buf, 1, cap - 1, f);
	buf[n] = '\0';
	(void)fclose(f);

	return (int)n;
}

static int write_phase(const char *path, const float *v)
{
	FILE *f = fopen(path, "wb");
	size_t n;

	if (!f)
		return -1;

	n = fwrite(v, sizeof(float), NCELL, f);
	(void)fclose(f);

	return n == NCELL ? 0 : -1;
}

static int read_phase(const char *path, float *v)
{
	FILE *f = fopen(path, "rb");
	size_t n;

	if (!f)
		return -1;

	n = fread(v, sizeof(float), NCELL, f);
	(void)fclose(f);

	return n == NCELL ? 0 : -1;
}

/* Run `cmd` and capture its combined output into `log`; return the exit code. */
static int run_cli(const char *cmd, const char *log)
{
	char full[4096];
	int rc;

	snprintf(full, sizeof(full), "%s > %s 2>&1", cmd, log);
	rc = system(full);
	if (rc == -1 || !WIFEXITED(rc))
		return -1;

	return WEXITSTATUS(rc);
}

int main(int argc, char **argv)
{
	const char *bin;
	char cmd[4096];
	char out[8192];
	float *in;
	float *res;
	int i;
	int rc;
	long want = (long)NCELL * (long)sizeof(float);

	if (argc < 2) {
		fprintf(stderr, "usage: %s <path-to-snaphu>\n", argv[0]);
		return 2;
	}
	bin = argv[1];

	if (mkdir("consumer_work", 0755) != 0 && errno != EEXIST) {
		perror("mkdir consumer_work");
		return 2;
	}
	if (chdir("consumer_work") != 0) {
		perror("chdir consumer_work");
		return 2;
	}

	in = (float *)malloc(sizeof(float) * NCELL);
	res = (float *)malloc(sizeof(float) * NCELL);
	if (!in || !res)
		return 2;

	/* --- 1. version banner and usage ------------------------------------ */
	snprintf(cmd, sizeof(cmd), "'%s' -hv", bin);
	rc = run_cli(cmd, "ver.log");
	/* Upstream prints the banner/usage and exits 1 because no infile was
	   given; the exit status is part of the observed CLI contract. */
	check(rc == 1, "snaphu -hv prints usage and exits 1 (missing infile)");
	check(read_text("ver.log", out, sizeof(out)) > 0
	      && strstr(out, "snaphu v2.0.7") != NULL,
	      "snaphu -hv prints the version banner 'snaphu v2.0.7'");
	check(strstr(out, "usage:") != NULL, "snaphu -hv prints the usage text");

	/* --- 2. known answer: zero wrapped phase unwraps to all zeros ------- */
	for (i = 0; i < NCELL; i++)
		in[i] = 0.0f;
	check(write_phase("zero.flt", in) == 0, "wrote the 16x16 zero-phase input");

	snprintf(cmd, sizeof(cmd), "'%s' zero.flt %d -o zero_out.flt -d",
		 bin, COLS);
	rc = run_cli(cmd, "zero.log");
	check(rc == 0, "snaphu unwraps the zero-phase grid (exit 0)");
	check(file_size("zero_out.flt") == want,
	      "zero-phase output has exactly R*C*4 bytes");
	if (read_phase("zero_out.flt", res) == 0) {
		int all_zero = 1;

		for (i = 0; i < NCELL; i++) {
			if (res[i] != 0.0f)
				all_zero = 0;
		}
		check(all_zero, "known answer: every unwrapped sample is exactly 0");
	}
	else {
		check(0, "zero-phase output is readable as float32");
	}

	/* --- 3. wrapped ramp: the tool really processes the grid ------------ */
	for (i = 0; i < NCELL; i++) {
		double ph = 2.0 * M_PI
			* (0.5 * (i % COLS) / COLS + 0.25 * (i / COLS) / ROWS);
		double wrapped = fmod(ph + M_PI, 2.0 * M_PI) - M_PI;

		in[i] = (float)wrapped;
	}
	check(write_phase("ramp.flt", in) == 0, "wrote the 16x16 wrapped-ramp input");

	snprintf(cmd, sizeof(cmd), "'%s' ramp.flt %d -o ramp_out.flt -d",
		 bin, COLS);
	rc = run_cli(cmd, "ramp.log");
	check(rc == 0, "snaphu unwraps the wrapped ramp (exit 0)");
	check(file_size("ramp_out.flt") == want,
	      "ramp output has exactly R*C*4 bytes");
	if (read_text("ramp.log", out, sizeof(out)) > 0) {
		check(strstr(out, "Program snaphu done") != NULL,
		      "the run reports 'Program snaphu done'");
	}
	else {
		check(0, "the run produced a log");
	}
	if (read_phase("ramp_out.flt", res) == 0) {
		int finite = 1;
		int differs = 0;
		int degenerate = 1;

		for (i = 0; i < NCELL; i++) {
			if (!isfinite(res[i]))
				finite = 0;
			if (res[i] != in[i])
				differs = 1;
			if (res[i] != res[0])
				degenerate = 0;
		}
		check(finite, "every unwrapped sample is finite");
		check(differs, "the unwrapped result differs from the wrapped input");
		check(!degenerate, "the unwrapped result is not a constant field");
	}
	else {
		check(0, "ramp output is readable as float32");
	}

	printf("\n%d checks, %d failures\n", g_checks, g_failures);

	return g_failures == 0 ? 0 : 1;
}
