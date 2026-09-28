#include <re.h>
#include "_check.h"

/* 已知答案取自上游 test/crc32.c 的向量表 */
static const struct { const char *str; uint32_t crc; } tv[] = {
	{"string",  0x9ebeb2a9},
	{"hei",     0x95610594},
	{"0ndka98d198aloidks9zaz1oqs5jilk", 0x92a398f6},
};

int main(void)
{

	CHECK(libre_init() == 0);
	uint32_t crc, part;
	size_t i;

	for (i = 0; i < sizeof(tv) / sizeof(tv[0]); i++) {
		crc = re_crc32(0, (const uint8_t *)tv[i].str,
			      (uint32_t)strlen(tv[i].str));
		CHECK(crc == tv[i].crc);
	}

	/* 分段计算与一次性计算等价 */
	crc = re_crc32(0, (const uint8_t *)"0ndka98d", 8);
	part = re_crc32(crc, (const uint8_t *)"198aloidks9zaz1oqs5jilk", 23);
	CHECK(part == 0x92a398f6);

	CHECK(re_crc32(0, (const uint8_t *)"a", 1) !=
	      re_crc32(0, (const uint8_t *)"b", 1));

	libre_close();

	return errors ? 1 : 0;
}
