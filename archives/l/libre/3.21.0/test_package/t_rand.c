#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	char str[16];
	size_t i, nz = 0;
	uint16_t a1 = rand_u16(), a2 = rand_u16();
	uint32_t b1 = rand_u32(), b2 = rand_u32();
	uint64_t c1 = rand_u64(), c2 = rand_u64();

	(void)a1; (void)c1;
	CHECK(a2 != a1 || b2 != b1 || c2 != c1);

	memset(str, 0, sizeof(str));
	rand_str(str, sizeof(str));
	for (i = 0; i < sizeof(str); i++)
		if (str[i])
			++nz;
	CHECK(nz > 0);
	CHECK(str[sizeof(str) - 1] == '\0');

	CHECK(rand_char() != 0);

	libre_close();

	return errors ? 1 : 0;
}
