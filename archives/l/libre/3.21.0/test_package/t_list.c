#include <re.h>
#include "_check.h"

struct item { int v; struct le le; };

int main(void)
{

	CHECK(libre_init() == 0);
	struct list list;
	struct item a = {1}, b = {2}, c = {3};

	list_init(&list);
	CHECK(list_count(&list) == 0);
	CHECK(list.head == NULL && list.tail == NULL);

	list_append(&list, &a.le, &a);
	list_append(&list, &b.le, &b);
	list_prepend(&list, &c.le, &c);

	CHECK(list_count(&list) == 3);
	CHECK(list_head(&list) == &c.le);
	CHECK(list_tail(&list) == &b.le);
	CHECK(((struct item *)list_head(&list)->data)->v == 3);
	CHECK(((struct item *)list_tail(&list)->data)->v == 2);
	CHECK(c.le.next == &a.le && a.le.prev == &c.le);
	CHECK(a.le.list == &list);

	list_unlink(&a.le);
	CHECK(list_count(&list) == 2);
	CHECK(list_head(&list) == &c.le && c.le.next == &b.le);

	list_clear(&list);
	CHECK(list_count(&list) == 0);
	CHECK(list.head == NULL && list.tail == NULL);

	libre_close();

	return errors ? 1 : 0;
}
