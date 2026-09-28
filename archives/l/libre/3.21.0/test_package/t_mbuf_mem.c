#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct mbuf *mb = mbuf_alloc(8);
	struct mbuf *ref;
	uint8_t out[16];

	CHECK(mb != NULL);
	/* 初始容量不足时 write 应自动增长 */
	CHECK(mbuf_write_mem(mb, (const uint8_t *)"abcdefgh", 8) == 0);
	CHECK(mb->end == 8);
	CHECK(mbuf_write_mem(mb, (const uint8_t *)"ijkl", 4) == 0);
	CHECK(mb->end == 12);

	mbuf_set_pos(mb, 0);
	CHECK(mbuf_read_mem(mb, out, 12) == 0);
	CHECK(memcmp(out, "abcdefghijkl", 12) == 0);

	mbuf_reset(mb);
	CHECK(mbuf_resize(mb, 64) == 0);
	CHECK(mb->size >= 64);

	CHECK(mbuf_write_str(mb, "trim") == 0);
	mbuf_set_end(mb, 2);
	mbuf_trim(mb);
	CHECK(mb->end == 2);
	CHECK(mbuf_get_left(mb) == 0);

	ref = mbuf_alloc_ref(mb);
	CHECK(ref != NULL);
	CHECK(mbuf_get_left(ref) == 0);

	(void)mem_deref(ref);
	(void)mem_deref(mb);
	libre_close();

	return errors ? 1 : 0;
}
