/*
 * VISAM 消费者用例（OpenHarmony 适配验证）。
 *
 * 目的：以"消费方"身份、仅通过公开头文件 <visam.h>（它已包含 vdecimal.h）与公开 API
 * 验证已发布包是否可用，覆盖两条对 OHOS 适配最关键的路径：
 *
 *   1) ISAM 文件完整生命周期：iserase -> isbuild -> isaddindex -> iswrite
 *      -> isread(ISFIRST/ISNEXT) -> isfullclose，并校验写入/读回记录数一致。
 *   2) 十进制转换：deccvdbl()/dectodbl()。这两个 API 走 libvisam/isdecimal.c
 *      的 deccvreal()，是本包在 OHOS 上唯一需要补 ecvt(3) 的调用链
 *      （musl libc 不提供 glibc 扩展 ecvt），因此必须由消费者用例真实跑到。
 *
 * 任何一步失败立即返回非 0，并由 test_package/conanfile.py 的 test() 执行。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* 注意：vdecimal.h 没有 include guard，且已被 visam.h 包含，
   消费方只需包含 <visam.h>（重复包含 vdecimal.h 会导致 struct decimal 重定义）。 */
#include <visam.h>

#define RECLEN      63
#define NRECORDS    200
#define DBFILE      "visam_consumer_db"

static int failures;

static void
check (int condition, const char *what)
{
	printf ("[%s] %s\n", condition ? "PASS" : "FAIL", what);
	if (!condition) {
		failures++;
	}
}

static int
test_decimal (void)
{
	dec_t       d;
	double      back = 0.0;
	const double value = 1234.5678;

	if (deccvdbl (value, &d) != 0) {
		printf ("[FAIL] deccvdbl(%f) 返回非 0\n", value);
		failures++;
		return -1;
	}
	if (dectodbl (&d, &back) != 0) {
		printf ("[FAIL] dectodbl() 返回非 0\n");
		failures++;
		return -1;
	}
	printf ("[INFO] decimal round-trip: %.4f -> %.4f\n", value, back);
	check (fabs (back - value) < 0.01,
		   "deccvdbl/dectodbl 往返精度（覆盖 ecvt 兼容垫片）");

	return 0;
}

static int
test_isam (void)
{
	struct keydesc key1;
	struct keydesc key2;
	int         handle;
	int         written = 0;
	int         readback = 0;
	int         i;
	char        record[RECLEN + 1];

	memset (&key1, 0, sizeof (key1));
	key1.k_flags = ISNODUPS;
	key1.k_nparts = 1;
	key1.k_start = 0;
	key1.k_leng = 5;
	key1.k_type = CHARTYPE;

	memset (&key2, 0, sizeof (key2));
	key2.k_flags = ISDUPS;
	key2.k_nparts = 1;
	key2.k_start = 23;
	key2.k_leng = 3;
	key2.k_type = CHARTYPE;

	iserase ((VB_CHAR *) DBFILE);

	handle = isbuild ((VB_CHAR *) DBFILE, RECLEN, &key1,
					  ISINOUT + ISFIXLEN + ISEXCLLOCK);
	if (handle < 0) {
		printf ("[FAIL] isbuild 失败, iserrno=%d\n", iserrno);
		failures++;
		return -1;
	}

	if (isaddindex (handle, &key2) != 0) {
		printf ("[FAIL] isaddindex 失败, iserrno=%d\n", iserrno);
		failures++;
		isfullclose (handle);
		return -1;
	}

	for (i = 0; i < NRECORDS; i++) {
		memset (record, ' ', RECLEN);
		snprintf (record, 4, "%03d", i);
		record[RECLEN] = '\0';
		if (iswrite (handle, (VB_CHAR *) record) != 0) {
			printf ("[FAIL] iswrite 第 %d 条失败, iserrno=%d\n", i, iserrno);
			failures++;
			break;
		}
		written++;
	}

	memset (record, ' ', RECLEN);
	record[RECLEN] = '\0';
	if (isread (handle, (VB_CHAR *) record, ISFIRST) == 0) {
		readback++;
		while (isread (handle, (VB_CHAR *) record, ISNEXT) == 0) {
			readback++;
		}
	}

	isfullclose (handle);

	printf ("[INFO] ISAM: written=%d readback=%d\n", written, readback);
	check (written == NRECORDS, "iswrite 写入全部记录");
	check (readback == NRECORDS, "isread(ISFIRST/ISNEXT) 顺序读回全部记录");

	return 0;
}

int
main (void)
{
	printf ("VISAM consumer test (visam %s)\n", "2.2");

	test_decimal ();
	test_isam ();

	/* 清理临时数据库 */
	iserase ((VB_CHAR *) DBFILE);

	if (failures != 0) {
		printf ("RESULT: %d FAILURE(S)\n", failures);
		return 1;
	}
	printf ("RESULT: OK\n");
	return 0;
}
