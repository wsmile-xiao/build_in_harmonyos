/* Consumer test for libzahl 1.0: exercises real library APIs.
 * 6 checks: add, mul, sub, powu, gcd, string round-trip + comparison.
 * Returns 0 only if all checks pass; prints the verified values so the
 * harness output proves the library really ran (no silent pass).
 */
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include <zahl.h>

int main(void)
{
	static z_t a, b, c;
	static char buf[1024];
	static jmp_buf env;

	if (setjmp(env)) {
		printf("libzahl error: longjmp taken\n");
		return 1;
	}
	zsetup(env);
	zinit(a);
	zinit(b);
	zinit(c);

	/* 1. addition: 12345 + 67890 = 80235 */
	zsets(a, "12345");
	zsets(b, "67890");
	zadd(c, a, b);
	if (strcmp(zstr(c, buf), "80235") != 0) {
		printf("add failed: got %s\n", zstr(c, buf));
		return 2;
	}
	printf("check1 add passed: 12345+67890=%s\n", buf);

	/* 2. multiplication: 123 * 456 = 56088 */
	zsets(a, "123");
	zsets(b, "456");
	zmul(c, a, b);
	if (strcmp(zstr(c, buf), "56088") != 0) {
		printf("mul failed: got %s\n", zstr(c, buf));
		return 3;
	}
	printf("check2 mul passed: 123*456=%s\n", buf);

	/* 3. subtraction: 100 - 58 = 42 */
	zsets(a, "100");
	zsets(b, "58");
	zsub(c, a, b);
	if (strcmp(zstr(c, buf), "42") != 0) {
		printf("sub failed: got %s\n", zstr(c, buf));
		return 4;
	}
	printf("check3 sub passed: 100-58=%s\n", buf);

	/* 4. power: 2^10 = 1024 */
	zsetu(b, 2);
	zpowu(c, b, 10);
	if (strcmp(zstr(c, buf), "1024") != 0) {
		printf("powu failed: got %s\n", zstr(c, buf));
		return 5;
	}
	printf("check4 powu passed: 2^10=%s\n", buf);

	/* 5. gcd: gcd(54, 24) = 6 */
	zsets(a, "54");
	zsets(b, "24");
	zgcd(c, a, b);
	if (strcmp(zstr(c, buf), "6") != 0) {
		printf("gcd failed: got %s\n", zstr(c, buf));
		return 6;
	}
	printf("check5 gcd passed: gcd(54,24)=%s\n", buf);

	/* 6. string round-trip + comparison: -987654321 < 0 */
	zsets(a, "-987654321");
	if (strcmp(zstr(a, buf), "-987654321") != 0) {
		printf("str failed: got %s\n", buf);
		return 7;
	}
	zsets(b, "0");
	if (!(zcmp(a, b) < 0)) {
		printf("cmp failed\n");
		return 7;
	}
	printf("check6 str/cmp passed: %s < 0\n", buf);

	zfree(a);
	zfree(b);
	zfree(c);
	zunsetup();
	puts("libzahl consumer checks passed: 6/6");
	return 0;
}
