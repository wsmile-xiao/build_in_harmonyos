/*
 * libjwt 消费者测试（test_package）— 真实调用 libjwt 公开 API。
 *
 * 覆盖：JWKS 载入 → 取 JWK → HS256 签发 → 校验通过 → 篡改后校验失败（负样本）。
 * 不引入 libcheck（test_package 不应依赖测试框架），自带轻量断言宏。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <jwt.h>

/* HS256 对称密钥（与上游 tests/keys/oct_key_256.json 同值） */
static const char *JWKS_HS256 =
	"{\"keys\":[{\"kty\":\"oct\",\"alg\":\"HS256\","
	"\"k\":\"0gmNspkRljssLSrldySnYUS-zhtCo5sqeqo_yl7n2XA\"}]}";

static int failures;

#define CHECK(cond, msg)						\
	do {								\
		if (!(cond)) {						\
			fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__);	\
			failures++;					\
		} else {						\
			printf("ok: %s\n", (msg));			\
		}							\
	} while (0)

int main(void)
{
	jwk_set_t *jwks = NULL;
	const jwk_item_t *key = NULL;
	jwt_builder_t *builder = NULL;
	jwt_checker_t *checker = NULL;
	char *token = NULL;
	int ret;

	jwks = jwks_create(JWKS_HS256);
	CHECK(jwks != NULL, "jwks_create() 返回非空");
	CHECK(jwks != NULL && jwks_error(jwks) == 0, "JWKS 载入无错误");
	CHECK(jwks != NULL && jwks_item_count(jwks) == 1, "JWKS 含 1 个密钥");

	key = jwks ? jwks_item_get(jwks, 0) : NULL;
	CHECK(key != NULL, "jwks_item_get(0) 返回非空");

	builder = jwt_builder_new();
	CHECK(builder != NULL, "jwt_builder_new() 返回非空");

	ret = builder ? jwt_builder_setkey(builder, JWT_ALG_HS256, key) : -1;
	CHECK(ret == 0, "jwt_builder_setkey(HS256) 成功");

	token = builder ? jwt_builder_generate(builder) : NULL;
	CHECK(token != NULL, "jwt_builder_generate() 产出 token");
	CHECK(token != NULL && strchr(token, '.') != NULL, "token 含 JWT 分隔点");

	checker = jwt_checker_new();
	CHECK(checker != NULL, "jwt_checker_new() 返回非空");

	ret = checker ? jwt_checker_setkey(checker, JWT_ALG_HS256, key) : -1;
	CHECK(ret == 0, "jwt_checker_setkey(HS256) 成功");

	ret = (checker != NULL && token != NULL) ? jwt_checker_verify(checker, token) : -1;
	CHECK(ret == 0, "jwt_checker_verify() 校验自签 token 通过");

	/* 负样本：篡改签名末位后必须校验失败 */
	if (checker != NULL && token != NULL) {
		size_t len = strlen(token);
		char *bad = (char *)malloc(len + 1);

		if (bad != NULL) {
			memcpy(bad, token, len + 1);
			bad[len - 1] = (bad[len - 1] == 'A') ? 'B' : 'A';
			ret = jwt_checker_verify(checker, bad);
			CHECK(ret != 0, "被篡改的 token 校验失败（负样本）");
			free(bad);
		}
	}

	free(token);
	jwt_checker_free(checker);
	jwt_builder_free(builder);
	jwks_free(jwks);

	if (failures != 0) {
		fprintf(stderr, "%d check(s) FAILED\n", failures);
		return EXIT_FAILURE;
	}

	printf("test libjwt 3.3.3: all checks passed\n");
	return EXIT_SUCCESS;
}
