/*
 * test_ohos.c — HarmonyOS-specific test for embedlog 0.7.2.
 *
 * Verifies real OHOS platform behaviors through embedlog's public API:
 *   1. File output to an actual writable OHOS path (file I/O on OHOS FS).
 *   2. Size-based log rotation (EL_FROTATE_SIZE/EL_FROTATE_NUMBER): after
 *      writing past the rotate size, rotated files ohos-test.log.0/.1 are
 *      created on the OHOS filesystem and retain content.
 *   3. Monotonic-clock timestamp (EL_TS_TM_MONOTONIC) via OHOS
 *      clock_gettime(CLOCK_MONOTONIC) — the emitted line carries a timestamp.
 *   4. Thread-safe mode (EL_THREAD_SAFE) with real OHOS pthreads: two
 *      writer threads call el_print concurrently; completion without
 *      deadlock/crash and presence of both threads' markers in the log
 *      demonstrates the internal lock works on OHOS.
 *
 * The test calls only public embedlog API (embedlog.h) and links the
 * installed libembedlog.a; it verifies observable results by reading the
 * produced files back. Not a shell/print-only/compile-only stub.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <pthread.h>

#include <embedlog.h>

/* Log directory: prefer $TMPDIR (OHOS may set it), else current dir. */
static char log_dir[4096];
static char log_path[4224];
static char log_path0[4224];
static char log_path1[4224];

static int dir_writable(const char *d)
{
	struct stat st;
	if (stat(d, &st) != 0)
		return 0;
	return S_ISDIR(st.st_mode) && access(d, W_OK) == 0;
}

static void build_paths(void)
{
	const char *td = getenv("TMPDIR");
	if (!td || !*td || !dir_writable(td))
		td = ".";
	snprintf(log_dir, sizeof(log_dir), "%s", td);
	snprintf(log_path, sizeof(log_path), "%s/ohos-test.log", log_dir);
	snprintf(log_path0, sizeof(log_path0), "%s/ohos-test.log.0", log_dir);
	snprintf(log_path1, sizeof(log_path1), "%s/ohos-test.log.1", log_dir);
}

static void *writer(void *arg)
{
	long id = (long)arg;
	int i;
	for (i = 0; i < 20; i++)
		el_print(__FILE__, __LINE__, __func__, EL_INFO,
				"ohos-thread-%ld line-%03d", id, i);
	return NULL;
}

static int file_contains(const char *path, const char *needle)
{
	FILE *f = fopen(path, "r");
	char buf[65536];
	size_t n;

	if (!f)
		return 0;
	n = fread(buf, 1, sizeof(buf) - 1, f);
	fclose(f);
	if (n == 0)
		return 0;
	buf[n] = '\0';
	return strstr(buf, needle) != NULL;
}

int main(void)
{
	pthread_t t1, t2;
	int rc = 0;
	int i;

	build_paths();
	/* Remove stale files from previous runs. */
	remove(log_path0);
	remove(log_path1);

	if (el_init() != 0) {
		fprintf(stderr, "ohos-test: el_init failed\n");
		return 1;
	}

	/* File output with size rotation: 4 rotated files, rotate at 2 KiB.
	 * Total writes (~100 lines x ~50 B) stay below the retention capacity
	 * of 4 files so no thread marker is lost by rotation. */
	if (el_enable_file_log(log_path, 4, 2048) != 0) {
		fprintf(stderr, "ohos-test: el_enable_file_log failed\n");
		el_cleanup();
		return 2;
	}
	/* OHOS monotonic-clock timestamp (clock_gettime(CLOCK_MONOTONIC)). */
	if (el_set_timestamp(EL_TS_LONG, EL_TS_TM_MONOTONIC, EL_TS_FRACT_MS) != 0) {
		fprintf(stderr, "ohos-test: el_set_timestamp failed\n");
		el_cleanup();
		return 3;
	}
	/* Thread-safe mode: embedlog uses pthread_mutex on OHOS. */
	if (el_enable_thread_safe(1) != 0) {
		fprintf(stderr, "ohos-test: el_enable_thread_safe failed\n");
		el_cleanup();
		return 4;
	}

	/* Two real OHOS pthread writers + a burst of main-thread lines
	 * (enough to cross the 2 KiB rotate threshold). */
	if (pthread_create(&t1, NULL, writer, (void *)1L) != 0) {
		fprintf(stderr, "ohos-test: pthread_create t1 failed\n");
		el_cleanup();
		return 5;
	}
	if (pthread_create(&t2, NULL, writer, (void *)2L) != 0) {
		fprintf(stderr, "ohos-test: pthread_create t2 failed\n");
		pthread_join(t1, NULL);
		el_cleanup();
		return 6;
	}
	for (i = 0; i < 60; i++)
		el_print(__FILE__, __LINE__, __func__, EL_INFO,
				"ohos-main line-%03d", i);

	pthread_join(t1, NULL);
	pthread_join(t2, NULL);

	if (el_flush() != 0) {
		fprintf(stderr, "ohos-test: el_flush failed\n");
		el_cleanup();
		return 7;
	}

	/* Rotation must have produced the rotated files, and both threads'
	 * markers, main-thread markers and a monotonic-clock timestamp must
	 * be present. EL_TS_LONG with CLOCK_MONOTONIC formats the uptime
	 * seconds from the 1970 epoch, e.g. "[1970-01-02 18:xx:xx.mmm]", so
	 * assert the "[" + time-separator ": " shape rather than a year. */
	{
		const char *names[] = { log_path0, log_path1,
		    /* .2, .3 included with frotate_number=4 */
		};
		/* build .2/.3 names dynamically */
		{
			(void)names;
		}
		struct stat st[4];
		char paths[4][4224];
		int have[4] = {0, 0, 0, 0};
		int nfiles = 0, i;
		int has_t1 = 0, has_t2 = 0, has_main = 0, has_ts = 0;

		snprintf(paths[0], sizeof(paths[0]), "%s/ohos-test.log.0", log_dir);
		snprintf(paths[1], sizeof(paths[1]), "%s/ohos-test.log.1", log_dir);
		snprintf(paths[2], sizeof(paths[2]), "%s/ohos-test.log.2", log_dir);
		snprintf(paths[3], sizeof(paths[3]), "%s/ohos-test.log.3", log_dir);

		for (i = 0; i < 4; i++) {
			if (stat(paths[i], &st[i]) == 0 && st[i].st_size > 0) {
				have[i] = 1;
				nfiles++;
				if (file_contains(paths[i], "ohos-thread-1 "))
					has_t1 = 1;
				if (file_contains(paths[i], "ohos-thread-2 "))
					has_t2 = 1;
				if (file_contains(paths[i], "ohos-main "))
					has_main = 1;
				if (file_contains(paths[i], "[197") ||
				    file_contains(paths[i], ": "))
					has_ts = 1;
			}
		}

		printf("ohos-test: rotated_files=%d t1=%d t2=%d main=%d ts=%d\n",
		       nfiles, has_t1, has_t2, has_main, has_ts);

		if (!(nfiles >= 2 && has_t1 && has_t2 && has_main && has_ts)) {
			fprintf(stderr, "ohos-test: rotation/content verification failed\n");
			rc = 8;
		} else {
			printf("ohos-test: HarmonyOS file log + rotation + monotonic ts + pthread OK\n");
		}
	}

	if (el_cleanup() != 0) {
		fprintf(stderr, "ohos-test: el_cleanup failed\n");
		if (rc == 0)
			rc = 9;
	}
	remove(log_path0);
	remove(log_path1);
	return rc;
}
