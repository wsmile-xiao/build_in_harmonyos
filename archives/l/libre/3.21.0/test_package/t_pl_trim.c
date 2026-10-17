#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct pl pl, dup;
	struct pl *alloced;
	char *sdup = NULL;

	pl.p = "  spaced  ";
	pl.l = 10;
	CHECK(pl_isset(&pl) == true);
	CHECK(pl_trim(&pl) == 0);
	CHECK(pl.l == 6);
	CHECK(pl.p[0] == 's' && pl.p[5] == 'd');

	pl.p = "\tleft";
	pl.l = 5;
	CHECK(pl_ltrim(&pl) == 0);
	CHECK(pl.l == 4 && pl.p[0] == 'l');

	pl.p = "right\n";
	pl.l = 6;
	CHECK(pl_rtrim(&pl) == 0);
	CHECK(pl.l == 5);

	pl_set_str(&pl, "copy me");
	CHECK(pl_dup(&dup, &pl) == 0);
	/* pl_dup 返回一份新分配的副本（非同一指针） */
	CHECK(dup.l == 7 && dup.p != pl.p);
	CHECK(memcmp(dup.p, pl.p, 7) == 0);
	mem_deref((void *)dup.p);
	CHECK(pl_strdup(&sdup, &pl) == 0);
	CHECK(sdup != NULL && strcmp(sdup, "copy me") == 0);
	sdup = mem_deref(sdup);

	alloced = pl_alloc_str("alloc");
	CHECK(alloced != NULL);
	CHECK(alloced->l == 5);
	/* pl_alloc_str 分配的缓冲区不带 NUL 结尾，按长度比较 */
	CHECK(memcmp(alloced->p, "alloc", 5) == 0);
	alloced = mem_deref(alloced);

	pl_set_str(&pl, "advance");
	pl_advance(&pl, 3);
	CHECK(pl.l == 4);
	CHECK(pl.p[0] == 'a' && pl.p[3] == 'e');

	libre_close();

	return errors ? 1 : 0;
}
