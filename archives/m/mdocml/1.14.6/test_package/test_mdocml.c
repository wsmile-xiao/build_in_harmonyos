/*
 * test_mdocml.c — mdocml 1.14.6 消费者测试：链接交付的 libmandoc.a，
 * 经公开 API（mandoc.h）覆盖字符表、unicode 映射与转义序列解析。
 *
 * 7 项断言全部在设备实测通过（clang 15 + libmandoc.a + conan zlib/1.3.1）。
 * 计入「鸿蒙特有测试」行（消费者用例不进上游分母，但必须计数）。
 */
#include <stdio.h>
#include <string.h>

#include "mandoc.h"

static int fails = 0;

#define CHECK(cond, msg)                                          \
	do {                                                    \
		if (!(cond)) {                                  \
			printf("FAIL: %s\n", (msg));            \
			fails++;                                \
		} else {                                        \
			printf("ok: %s\n", (msg));              \
		}                                               \
	} while (0)

int
main(void)
{
	const char *s;
	const char *sv;
	size_t len;
	int uc, cp;
	char buf[16];
	const char *p;
	const char *seq;
	int sz;
	enum mandoc_esc esc;

	/* 1) 十六进制数字串 → unicode 码点 */
	mchars_alloc();
	uc = mchars_num2uc("0x2019", 6);
	CHECK(uc == 0x2019, "1 mchars_num2uc(\"0x2019\",6)==0x2019");

	/* 2) unicode 码点 → ascii 近似串（命中 lines[] 映射表） */
	s = mchars_uc2str(uc);
	CHECK(s != NULL && strcmp(s, "<?>") != 0,
	    "2 mchars_uc2str(0x2019) 命中映射表");

	/* 3) roff 特殊字符名 → unicode（ul = underscore 0x005f） */
	cp = mchars_spec2cp("ul", 2);
	CHECK(cp == 0x005f, "3 mchars_spec2cp(\"ul\")==0x005f ('_')");

	/* 4) roff 特殊字符名 → ascii 近似串及长度契约 */
	len = 0;
	sv = mchars_spec2str("ul", 2, &len);
	CHECK(sv != NULL && len == 1 && sv[0] == '_',
	    "4 mchars_spec2str(\"ul\")==\"_\" len==1");

	/* 5) em dash（0x2014）走同一张表，证明表已按包形态加载 */
	cp = mchars_spec2cp("em", 2);
	CHECK(cp == 0x2014, "5 mchars_spec2cp(\"em\")==0x2014 (em dash)");
	mchars_free();

	/* 6) 转义序列解析：\fB → ESCAPE_FONTBOLD */
	memcpy(buf, "\\fBrest", 7);
	buf[7] = '\0';
	p = buf + 1;		/* 调用方先跳过反斜杠（上游 demandoc.c 同款） */
	seq = NULL;
	sz = 0;
	esc = mandoc_escape(&p, &seq, &sz);
	CHECK(esc == ESCAPE_FONTBOLD, "6 mandoc_escape(\"\\\\fB\")==ESCAPE_FONTBOLD");

	/* 7) 指针推进契约：只消费 \fB，停在 "rest" */
	CHECK(*p == 'r', "7 escape 消费后 p 停在 'rest'");

	printf("TOTAL=7 FAILS=%d\n", fails);
	return fails ? 1 : 0;
}
