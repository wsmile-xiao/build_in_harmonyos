#include <re.h>
#include "_check.h"

struct obj {
	unsigned magic;
	unsigned *hit;
};

static void destructor(void *arg)
{
	struct obj *obj = arg;
	obj->magic = 0;
	if (obj->hit)
		*obj->hit = 12345;
}

int main(void)
{

	CHECK(libre_init() == 0);
	struct obj *obj;
	unsigned hit = 0;
	char *p;

	obj = mem_zalloc(sizeof(*obj), destructor);
	CHECK(obj != NULL);
	CHECK(obj->magic == 0);
	CHECK(mem_nrefs(obj) == 1);

	CHECK(mem_ref(obj) == obj);
	CHECK(mem_nrefs(obj) == 2);
	/* re 的 mem_deref 在计数仍 >0 时返回 NULL（对象仍存活） */
	CHECK(mem_deref(obj) == NULL);
	CHECK(mem_nrefs(obj) == 1);
	CHECK(hit == 0);

	obj->hit = &hit;
	CHECK(mem_deref(obj) == NULL);
	CHECK(hit == 12345);

	p = mem_alloc(8, NULL);
	CHECK(p != NULL);
	p = mem_realloc(p, 64);
	CHECK(p != NULL);
	mem_deref(p);

	mem_deref(NULL);

	libre_close();

	return errors ? 1 : 0;
}
