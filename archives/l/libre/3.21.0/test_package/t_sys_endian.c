#include <re.h>
#include "_check.h"
#include <arpa/inet.h>

int main(void)
{

	CHECK(libre_init() == 0);
	uint16_t s = 0x1234;
	uint32_t l = 0xdeadbeefu;
	uint64_t ll = 0x0123456789abcdefULL;

	CHECK(sys_ltohs(sys_htols(s)) == s);
	CHECK(sys_ltohl(sys_htoll(l)) == l);
	CHECK(sys_ntohll(sys_htonll(ll)) == ll);

	/* sys_hto* 是 host 布局 -> 小端布局；arm64 小端下等于恒等，
	   与 libc 的大端 htonl/htons 不同，故只做往返断言 */
	CHECK(sys_htoll(l) == l);
	CHECK(sys_htols(s) == s);
	CHECK(sys_htonll(ll) != ll);
	CHECK(sys_ntohll(sys_htonll(ll)) == ll);

	libre_close();

	return errors ? 1 : 0;
}
