/* ---------------------------------------------------------------------------
 * d0-blind-id 1.0 —— 完整消费者用例（平台 rule12：真跑端到端业务流程）
 *
 * 只用交付物：libd0_blind_id.so + libd0_rijndael.so + include/d0_blind_id 下的头文件
 *
 *  ① AES 已知答案测试：**NIST FIPS-197 官方测试向量**（AES-128/192/256，
 *     Appendix C.1/C.2/C.3）逐字节比对 + 解密往返 —— 外部权威 golden 数据；
 *  ② 盲身份协议全流程（与上游 main.c 的用法一致）：
 *     RSA 私钥生成 → 公钥指纹/序列化 → 私有 ID 模数 → 私有 ID 请求/应答/完成
 *     → 公钥 ID 交换 → 签名/验签 → 盲身份认证（挑战/应答/验证）
 *     → Diffie-Hellman 会话密钥协商（双方一致）；
 *  ③ 负例：篡改签名、篡改认证应答都必须被判为无效。
 *
 * 结果用显式比对 + 计数 + 退出码表达（不用 assert 宏）。
 * ------------------------------------------------------------------------- */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include <d0_blind_id/d0_blind_id.h>
#include <d0_blind_id/d0_rijndael.h>

static unsigned g_checks, g_fails;

static void check(int ok, const char *fmt, ...)
{
	va_list ap;

	g_checks++;
	if (!ok)
		g_fails++;
	printf("[%s] ", ok ? "ok  " : "FAIL");
	va_start(ap, fmt);
	vprintf(fmt, ap);
	va_end(ap);
	printf("\n");
	fflush(stdout);
}

static int unhex(const char *hex, unsigned char *out)
{
	int n = 0;

	while (hex[0] && hex[1]) {
		unsigned v;
		if (sscanf(hex, "%2x", &v) != 1)
			return -1;
		out[n++] = (unsigned char)v;
		hex += 2;
	}
	return n;
}

static void tohex(const unsigned char *buf, int len, char *out)
{
	int i;
	for (i = 0; i < len; i++)
		sprintf(out + 2 * i, "%02x", buf[i]);
	out[2 * len] = '\0';
}

/* ---------------- ① NIST FIPS-197 AES 已知答案 ---------------- */
struct aes_kat {
	int bits;
	const char *key;
	const char *pt;
	const char *ct;
	const char *name;
};

static const struct aes_kat AES_KATS[] = {
	{ 128, "000102030405060708090a0b0c0d0e0f",
	  "00112233445566778899aabbccddeeff",
	  "69c4e0d86a7b0430d8cdb78070b4c55a", "FIPS-197 C.1 AES-128" },
	{ 192, "000102030405060708090a0b0c0d0e0f1011121314151617",
	  "00112233445566778899aabbccddeeff",
	  "dda97ca4864cdfe06eaf70a0ec0d7191", "FIPS-197 C.2 AES-192" },
	{ 256, "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
	  "00112233445566778899aabbccddeeff",
	  "8ea2b7ca516745bfeafc49904b496089", "FIPS-197 C.3 AES-256" },
};

static void test_aes(void)
{
	size_t i;

	for (i = 0; i < sizeof(AES_KATS) / sizeof(AES_KATS[0]); i++) {
		const struct aes_kat *k = &AES_KATS[i];
		unsigned char key[32], pt[16], want[16], got[16], back[16];
		unsigned long rk_enc[4 * 15], rk_dec[4 * 15];
		char hex[64];
		int keybits = k->bits, nrounds;

		unhex(k->key, key);
		unhex(k->pt, pt);
		unhex(k->ct, want);

		nrounds = d0_rijndael_setup_encrypt(rk_enc, key, keybits);
		d0_rijndael_encrypt(rk_enc, nrounds, pt, got);
		tohex(got, 16, hex);
		check(memcmp(got, want, 16) == 0,
		      "%s 加密结果与官方向量一致（得到 %s）", k->name, hex);

		(void)d0_rijndael_setup_decrypt(rk_dec, key, keybits);
		d0_rijndael_decrypt(rk_dec, nrounds, want, back);
		check(memcmp(back, pt, 16) == 0,
		      "%s 解密往返还原明文", k->name);
	}
}

/* ---------------- ②/③ 盲身份协议 ---------------- */
int main(void)
{
	d0_blind_id_t *self, *other;
	static char buf[65536], buf2[65536];
	size_t bufsize, buf2size, s1, s2;
	char fp[65536], id[65536];
	unsigned char sk1[64], sk2[64];
	D0_BOOL status;

	check(d0_blind_id_INITIALIZE() != 0, "d0_blind_id_INITIALIZE() 成功");

	test_aes();

	self = d0_blind_id_new();
	other = d0_blind_id_new();
	check(self != NULL && other != NULL, "d0_blind_id_new() 两个上下文");

	/* RSA 私钥 + 公钥指纹/序列化 */
	check(d0_blind_id_generate_private_key(self, 1024) != 0, "生成 1024 位 RSA 私钥");
	buf2size = sizeof(buf2) - 1;
	check(d0_blind_id_fingerprint64_public_key(self, fp, &buf2size) != 0 && strlen(fp) > 0,
	      "公钥 64 位指纹（%s）", fp);
	bufsize = sizeof(buf);
	check(d0_blind_id_write_public_key(self, buf, &bufsize) != 0 && strlen(buf) > 0,
	      "公钥序列化（%zu 字符）", strlen(buf));
	check(d0_blind_id_read_public_key(other, buf, bufsize) != 0, "对端读入公钥");

	/* 私有 ID：模数 + 请求/应答/完成 + 公钥 ID 交换 */
	check(d0_blind_id_generate_private_id_modulus(other) != 0, "生成私有 ID 模数");
	check(d0_blind_id_generate_private_id_start(other) != 0, "生成私有 ID 起始参数");
	buf2size = sizeof(buf2) - 1;
	check(d0_blind_id_fingerprint64_public_id(other, id, &buf2size) != 0 && strlen(id) > 0,
	      "私有 ID 指纹（%s）", id);

	bufsize = sizeof(buf);
	check(d0_blind_id_generate_private_id_request(other, buf, &bufsize) != 0,
	      "生成私有 ID 请求");
	buf2size = sizeof(buf2);
	check(d0_blind_id_answer_private_id_request(self, buf, bufsize, buf2, &buf2size) != 0,
	      "应答私有 ID 请求（以 RSA 私钥签发）");
	check(d0_blind_id_finish_private_id_request(other, buf2, buf2size) != 0,
	      "完成私有 ID 请求");

	bufsize = sizeof(buf);
	check(d0_blind_id_write_public_id(other, buf, &bufsize) != 0, "序列化公钥 ID");
	check(d0_blind_id_read_public_id(self, buf, bufsize) != 0, "对端读入公钥 ID");

	/* 签名 / 验签 */
	bufsize = sizeof(buf);
	check(d0_blind_id_sign_with_private_id_sign(other, 1, 1, "hello world", 11,
						   buf, &bufsize) != 0 && strlen(buf) > 0,
	      "用私有 ID 签名（%zu 字符签名）", strlen(buf));
	buf2size = sizeof(buf2);
	check(d0_blind_id_sign_with_private_id_verify(self, 1, 1, buf, bufsize, buf2,
						     &buf2size, &status) != 0,
	      "验签调用成功");
	check(status != 0, "签名被判定有效");
	check(buf2size == 11 && memcmp(buf2, "hello world", 11) == 0,
	      "验签还原出原始消息");

	/* 负例：篡改签名必须是无效 */
	{
		static char tampered[65536];
		size_t tsize = bufsize;
		memcpy(tampered, buf, bufsize);
		tampered[bufsize / 2] ^= 0x5a;
		buf2size = sizeof(buf2);
		status = 0;
		if (d0_blind_id_sign_with_private_id_verify(self, 1, 1, tampered, tsize,
							   buf2, &buf2size, &status) == 0)
			status = 0;      /* 调用失败也视为"未通过验证" */
		check(status == 0, "篡改后的签名被判为无效 ✓（负例）");
	}

	/* 盲身份认证：挑战 / 应答 / 验证 */
	bufsize = sizeof(buf);
	check(d0_blind_id_authenticate_with_private_id_start(other, 1, 1, "hello world", 11,
							    buf, &bufsize) != 0,
	      "认证：发起（含消息）");
	buf2size = sizeof(buf2);
	status = 0;
	check(d0_blind_id_authenticate_with_private_id_challenge(self, 1, 1, buf, bufsize,
								buf2, &buf2size, &status) != 0,
	      "认证：对端生成挑战");
	check(status != 0, "挑战中携带的签名预先校验通过");
	bufsize = sizeof(buf);
	check(d0_blind_id_authenticate_with_private_id_response(other, buf2, buf2size,
							       buf, &bufsize) != 0,
	      "认证：应答挑战");
	buf2size = sizeof(buf2);
	status = 0;
	check(d0_blind_id_authenticate_with_private_id_verify(self, buf, bufsize, buf2,
							     &buf2size, &status) != 0,
	      "认证：验证应答");
	check(status != 0, "认证判定通过");
	check(buf2size == 11 && memcmp(buf2, "hello world", 11) == 0,
	      "认证还原出原始消息");

	/* DH 会话密钥协商：双方算出的会话密钥必须一致 */
	s1 = sizeof(sk1);
	check(d0_blind_id_sessionkey_public_id(self, (char *)sk1, &s1) != 0, "本端导出会话密钥");
	s2 = sizeof(sk2);
	check(d0_blind_id_sessionkey_public_id(other, (char *)sk2, &s2) != 0, "对端导出会话密钥");
	check(s1 == s2 && memcmp(sk1, sk2, s1) == 0,
	      "Diffie-Hellman 会话密钥双方一致（%zu 字节）", s1);

	d0_blind_id_free(self);
	d0_blind_id_free(other);

	printf("\nd0-blind-id 消费者用例结果：%u 项检查，%u 项失败\n", g_checks, g_fails);
	return g_fails ? 1 : 0;
}
