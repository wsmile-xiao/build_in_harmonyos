#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	static const uint8_t linklocal[16] = {0xfe, 0x80, 0, 0, 0, 0, 0, 0,
					      0, 0, 0, 0, 0, 0, 0, 1};
	static const uint8_t allnodes[16]  = {0xff, 0x02, 0, 0, 0, 0, 0, 0,
					      0, 0, 0, 0, 0, 0, 0, 1};
	struct sa sa;
	uint8_t out[16];
	char buf[64];

	sa_init(&sa, AF_INET6);
	sa_set_in6(&sa, linklocal, 1234);
	CHECK(sa_af(&sa) == AF_INET6);
	CHECK(sa_port(&sa) == 1234);
	CHECK(sa_is_linklocal(&sa) == true);
	CHECK(sa_is_multicast(&sa) == false);

	memset(out, 0, sizeof(out));
	sa_in6(&sa, out);
	CHECK(memcmp(out, linklocal, sizeof(out)) == 0);

	sa_set_in6(&sa, allnodes, 5353);
	CHECK(sa_is_multicast(&sa) == true);
	CHECK(sa_port(&sa) == 5353);

	CHECK(sa_ntop(&sa, buf, sizeof(buf)) == 0);
	CHECK(strchr(buf, ':') != NULL);

	CHECK(sa_decode(&sa, "[::1]:5060", 10) == 0);
	CHECK(sa_af(&sa) == AF_INET6);
	CHECK(sa_port(&sa) == 5060);
	CHECK(sa_is_loopback(&sa) == true);

	libre_close();

	return errors ? 1 : 0;
}
