#include <re.h>
#include "_check.h"

static uint32_t cnt;

/* hash_lookup 需要一个 apply 处理器（传 NULL 直接返回 NULL）；用它按数据指针定位 */
static bool find_data(struct le *le, void *arg)
{
	return le->data == arg;
}

static bool countfn(struct le *le, void *arg)
{
	(void)le;
	(void)arg;
	++cnt;
	return false;
}

int main(void)
{

	CHECK(libre_init() == 0);
	struct hash *h = NULL;
	/* struct le 必须初始化，否则 hash_append 会因 le->list 非空而拒绝 */
	struct le le1 = LE_INIT, le2 = LE_INIT, le3 = LE_INIT;
	struct le *le;
	int v1 = 1, v2 = 2, v3 = 3;
	uint32_t k1, k2, k3;

	CHECK(hash_alloc(&h, 32) == 0);
	CHECK(h != NULL);
	CHECK(hash_bsize(h) >= 32);

	k1 = hash_joaat_str("alpha");
	k2 = hash_joaat_str("beta");
	k3 = hash_joaat_str("gamma");

	hash_append(h, k1, &le1, &v1);
	hash_append(h, k2, &le2, &v2);
	hash_append(h, k1, &le3, &v3);

	le = hash_lookup(h, k1, find_data, &v1);
	CHECK(le != NULL && le->data == &v1);
	le = hash_lookup(h, k2, find_data, &v2);
	CHECK(le != NULL && le->data == &v2);
	CHECK(hash_lookup(h, k3, find_data, &v1) == NULL);
	CHECK(hash_list(h, k1) != NULL);

	cnt = 0;
	hash_apply(h, countfn, NULL);
	CHECK(cnt == 3);

	hash_unlink(&le3);
	le = hash_lookup(h, k1, find_data, &v1);
	CHECK(le != NULL && le->data == &v1);
	cnt = 0;
	hash_apply(h, countfn, NULL);
	CHECK(cnt == 2);

	hash_flush(h);
	cnt = 0;
	hash_apply(h, countfn, NULL);
	CHECK(cnt == 0);

	(void)mem_deref(h);
	libre_close();

	return errors ? 1 : 0;
}
