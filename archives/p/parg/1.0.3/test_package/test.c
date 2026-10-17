/*
 * test_parg — test_package consumer checks for parg 1.0.3
 *
 * 每个 argv[1] 选择一个消费者用例；test_package/CMakeLists.txt 把它们注册成
 * 独立的 CTest 条目（计数可审计，对应 PR 正文「鸿蒙特有测试」行）。
 * 断言直接走已安装的 parg 制品（find_package(parg) → parg::parg）。
 */
#include <stdio.h>
#include <string.h>

#include "parg.h"

static const char *os_def = ":no::r:";

static const struct parg_option po_def[] = {
	{ "noarg", PARG_NOARG, NULL, 'n' },
	{ "optarg", PARG_OPTARG, NULL, 'o' },
	{ "reqarg", PARG_REQARG, NULL, 'r' },
	{ 0, 0, 0, 0 }
};

static int failures;

static void
check_int(int expected, int actual, const char *what)
{
	if (expected != actual) {
		fprintf(stderr, "FAIL: %s: expected %d, got %d\n", what, expected,
		    actual);
		failures++;
	}
}

static void
check_str(const char *expected, const char *actual, const char *what)
{
	if (actual == NULL || strcmp(expected, actual) != 0) {
		fprintf(stderr, "FAIL: %s: expected \"%s\", got \"%s\"\n", what,
		    expected, actual == NULL ? "(null)" : actual);
		failures++;
	}
}

/* 版本宏 + parg_init 初始状态（消费方可见的 ABI 面） */
static int
case_link(void)
{
	struct parg_state ps;

	check_int(1, PARG_VER_MAJOR, "PARG_VER_MAJOR");
	check_int(0, PARG_VER_MINOR, "PARG_VER_MINOR");
	check_int(3, PARG_VER_PATCH, "PARG_VER_PATCH");
	check_str("1.0.3", PARG_VER_STRING, "PARG_VER_STRING");

	parg_init(&ps);
	check_int(NULL == ps.optarg, 1, "parg_init optarg==NULL");
	check_int(1, ps.optind, "parg_init optind==1");
	check_int('?', ps.optopt, "parg_init optopt=='?'");
	check_int(NULL == ps.nextchar, 1, "parg_init nextchar==NULL");

	return failures;
}

/* 短选项解析：flag / 必需参数 / 可选参数 */
static int
case_short(void)
{
	struct parg_state ps;
	char *argv[] = { "app", "-n", "-r", "val", "-oinline" };

	parg_init(&ps);

	check_int('n', parg_getopt(&ps, 5, argv, os_def), "first -n");
	check_int(NULL == ps.optarg, 1, "-n takes no argument");
	check_int(2, ps.optind, "optind after -n");

	check_int('r', parg_getopt(&ps, 5, argv, os_def), "-r");
	check_str("val", ps.optarg, "-r consumes next argv element");
	check_int(4, ps.optind, "optind after -r val");

	check_int('o', parg_getopt(&ps, 5, argv, os_def), "-o inline arg");
	check_str("inline", ps.optarg, "-oinline inline argument");
	check_int(5, ps.optind, "optind after -oinline");

	check_int(-1, parg_getopt(&ps, 5, argv, os_def), "end of argv");

	return failures;
}

/* 长选项解析：inline 参数、必需参数缺失、前缀消歧 */
static int
case_long(void)
{
	struct parg_state ps;
	char *argv[] = { "app", "--reqarg=val", "--noarg", "--req=other",
	    "--reqarg" };
	int li = -1;

	parg_init(&ps);

	check_int('r', parg_getopt_long(&ps, 5, argv, ":", po_def, &li),
	    "--reqarg=val");
	check_int(2, li, "long index for reqarg");
	check_str("val", ps.optarg, "--reqarg inline value");
	check_int(2, ps.optind, "optind after --reqarg=val");

	check_int('n', parg_getopt_long(&ps, 5, argv, ":", po_def, &li),
	    "--noarg");
	check_int(0, li, "long index for noarg");
	check_int(3, ps.optind, "optind after --noarg");

	check_int('r', parg_getopt_long(&ps, 5, argv, ":", po_def, &li),
	    "--req unambiguous prefix");
	check_str("other", ps.optarg, "--req=other inline value");
	check_int(2, li, "long index via prefix");

	check_int(':', parg_getopt_long(&ps, 5, argv, ":", po_def, &li),
	    "trailing --reqarg without value rejected");
	check_int('r', ps.optopt, "optopt for missing argument");
	check_int(5, ps.optind, "optind after rejected element");

	check_int(-1, parg_getopt_long(&ps, 5, argv, ":", po_def, &li),
	    "end of argv");

	return failures;
}

/* parg_reorder：非选项参数后置，选项与 -- 分隔符保持顺序 */
static int
case_reorder(void)
{
	char *argv[] = { "app", "first", "-r", "--", "foo", "-u", "bar",
	    "-o", "--", "-n", "last" };
	char *expected[] = { "app", "-r", "--", "-u", "-o", "--", "first",
	    "foo", "bar", "-n", "last" };
	size_t i;

	check_int(6, parg_reorder(11, argv, os_def, NULL),
	    "parg_reorder return value");
	for (i = 0; i < 11; ++i) {
		check_str(expected[i], argv[i], "reordered argv element");
	}

	return failures;
}

int
main(int argc, char **argv)
{
	const char *which = argc > 1 ? argv[1] : "";

	if (strcmp(which, "link") == 0) {
		failures = case_link();
	} else if (strcmp(which, "short") == 0) {
		failures = case_short();
	} else if (strcmp(which, "long") == 0) {
		failures = case_long();
	} else if (strcmp(which, "reorder") == 0) {
		failures = case_reorder();
	} else {
		fprintf(stderr, "usage: %s link|short|long|reorder\n", argv[0]);
		return 2;
	}

	printf("parg consumer check '%s': %s (failures=%d)\n", which,
	    failures == 0 ? "PASS" : "FAIL", failures);
	return failures == 0 ? 0 : 1;
}
