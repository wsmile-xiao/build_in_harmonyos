#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct mbuf *mb = mbuf_alloc(64);

	CHECK(mb != NULL);
	if (!mb)
		return 1;
	CHECK(mb->size >= 64);
	CHECK(mbuf_get_left(mb) == 0);

	CHECK(mbuf_write_u8(mb, 0x11) == 0);
	CHECK(mbuf_write_u16(mb, 0x2222) == 0);
	CHECK(mbuf_write_u32(mb, 0x33333333) == 0);
	CHECK(mbuf_write_u64(mb, 0x4444444444444444ULL) == 0);
	CHECK(mb->end == 15);
	CHECK(mbuf_get_left(mb) == 0);

	mbuf_set_pos(mb, 0);
	CHECK(mbuf_get_left(mb) == 15);
	CHECK(mbuf_read_u8(mb) == 0x11);
	CHECK(mbuf_read_u16(mb) == 0x2222);
	CHECK(mbuf_read_u32(mb) == 0x33333333);
	CHECK(mbuf_read_u64(mb) == 0x4444444444444444ULL);
	CHECK(mbuf_get_left(mb) == 0);

	mbuf_reset(mb);
	CHECK(mb->pos == 0 && mb->end == 0);

	(void)mem_deref(mb);
	libre_close();

	return errors ? 1 : 0;
}
