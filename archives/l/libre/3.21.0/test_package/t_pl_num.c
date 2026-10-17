#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct pl pl;
	bool val = false;
	uint8_t hex[4];

	pl_set_str(&pl, "4294967295");
	CHECK(pl_u32(&pl) == 4294967295u);

	pl_set_str(&pl, "-2147483648");
	CHECK(pl_i32(&pl) == (-2147483647 - 1));

	pl_set_str(&pl, "18446744073709551615");
	CHECK(pl_u64(&pl) == 18446744073709551615ULL);

	pl_set_str(&pl, "-9223372036854775808");
	CHECK(pl_i64(&pl) == (-9223372036854775807LL - 1));

	pl_set_str(&pl, "ff00aa55");
	CHECK(pl_x32(&pl) == 0xff00aa55u);

	pl_set_str(&pl, "10");
	CHECK(pl_u32(&pl) == 10);

	pl_set_str(&pl, "3.5");
	{
		double f = pl_float(&pl);
		CHECK(f > 3.4 && f < 3.6);
	}

	pl_set_str(&pl, "yes");
	CHECK(pl_bool(&val, &pl) == 0 && val == true);
	pl_set_str(&pl, "no");
	CHECK(pl_bool(&val, &pl) == 0 && val == false);

	pl_set_str(&pl, "deadbeef");
	CHECK(pl_hex(&pl, hex, 4) == 0);
	CHECK(hex[0] == 0xde && hex[1] == 0xad);
	CHECK(hex[2] == 0xbe && hex[3] == 0xef);

	libre_close();

	return errors ? 1 : 0;
}
