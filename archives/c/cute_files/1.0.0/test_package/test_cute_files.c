/* test_cute_files.c — cute_files 1.0.0 test_package.
 *
 * Defines CUTE_FILES_IMPLEMENTATION in this single TU and exercises the
 * real public API: directory traversal (cf_dir_open/cf_read_file/
 * cf_dir_next/cf_dir_close), cf_file_exists and extension matching
 * (cf_match_ext/cf_get_ext). Asserts each result; prints per-check lines
 * and a final HMBS_TEST_PACKAGE_RESULT line.
 */
#include <stdio.h>
#include <string.h>

#define CUTE_FILES_IMPLEMENTATION
#include <cute_files.h>

static int checks = 0;
static int failures = 0;

static void check(const char* name, int cond)
{
	checks++;
	if (!cond) { failures++; printf("FAIL: %s\n", name); }
	else       { printf("PASS: %s\n", name); }
}

int main(void)
{
	/* 1. cf_file_exists on our own binary / cwd. */
	int cwd_exists = cf_file_exists(".");
	check("cf_file_exists('.')==1", cwd_exists == 1);
	int missing = cf_file_exists("this_file_does_not_exist_xyz");
	check("cf_file_exists(nonexistent)==0", missing == 0);

	/* 2. Traverse "." and collect real entries. */
	cf_dir_t dir;
	int opened = cf_dir_open(&dir, ".");
	check("cf_dir_open('.')==1", opened == 1);
	if (opened)
	{
		int count = 0;
		int saw_dot = 0;
		cf_file_t file;
		while (dir.has_next && dir.entry)
		{
			if (cf_read_file(&dir, &file))
			{
				count++;
				if (strcmp(file.name, ".") == 0) saw_dot = 1;
				if (file.ext[0])
					check("cf_match_ext(ext) ok", cf_match_ext(&file, file.ext) == 1);
			}
			cf_dir_next(&dir);
		}
		check("traverse count>0", count > 0);
		(void)saw_dot;
		cf_dir_close(&dir);
	}
	else
	{
		check("traverse entries", 0);
	}

	/* 3. Header compile sanity: known constants present. */
	check("CUTE_FILES_MAX_PATH>0", CUTE_FILES_MAX_PATH > 0);
	check("CUTE_FILES_MAX_FILENAME>0", CUTE_FILES_MAX_FILENAME > 0);

	printf("checks=%d failures=%d\n", checks, failures);
	if (failures == 0) printf("HMBS_TEST_PACKAGE_RESULT: PASS\n");
	else printf("HMBS_TEST_PACKAGE_RESULT: FAIL\n");
	return failures == 0 ? 0 : 1;
}