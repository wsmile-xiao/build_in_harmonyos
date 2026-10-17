#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	char buf[32];
	struct pl pl;

	CHECK(re_snprintf(buf, sizeof(buf), "%u-%s", 42, "x") > 0);
	CHECK(strcmp(buf, "42-x") == 0);

	pl_set_str(&pl, "name");
	CHECK(re_snprintf(buf, sizeof(buf), "%r=%d", &pl, -7) > 0);
	CHECK(strcmp(buf, "name=-7") == 0);

	CHECK(re_snprintf(buf, sizeof(buf), "%02x", 0xab) > 0);
	CHECK(strcmp(buf, "ab") == 0);

	/* 目标缓冲不足时必须截断并保持 NUL 结尾，不得越界写 */
	memset(buf, 0xAA, sizeof(buf));
	CHECK(re_snprintf(buf, 4, "%s", "abcdefgh") <= 3);
	CHECK(strlen(buf) <= 3);

	libre_close();

	return errors ? 1 : 0;
}
