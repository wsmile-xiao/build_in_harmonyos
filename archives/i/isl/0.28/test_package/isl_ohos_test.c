/*
 * isl_ohos_test.c — HarmonyOS 专项测试
 *
 * 目的：验证 isl 0.28 在 HarmonyOS PC (aarch64) 平台上的适配正确性。
 * 本库适配采用 --with-int=imath（内建多精度整数实现，规避系统无 gmp.h 的问题），
 * 因此本测试重点验证 imath 后端的大整数运算（超出 64 位范围）与集合/映射
 * 基础操作的公开 API 行为，确保跨平台可复现、结果可断言。
 *
 * 仅使用已安装的公开头文件与公开 API（isl/ctx.h、isl/val.h、isl/set.h、isl/map.h）。
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <isl/ctx.h>
#include <isl/val.h>
#include <isl/set.h>
#include <isl/map.h>
#include <isl/version.h>

/* 用例 1：大整数乘法（128 位以上），验证 imath 后端多精度正确性。
 * 从 1 连乘 100 次 2 得 2^100；2^100 * 2^100 == 2^200。
 * 2^200 = 1606938044258990275541962092341162602522202993782792835301376 */
static int test_big_int_mul(isl_ctx *ctx)
{
	isl_val *v, *w, *r, *expected;
	int ok;

	v = isl_val_int_from_ui(ctx, 1);
	for (int i = 0; i < 100; ++i)
		v = isl_val_mul_ui(v, 2);
	w = isl_val_int_from_ui(ctx, 1);
	for (int i = 0; i < 100; ++i)
		w = isl_val_mul_ui(w, 2);
	r = isl_val_mul(v, w);

	expected = isl_val_int_from_ui(ctx, 1);
	for (int i = 0; i < 200; ++i)
		expected = isl_val_mul_ui(expected, 2);

	ok = isl_val_eq(r, expected);
	printf("[isl_ohos] big-int mul: 2^100 * 2^100 == 2^200 -> %s\n",
	       ok ? "PASS" : "FAIL");
	if (!ok)
		printf("[isl_ohos]   r = %s, expected = %s\n",
		       isl_val_to_str(r), isl_val_to_str(expected));

	isl_val_free(expected);
	isl_val_free(r);
	return ok ? 0 : 1;
}

/* 用例 2：GCD 运算（欧几里得算法经由 imath 后端） */
static int test_gcd(isl_ctx *ctx)
{
	isl_val *a, *b, *g, *expected;
	int ok;

	a = isl_val_int_from_ui(ctx, 1071);
	b = isl_val_int_from_ui(ctx, 462);
	g = isl_val_gcd(a, b);

	/* gcd(1071, 462) = 21 */
	expected = isl_val_int_from_ui(ctx, 21);
	ok = isl_val_eq(g, expected);
	printf("[isl_ohos] gcd(1071, 462) == 21 -> %s\n", ok ? "PASS" : "FAIL");
	if (!ok)
		printf("[isl_ohos]   g = %s\n", isl_val_to_str(g));

	isl_val_free(expected);
	isl_val_free(g);
	return ok ? 0 : 1;
}

/* 用例 3：集合解析与基数（公开 isl_set API） */
static int test_set_card(isl_ctx *ctx)
{
	isl_set *s;
	isl_val *card, *expected;
	int ok;
	const char *str = "{ [i] : 0 <= i < 7 }";

	s = isl_set_read_from_str(ctx, str);
	assert(s);
	card = isl_set_count_val(s);
	/* { i : 0 <= i < 7 } 基数为 7 */
	expected = isl_val_int_from_ui(ctx, 7);
	ok = isl_val_eq(card, expected);
	printf("[isl_ohos] card({ i : 0 <= i < 7 }) == 7 -> %s\n",
	       ok ? "PASS" : "FAIL");
	if (!ok)
		printf("[isl_ohos]   card = %s\n", isl_val_to_str(card));

	isl_val_free(expected);
	isl_val_free(card);
	isl_set_free(s);
	return ok ? 0 : 1;
}

/* 用例 4：映射解析与合成（公开 isl_map API） */
static int test_map_compose(isl_ctx *ctx)
{
	isl_map *m1, *m2, *m;
	int ok;

	m1 = isl_map_read_from_str(ctx, "{ [i] -> [i + 1] }");
	m2 = isl_map_read_from_str(ctx, "{ [j] -> [2 * j] }");
	assert(m1 && m2);
	m = isl_map_apply_range(m1, m2);
	/* { [i] -> [2 * (i + 1)] }，点 [3] 映到 [8] */
	{
		isl_map *check = isl_map_read_from_str(ctx, "{ [3] -> [8] }");
		ok = isl_map_is_subset(check, m);
		printf("[isl_ohos] apply_range { [i]->[i+1]; [j]->[2j] } maps 3->8 -> %s\n",
		       ok ? "PASS" : "FAIL");
		if (!ok)
			printf("[isl_ohos]   m = %s\n", isl_map_to_str(m));
		isl_map_free(check);
	}

	isl_map_free(m);
	return ok ? 0 : 1;
}

/* 用例 5：版本号公开 API（isl/version.h，configure 生成，含后端标识） */
static int test_version(isl_ctx *ctx)
{
	const char *ver = isl_version();
	int ok = ver != NULL && strstr(ver, "0.28") != NULL;
	printf("[isl_ohos] isl_version() contains 0.28 -> %s (got %s)\n",
	       ok ? "PASS" : "FAIL", ver ? ver : "(null)");
	(void)ctx;
	return ok ? 0 : 1;
}

int main(void)
{
	isl_ctx *ctx;
	int failed = 0;

	ctx = isl_ctx_alloc();
	assert(ctx);

	failed += test_big_int_mul(ctx);
	failed += test_gcd(ctx);
	failed += test_set_card(ctx);
	failed += test_map_compose(ctx);
	failed += test_version(ctx);

	isl_ctx_free(ctx);

	if (failed == 0) {
		printf("[isl_ohos] ALL 5 HarmonyOS-specific checks PASSED\n");
		return 0;
	}
	printf("[isl_ohos] %d check(s) FAILED\n", failed);
	return 1;
}
