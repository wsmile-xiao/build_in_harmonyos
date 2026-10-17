/* SPDX-License-Identifier: LGPL-2.1
 *
 * 消费者测试：只链接 libtracecmd，验证包的导出面。
 *
 * libtracecmd 的公开头 trace-cmd.h 里是 #include "event-parse.h" / "tracefs.h"，
 * 而 libtraceevent / libtracefs 是构建期输入（制品仓未发布）并被整体静态链入本库，
 * 因此这里刻意只 -ltracecmd 也要能拿到 tep_* / tracefs_* 符号——这正是本包在
 * HarmonyOS PC 上的交付形态是否可用的判据。
 */
#include <stdio.h>
#include <string.h>

#include <trace-cmd/trace-cmd.h>

static int checks;
static int failures;

#define CHECK(cond, desc)						\
	do {								\
		checks++;						\
		if (cond) {						\
			printf("ok %d - %s\n", checks, desc);		\
		} else {						\
			failures++;					\
			printf("FAIL %d - %s\n", checks, desc);		\
		}							\
	} while (0)

#define CHECK_STR_EQ(got, want, desc)					\
	do {								\
		const char *g_ = (got);					\
		checks++;						\
		if (g_ && strcmp(g_, (want)) == 0) {			\
			printf("ok %d - %s\n", checks, desc);		\
		} else {						\
			failures++;					\
			printf("FAIL %d - %s (got %s)\n", checks, desc,	\
			       g_ ? g_ : "(null)");			\
		}							\
	} while (0)

/* 打开不存在的 trace 文件必须干净地失败，而不是崩在解析器里。 */
static void test_open_failures(void)
{
	struct tracecmd_input *handle;

	handle = tracecmd_open("__ltc_no_such_file__.dat", 0);
	CHECK(handle == NULL, "tracecmd_open() on a missing file returns NULL");
	if (handle)
		tracecmd_close(handle);

	handle = tracecmd_open_head("__ltc_no_such_file__.dat", 0);
	CHECK(handle == NULL, "tracecmd_open_head() on a missing file returns NULL");
	if (handle)
		tracecmd_close(handle);

	handle = tracecmd_open("/proc/self/cmdline", 0);
	CHECK(handle == NULL, "tracecmd_open() rejects a file that is not a trace");
	if (handle)
		tracecmd_close(handle);
}

/* 链入的 libtraceevent 必须随 libtracecmd 一起导出。 */
static void test_tep_through_libtracecmd(void)
{
	char buf[128];
	struct tep_handle *tep;
	const char *comm;

	tep = tep_alloc();
	CHECK(tep != NULL, "tep_alloc() resolves and returns a handle");
	if (!tep)
		return;

	CHECK(tep_get_ref(tep) == 1, "fresh handle has one reference");

	tep_set_long_size(tep, 8);
	CHECK(tep_get_long_size(tep) == 8, "tep_set_long_size()/get round trip");

	tep_set_page_size(tep, 4096);
	CHECK(tep_get_page_size(tep) == 4096, "tep_set_page_size()/get round trip");

	CHECK(tep_register_comm(tep, "ltc-consumer", 4242) == 0,
	      "tep_register_comm() accepts a mapping");
	comm = tep_data_comm_from_pid(tep, 4242);
	CHECK_STR_EQ(comm, "ltc-consumer", "tep_data_comm_from_pid() returns it back");
	CHECK_STR_EQ(tep_data_comm_from_pid(tep, 999999), "<...>",
		     "unknown pid falls back to the placeholder comm");
	CHECK_STR_EQ(tep_data_comm_from_pid(tep, 0), "<idle>",
		     "pid 0 reports the idle comm");

	CHECK(tep_test_flag(tep, TEP_NSEC_OUTPUT) == false,
	      "TEP_NSEC_OUTPUT is clear by default");
	tep_set_flag(tep, TEP_NSEC_OUTPUT);
	CHECK(tep_test_flag(tep, TEP_NSEC_OUTPUT) == true, "tep_set_flag() sets it");
	tep_clear_flag(tep, TEP_NSEC_OUTPUT);
	CHECK(tep_test_flag(tep, TEP_NSEC_OUTPUT) == false, "tep_clear_flag() clears it");

	buf[0] = '\0';
	CHECK(tep_strerror(tep, TEP_ERRNO__MEM_ALLOC_FAILED, buf, sizeof(buf)) == 0,
	      "tep_strerror() maps an errno");
	CHECK_STR_EQ(buf, "failed to allocate memory", "tep_strerror() text matches header");

	tep_free(tep);
}

/* 链入的 libtracefs 同上；且这些用例不得依赖 root 权限。 */
static void test_tracefs_through_libtracecmd(void)
{
	char **list = NULL;
	char *path;

	list = tracefs_list_add(list, "alpha");
	CHECK(list != NULL, "tracefs_list_add() starts a list");
	CHECK(tracefs_list_size(list) == 1, "list holds one entry");

	list = tracefs_list_add(list, "beta");
	CHECK(tracefs_list_size(list) == 2, "list grows to two entries");
	CHECK(list && list[0] && strcmp(list[0], "alpha") == 0, "first entry keeps order");
	CHECK(list && list[1] && strcmp(list[1], "beta") == 0, "second entry appended");
	CHECK(list && list[2] == NULL, "list stays NULL terminated");
	tracefs_list_free(list);

	path = tracefs_get_tracing_file("trace");
	CHECK(path != NULL, "tracefs_get_tracing_file() builds a path");
	CHECK(path && strstr(path, "/trace") != NULL, "path ends in the requested file name");
	tracefs_put_tracing_file(path);

	CHECK(tracefs_event_systems("__ltc_no_such_dir__") == NULL,
	      "tracefs_event_systems() fails cleanly on a bad directory");
	CHECK(tracefs_instance_exists("__ltc_no_such_instance__") == false,
	      "tracefs_instance_exists() reports a missing instance as absent");
}

int main(void)
{
	printf("# libtracecmd consumer test on HarmonyOS PC\n");
	test_open_failures();
	test_tep_through_libtracecmd();
	test_tracefs_through_libtracecmd();
	printf("# Run Summary: checks %d, passed %d, failed %d\n",
	       checks, checks - failures, failures);
	fflush(stdout);
	return failures ? 1 : 0;
}
