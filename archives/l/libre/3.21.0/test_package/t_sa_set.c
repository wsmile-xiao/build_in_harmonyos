#include <re.h>
#include "_check.h"

int main(void)
{

	CHECK(libre_init() == 0);
	struct sa sa, ai;
	struct pl addr, port;

	pl_set_str(&addr, "192.0.2.7");
	port.p = "7000";
	port.l = 4;

	sa_init(&sa, AF_INET);
	CHECK(sa_set(&sa, &addr, (uint16_t)pl_u32(&port)) == 0);
	CHECK(sa_port(&sa) == 7000);
	CHECK(sa_af(&sa) == AF_INET);
	CHECK(sa_isset(&sa, SA_ADDR) == true);

	CHECK(sa_addrinfo("127.0.0.1", &ai) == 0);
	CHECK(sa_is_loopback(&ai) == true);
	CHECK(sa_decode(&ai, "127.0.0.1:1999", 14) == 0);
	CHECK(sa_port(&ai) == 1999);

	/* 端口 0 与非法地址应返回非 0 */
	CHECK(sa_set_str(&sa, "256.256.256.256", 1) != 0);

	libre_close();

	return errors ? 1 : 0;
}
