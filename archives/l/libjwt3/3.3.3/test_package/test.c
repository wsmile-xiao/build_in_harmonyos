/*
 * libjwt3 消费者测试（test_package）——真实调用被测包公开 API。
 *
 * 覆盖 v3 API 的完整正向 + 负向链路：
 *   1. JWKS 载入（jwks_create）→ 取 JWK（jwks_item_get）→ 校验键属性
 *   2. HS256 签发（jwt_builder_new/setkey/generate）
 *   3. 校验通过（jwt_checker_new/setkey/verify）
 *   4. 篡改签名后校验**必须失败**（负样本 —— 保证测试不是"只返回 0"的空壳）
 *   5. 篡改 payload 后校验**必须失败**
 *   6. 换密钥校验**必须失败**（算法/密钥不匹配）
 *   7. 过期的 exp 校验**必须失败**（checker 声明 JWT_CLAIM_EXP）
 *   8. builder claim 设置/读取（jwt_set_SET_INT/GET_INT 宏族 + jwt_t 访问）
 *
 * 不引入 libcheck 等外部测试框架，自带轻量断言宏（与上游 tests/ 无关，
 * 这是消费者视角的独立验证）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>	/* sleep()：exp 过期负样本需要真实等待 */

#include <jwt.h>

static int checks_ok;
static int checks_fail;

#define CHECK(cond, msg)						\
	do {								\
		if (cond) {						\
			checks_ok++;					\
			printf("ok: %s\n", (msg));			\
		} else {						\
			checks_fail++;					\
			printf("FAIL: %s (line %d)\n", (msg), __LINE__);	\
		}							\
	} while (0)

/* 上游 tests/keys/oct_key_256.json 的等价内容（HS256，256-bit） */
static const char *JWKS_OK =
	"{ \"keys\": [ { \"kty\": \"oct\", \"alg\": \"HS256\","
	" \"k\": \"0gmNspkRljssLSrldySnYUS-zhtCo5sqeqo_yl7n2XA\" } ] }";

/* 另一把不同的 HS256 密钥（用于"换密钥校验必须失败"负样本） */
static const char *JWKS_OTHER =
	"{ \"keys\": [ { \"kty\": \"oct\", \"alg\": \"HS256\","
	" \"k\": \"ABEiM0RVZneImaq7zN3u_wARIjNEVWZ3iJmqu8zd7v8\" } ] }";

/* 非法密钥集：oct 键缺少 "k"（jwks_error_any 必须为真） */
static const char *JWKS_BAD =
	"{ \"keys\": [ { \"kty\": \"oct\", \"alg\": \"HS256\" } ] }";

/* 篡改 JWT 的签名段（最后一段），保持长度不变 —— 签名必须校验失败 */
static void tamper_signature(char *token)
{
	size_t len = strlen(token);
	size_t i;
	for (i = len; i > 0; i--) {
		if (token[i - 1] == '.') {
			/* 找到最后一段起点，翻转首字符 */
			char *sig = token + i;
			if (*sig == '\0')
				return;
			*sig = (*sig == 'A') ? 'B' : 'A';
			return;
		}
	}
}

int main(void)
{
	/* ── 1. JWKS 载入与 JWK 校验 ───────────────────────────────────── */
	jwk_set_t *jwks = jwks_create(JWKS_OK);
	CHECK(jwks != NULL, "jwks_create() 载入 HS256 密钥集成功");
	if (jwks == NULL) {
		fprintf(stderr, "无法载入密钥集，后续检查中止\n");
		return EXIT_FAILURE;
	}
	CHECK(jwks_error(jwks) == 0, "jwks_error() == 0（密钥集本身无错误）");
	CHECK(jwks_error_any(jwks) == 0, "jwks_error_any() == 0（所有 JWK 项无错误）");

	const jwk_item_t *item = jwks_item_get(jwks, 0);
	CHECK(item != NULL, "jwks_item_get(0) 取到 JWK 项");
	CHECK(jwks_item_kty(item) == JWK_KEY_TYPE_OCT,
	      "jwks_item_kty() == JWK_KEY_TYPE_OCT");
	CHECK(jwks_item_alg(item) == JWT_ALG_HS256,
	      "jwks_item_alg() == JWT_ALG_HS256");

	const unsigned char *keybuf = NULL;
	size_t keylen = 0;
	CHECK(jwks_item_key_oct(item, &keybuf, &keylen) == 0 && keybuf != NULL &&
	      keylen == 32,
	      "jwks_item_key_oct() 返回 32 字节原始密钥（256-bit）");

	/* 非法密钥集：必须报出项级错误（负样本） */
	jwk_set_t *jwks_bad = jwks_create(JWKS_BAD);
	CHECK(jwks_bad != NULL && jwks_error_any(jwks_bad) != 0,
	      "非法 JWK（缺 k）被 jwks_error_any() 检出");

	/* ── 2. HS256 签发 ───────────────────────────────────────────── */
	jwt_builder_t *builder = jwt_builder_new();
	CHECK(builder != NULL && jwt_builder_error(builder) == 0,
	      "jwt_builder_new() 创建 builder");

	/* 关闭自动 iat，保证令牌内容可预期 */
	CHECK(jwt_builder_enable_iat(builder, 0) == 1,
	      "jwt_builder_enable_iat(0) 关闭自动 iat");

	CHECK(jwt_builder_setkey(builder, JWT_ALG_HS256, item) == 0,
	      "jwt_builder_setkey(HS256) 绑定密钥");

	/* 设置一个自定义 claim（真实使用 jwt_value_t 宏族） */
	jwt_value_t jval;
	jwt_builder_claim_set(builder, jwt_set_SET_STR(&jval, "sub", "libjwt3-test"));
	CHECK(jwt_builder_claim_get(builder, jwt_set_GET_STR(&jval, "sub")) ==
	      JWT_VALUE_ERR_NONE && jval.str_val != NULL &&
	      strcmp(jval.str_val, "libjwt3-test") == 0,
	      "builder claim \"sub\" 设置后可读回（SET/GET 宏族）");

	char *token = jwt_builder_generate(builder);
	CHECK(token != NULL, "jwt_builder_generate() 产出令牌");
	if (token == NULL) {
		fprintf(stderr, "签发失败: %s\n", jwt_builder_error_msg(builder));
		return EXIT_FAILURE;
	}
	/* JWS 紧凑形式必须恰好两处 '.' 且签名段非空 */
	{
		const char *p = token;
		int dots = 0;
		while (*p) {
			if (*p == '.')
				dots++;
			p++;
		}
		CHECK(dots == 2 && strlen(token) > 20,
		      "令牌为三段式紧凑 JWS（header.payload.signature）");
	}
	jwt_builder_free(builder);

	/* ── 3. 正确校验必须通过 ─────────────────────────────────────── */
	jwt_checker_t *checker = jwt_checker_new();
	CHECK(checker != NULL && jwt_checker_error(checker) == 0,
	      "jwt_checker_new() 创建 checker");
	CHECK(jwt_checker_setkey(checker, JWT_ALG_HS256, item) == 0,
	      "jwt_checker_setkey(HS256) 绑定密钥");
	CHECK(jwt_checker_verify(checker, token) == 0,
	      "jwt_checker_verify() 对合法令牌校验通过");
	jwt_checker_free(checker);

	/* ── 4. 篡改签名后校验必须失败（负样本） ─────────────────────── */
	{
		char *tampered = strdup(token);
		tamper_signature(tampered);
		CHECK(strcmp(tampered, token) != 0, "篡改后的令牌与原令牌不同");

		jwt_checker_t *c2 = jwt_checker_new();
		jwt_checker_setkey(c2, JWT_ALG_HS256, item);
		CHECK(jwt_checker_verify(c2, tampered) != 0,
		      "篡改签名后 jwt_checker_verify() 必须失败");
		jwt_checker_free(c2);
		free(tampered);
	}

	/* ── 5. 篡改 payload 后校验必须失败（负样本） ────────────────── */
	{
		char *tampered = strdup(token);
		char *dot = strchr(tampered, '.');
		if (dot != NULL && dot[1] != '\0' && dot[1] != '.') {
			char *pl = dot + 1;
			/* payload 段首字符做一次等效替换（保持 base64url 字符集） */
			*pl = (*pl == 'e') ? 'f' : 'e';
		}
		jwt_checker_t *c3 = jwt_checker_new();
		jwt_checker_setkey(c3, JWT_ALG_HS256, item);
		CHECK(jwt_checker_verify(c3, tampered) != 0,
		      "篡改 payload 后 jwt_checker_verify() 必须失败");
		jwt_checker_free(c3);
		free(tampered);
	}

	/* ── 6. 换密钥校验必须失败（负样本） ─────────────────────────── */
	{
		jwk_set_t *other = jwks_create(JWKS_OTHER);
		const jwk_item_t *other_item = jwks_item_get(other, 0);
		jwt_checker_t *c4 = jwt_checker_new();
		jwt_checker_setkey(c4, JWT_ALG_HS256, other_item);
		CHECK(jwt_checker_verify(c4, token) != 0,
		      "换用另一把 HS256 密钥校验必须失败");
		jwt_checker_free(c4);
		jwks_free(other);
	}

	/* ── 7. checker 声明式 claim 策略（正/负样本成对） ───────────── */
	{
		/* 上游语义（include/jwt.h:960-965）：sub 使用字符串全等比较。
		 * 期望值一致 → 通过；期望值不同 → 必须失败。 */
		jwt_checker_t *c5 = jwt_checker_new();
		jwt_checker_setkey(c5, JWT_ALG_HS256, item);
		CHECK(jwt_checker_claim_set(c5, JWT_CLAIM_SUB, "libjwt3-test") == 0,
		      "jwt_checker_claim_set(SUB) 设置期望值");
		CHECK(strcmp(jwt_checker_claim_get(c5, JWT_CLAIM_SUB),
			     "libjwt3-test") == 0,
		      "jwt_checker_claim_get(SUB) 读回期望值");
		CHECK(jwt_checker_verify(c5, token) == 0,
		      "checker 声明的 sub 与令牌一致 → 校验通过");
		CHECK(jwt_checker_claim_set(c5, JWT_CLAIM_SUB, "someone-else") == 0,
		      "jwt_checker_claim_set(SUB) 改为不一致的期望值");
		CHECK(jwt_checker_verify(c5, token) != 0,
		      "checker 声明的 sub 与令牌不一致 → 校验必须失败");
		jwt_checker_free(c5);
	}

	/* ── 7b. exp 过期语义（正/负样本成对，等价上游 tests/jwt_claims.c） ──
	 * exp/nbf 不是字符串 claim，不能用 jwt_checker_claim_set（上游只接受
	 * ISS/AUD/SUB），须用 jwt_checker_time_leeway 开启检查并设 leeway。 */
	{
		jwt_builder_t *b = jwt_builder_new();
		jwt_builder_enable_iat(b, 0);
		jwt_builder_setkey(b, JWT_ALG_HS256, item);
		/* exp = now + 1（上游语义：time_offset 取「当前时间 + secs」） */
		CHECK(jwt_builder_time_offset(b, JWT_CLAIM_EXP, 1) == 0,
		      "jwt_builder_time_offset(EXP, 1) 设置 1 秒后过期");
		char *short_lived = jwt_builder_generate(b);
		CHECK(short_lived != NULL, "签发带 exp 的短期令牌");
		jwt_builder_free(b);

		jwt_checker_t *c5b = jwt_checker_new();
		jwt_checker_setkey(c5b, JWT_ALG_HS256, item);
		/* leeway=0 → 开启 exp 校验 */
		CHECK(jwt_checker_time_leeway(c5b, JWT_CLAIM_EXP, 0) == 0,
		      "jwt_checker_time_leeway(EXP, 0) 开启 exp 校验");
		CHECK(jwt_checker_verify(c5b, short_lived) == 0,
		      "未过期的 exp 令牌校验通过");

		/* 等到过期后再验：必须失败 */
		sleep(2);
		CHECK(jwt_checker_verify(c5b, short_lived) != 0,
		      "已过期的 exp 令牌校验必须失败");
		jwt_checker_error_clear(c5b);

		/* 放宽 leeway 后应重新通过（证明失败确由 exp 触发） */
		CHECK(jwt_checker_time_leeway(c5b, JWT_CLAIM_EXP, 10) == 0,
		      "jwt_checker_time_leeway(EXP, 10) 放宽 10 秒");
		CHECK(jwt_checker_verify(c5b, short_lived) == 0,
		      "放宽 leeway 后同一过期令牌校验通过（失败确由 exp 触发）");
		jwt_checker_free(c5b);
		free(short_lived);
	}

	/* ── 8. 无效令牌必须失败（负样本） ───────────────────────────── */
	{
		jwt_checker_t *c6 = jwt_checker_new();
		jwt_checker_setkey(c6, JWT_ALG_HS256, item);
		CHECK(jwt_checker_verify(c6, "not-a-jwt") != 0,
		      "非 JWT 字符串校验必须失败");
		jwt_checker_free(c6);
	}

	free(token);
	jwks_free(jwks_bad);
	jwks_free(jwks);

	printf("test libjwt3 3.3.3 consumer: %d checks passed, %d failed\n",
	       checks_ok, checks_fail);
	return checks_fail == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
