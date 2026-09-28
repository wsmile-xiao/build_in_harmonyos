#include <re.h>
#include "_check.h"
#include <arpa/inet.h>

int main(void)
{

	CHECK(libre_init() == 0);
	struct sa sa, other, cpy;
	char buf[64];

	sa_init(&sa, AF_INET);
	CHECK(sa_af(&sa) == AF_INET);
	CHECK(sa_isset(&sa, SA_ADDR) == false);

	CHECK(sa_set_str(&sa, "127.0.0.1", 8080) == 0);
	CHECK(sa_af(&sa) == AF_INET);
	CHECK(sa_port(&sa) == 8080);
	CHECK(sa_in(&sa) == 0x7f000001u);
	CHECK(sa_is_loopback(&sa) == true);
	CHECK(sa_is_multicast(&sa) == false);

	CHECK(sa_ntop(&sa, buf, sizeof(buf)) == 0);
	CHECK(strcmp(buf, "127.0.0.1") == 0);

	CHECK(sa_set_str(&other, "127.0.0.1", 9090) == 0);
	CHECK(sa_cmp(&sa, &other, SA_ADDR) == true);
	CHECK(sa_cmp(&sa, &other, SA_ALL) == false);
	CHECK(sa_hash(&sa, SA_ADDR) == sa_hash(&other, SA_ADDR));

	sa_set_port(&sa, 5060);
	CHECK(sa_port(&sa) == 5060);

	CHECK(sa_pton("239.1.2.3", &other) == 0);
	CHECK(sa_is_multicast(&other) == true);

	sa_cpy(&cpy, &sa);
	CHECK(sa_cmp(&cpy, &sa, SA_ALL) == true);

	CHECK(sa_set_str(&other, "10.20.30.40", 1) == 0);
	CHECK(sa_in(&other) == 0x0a141e28u);

	libre_close();

	return errors ? 1 : 0;
}
