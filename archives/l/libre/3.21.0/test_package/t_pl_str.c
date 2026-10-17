#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct pl a, b;

	pl_set_str(&a, "hello world");
	pl_set_str(&b, "hello world");
	CHECK(a.l == 11);
	CHECK(pl_cmp(&a, &b) == 0);
	CHECK(pl_strcmp(&a, "hello world") == 0);
	CHECK(pl_strcmp(&a, "hello") != 0);
	CHECK(pl_strncmp(&a, "hello", 5) == 0);

	pl_set_str(&b, "HELLO WORLD");
	CHECK(pl_cmp(&a, &b) != 0);
	CHECK(pl_casecmp(&a, &b) == 0);
	CHECK(pl_strcasecmp(&b, "hello world") == 0);

	/* "hello world": w@6, o@4 与 o@7 */
	CHECK(pl_strstr(&a, "world") == &a.p[6]);
	CHECK(pl_strstr(&a, "nope") == NULL);
	CHECK(pl_strchr(&a, 'w') == &a.p[6]);
	CHECK(pl_strrchr(&a, 'o') == &a.p[7]);
	CHECK(pl_strchr(&a, 'z') == NULL);

	libre_close();

	return errors ? 1 : 0;
}
