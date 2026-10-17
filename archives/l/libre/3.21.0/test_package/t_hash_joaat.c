#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct pl pl;

	CHECK(hash_joaat_str("aardvark") ==
	      hash_joaat((const uint8_t *)"aardvark", 8));
	CHECK(hash_joaat_ci("ABCdef", 6) == hash_joaat_ci("abcdef", 6));
	CHECK(hash_joaat_str("ABCdef") != hash_joaat_ci("abcdef", 6));

	pl_set_str(&pl, "lookup-key");
	CHECK(hash_joaat_pl(&pl) == hash_joaat_str("lookup-key"));
	pl_set_str(&pl, "LOOKUP-KEY");
	CHECK(hash_joaat_pl_ci(&pl) == hash_joaat_ci("lookup-key", 10));
	CHECK(hash_fast("xyz", 3) == hash_fast_str("xyz"));

	CHECK(hash_valid_size(0) >= 1);
	CHECK(hash_valid_size(hash_valid_size(100)) == hash_valid_size(100));

	CHECK(hash_joaat_str("one") != hash_joaat_str("two"));

	libre_close();

	return errors ? 1 : 0;
}
