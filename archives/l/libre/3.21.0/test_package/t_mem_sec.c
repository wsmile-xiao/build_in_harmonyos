#include <errno.h>
#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	uint8_t a[16], b[16];
	struct memstat ms;

	memset(a, 0x41, sizeof(a));
	memset(b, 0x41, sizeof(b));
	CHECK(mem_seccmp(a, b, sizeof(a)) == 0);

	b[15] = 0x42;
	CHECK(mem_seccmp(a, b, sizeof(a)) != 0);

	a[15] = 0x42;
	CHECK(mem_seccmp(a, b, sizeof(a)) == 0);

	CHECK(mem_seccmp(a, b, 0) == 0);

	mem_secclean(a, sizeof(a));
	CHECK(a[0] == 0 && a[15] == 0);

	/* re 的 memstat 仅在 MEM_DEBUG 构建下可用，否则按设计返回 ENOSYS */
	CHECK(mem_get_stat(&ms) == ENOSYS || mem_get_stat(&ms) == 0);

	libre_close();

	return errors ? 1 : 0;
}
