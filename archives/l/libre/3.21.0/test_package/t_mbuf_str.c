#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct mbuf *mb = mbuf_alloc(32);
	struct pl pl;
	char buf[16];

	CHECK(mb != NULL);
	CHECK(mbuf_write_str(mb, "hello re") == 0);
	CHECK(mb->end == 8);

	mbuf_set_pos(mb, 0);
	pl_set_mbuf(&pl, mb);
	CHECK(pl.l == 8);
	CHECK(pl_strcmp(&pl, "hello re") == 0);

	mbuf_set_pos(mb, 6);
	CHECK(mbuf_get_left(mb) == 2);
	pl_set_mbuf(&pl, mb);
	CHECK(pl_strcmp(&pl, "re") == 0);

	CHECK(mbuf_read_str(mb, buf, sizeof(buf)) == 0);
	CHECK(strcmp(buf, "re") == 0);

	(void)mem_deref(mb);
	libre_close();

	return errors ? 1 : 0;
}
