#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#include <lastlog2.h>

static int failures = 0;

#define CHECK(cond, msg)                                                   \
	do {                                                               \
		if (!(cond)) {                                             \
			fprintf(stderr, "FAIL: %s\n", msg);                \
			failures++;                                        \
		} else {                                                   \
			printf("PASS: %s\n", msg);                         \
		}                                                          \
	} while (0)

int main(void)
{
	struct ll2_context *ctx;
	char *error = NULL;
	int64_t login_time = (int64_t)1712345678;
	int64_t read_time = 0;
	char *tty = NULL;
	char *rhost = NULL;
	char *service = NULL;
	int ret;

	ctx = ll2_new_context("lastlog2_consumer_test.db");
	CHECK(ctx != NULL, "ll2_new_context");
	if (ctx == NULL)
		return 1;

	ret = ll2_write_entry(ctx, "ohostest", login_time, "pts/0",
			      "192.168.122.1", "sshd", &error);
	CHECK(ret == 0, "ll2_write_entry");

	ret = ll2_read_entry(ctx, "ohostest", &read_time, &tty, &rhost,
			     &service, &error);
	CHECK(ret == 0, "ll2_read_entry after write");
	CHECK(read_time == login_time, "ll_time roundtrip");
	CHECK(tty != NULL && strcmp(tty, "pts/0") == 0, "tty roundtrip");
	CHECK(rhost != NULL && strcmp(rhost, "192.168.122.1") == 0,
	      "rhost roundtrip");

	ret = ll2_rename_user(ctx, "ohostest", "ohostest2", &error);
	CHECK(ret == 0, "ll2_rename_user");

	ret = ll2_read_entry(ctx, "ohostest2", &read_time, &tty, &rhost,
			     &service, &error);
	CHECK(ret == 0 && read_time == login_time,
	      "ll2_read_entry after rename");

	ret = ll2_remove_entry(ctx, "ohostest2", &error);
	CHECK(ret == 0, "ll2_remove_entry");

	/* this needs to fail, as the entry should not exist anymore */
	ret = ll2_read_entry(ctx, "ohostest2", &read_time, &tty, &rhost,
			     &service, &error);
	CHECK(ret != 0, "ll2_read_entry of removed entry fails");

	ll2_unref_context(ctx);
	free(error);
	free(tty);
	free(rhost);
	free(service);
	remove("lastlog2_consumer_test.db");

	if (failures != 0) {
		fprintf(stderr, "%d check(s) failed\n", failures);
		return 1;
	}
	printf("ALL CHECKS PASSED\n");
	return 0;
}
