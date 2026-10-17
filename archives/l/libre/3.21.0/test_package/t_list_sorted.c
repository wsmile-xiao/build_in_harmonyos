#include <re.h>
#include "_check.h"

struct item { int v; struct le le; };

static bool asc(struct le *l1, struct le *l2, void *arg)
{
	(void)arg;
	return ((const struct item *)l1->data)->v <
		((const struct item *)l2->data)->v;
}

static bool sumapply(struct le *le, void *arg)
{
	unsigned *sum = arg;
	*sum += (unsigned)((struct item *)le->data)->v;
	return false;
}

int main(void)
{

	CHECK(libre_init() == 0);
	struct list list;
	struct item v[5] = {{30}, {10}, {50}, {20}, {40}};
	unsigned sum = 0;
	size_t i;

	list_init(&list);
	for (i = 0; i < 5; i++)
		list_insert_sorted(&list, asc, NULL, &v[i].le, &v[i]);

	CHECK(list_count(&list) == 5);
	for (i = 0; i < 5; i++) {
		struct le *le = list_head(&list);
		CHECK(le != NULL);
		CHECK(((struct item *)le->data)->v == (int)((i + 1) * 10));
		list_unlink(le);
	}
	CHECK(list_count(&list) == 0);

	for (i = 0; i < 5; i++)
		list_append(&list, &v[i].le, &v[i]);
	list_apply(&list, true, sumapply, &sum);
	CHECK(sum == 150);

	list_sort(&list, asc, NULL);
	CHECK(((struct item *)list_head(&list)->data)->v == 10);
	CHECK(((struct item *)list_tail(&list)->data)->v == 50);

	list_clear(&list);
	CHECK(list_count(&list) == 0);

	libre_close();

	return errors ? 1 : 0;
}
