/*
 * libsylph 消费者测试（test_package）——以库使用者身份调用公开 API 并断言行为。
 * 覆盖三组真实功能：base64 往返、MD5 已知摘要、quoted-printable 往返。
 *
 * 断言口径按上游实际 API 契约（读 libsylph/*.h 与实现确认）：
 *  - base64_encode 输出长度 = 4*ceil(n/3)；
 *  - s_gnet_md5_new(buffer,len) 才是"计算"入口（s_gnet_md5_new_string 断言
 *    strlen(str) >= 32，是"从 32 位十六进制串反序列化"的入口，不能用来算摘要）；
 *  - qp_encode_line 会补行尾换行，故用前缀比较而非整串相等。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <glib.h>
#include <sylph/base64.h>
#include <sylph/md5.h>
#include <sylph/quoted-printable.h>

static int failures = 0;

static void check(int cond, const char *what)
{
	if (cond) {
		printf("PASS: %s\n", what);
	} else {
		printf("FAIL: %s\n", what);
		failures++;
	}
}

int main(void)
{
	/* ---- 1) base64 往返（含非 ASCII 与二进制字节）---- */
	{
		const guchar raw[] = "libsylph \xE4\xB8\xAD\xE6\x96\x87 \x01\x02\xFF";
		gint rawlen = (gint)sizeof(raw) - 1;	/* 去掉结尾 NUL */
		gchar enc[256];
		guchar dec[256];
		gint declen;
		gint expect_enc;

		memset(enc, 0, sizeof(enc));
		memset(dec, 0, sizeof(dec));

		base64_encode(enc, raw, rawlen);
		printf("      base64_encode(%d bytes) -> \"%s\"\n", rawlen, enc);

		expect_enc = ((rawlen + 2) / 3) * 4;
		check((gint)strlen(enc) == expect_enc, "base64 编码长度 == 4*ceil(n/3)");

		declen = base64_decode(dec, enc, (gint)strlen(enc));
		check(declen == rawlen, "base64_decode 返回原始长度");
		check(memcmp(dec, raw, (size_t)rawlen) == 0, "base64 往返载荷一致");
	}

	/* ---- 2) MD5 已知摘要（RFC 1321 测试向量 "abc"）---- */
	{
		SMD5 *md5 = s_gnet_md5_new((const guchar *)"abc", 3);
		gchar digest[64];

		memset(digest, 0, sizeof(digest));
		check(md5 != NULL, "s_gnet_md5_new 返回非空");
		if (md5 != NULL) {
			s_gnet_md5_copy_string(md5, digest);
			printf("      md5(\"abc\") -> %s\n", digest);
			check(strcmp(digest, "900150983cd24fb0d6963f7d28e17f72") == 0,
			      "MD5(\"abc\") == RFC 1321 向量");
			s_gnet_md5_delete(md5);
		}
	}

	/* ---- 3) quoted-printable 往返（'=' 必须编码为 =3D）---- */
	{
		gchar enc[256];
		gchar buf[256];
		gint declen;

		memset(enc, 0, sizeof(enc));
		qp_encode_line(enc, (const guchar *)"a=b");
		printf("      qp_encode_line(\"a=b\") -> \"%s\"\n", enc);
		check(strncmp(enc, "a=3Db", 5) == 0, "qp_encode_line 把 '=' 编成 =3D");

		memset(buf, 0, sizeof(buf));
		strcpy(buf, "a=3Db");
		declen = qp_decode_line(buf);
		check(declen == 3, "qp_decode_line 返回解码长度 3");
		check(strcmp(buf, "a=b") == 0, "quoted-printable 往返一致");
	}

	printf("\nlibsylph 消费者测试: %s（%d 项失败）\n",
	       failures == 0 ? "全部通过" : "存在失败", failures);
	return failures == 0 ? 0 : 1;
}
