#include <stdio.h>
#include <netinet/in.h>

#include <osmocom/sigtran/osmo_ss7.h>
#include <osmocom/sigtran/protocol/m3ua.h>

/* C 消费者测试：真实调用 libosmo-sigtran 公开 API
 * （SS7 实例 / ASP / AS 对象的创建、查询、配置、销毁全链） */
int main(void)
{
	struct osmo_ss7_instance *inst;
	struct osmo_ss7_asp *asp;
	struct osmo_ss7_as *as;
	int rc;

	osmo_ss7_init();

	inst = osmo_ss7_instance_find_or_create(NULL, 1);
	if (!inst) {
		printf("FAIL: osmo_ss7_instance_find_or_create\n");
		return 1;
	}
	printf("ok: osmo_ss7_instance_find_or_create\n");

	if (osmo_ss7_instance_find(1) != inst) {
		printf("FAIL: osmo_ss7_instance_find\n");
		return 1;
	}
	printf("ok: osmo_ss7_instance_find\n");

	asp = osmo_ss7_asp_find_or_create2(inst, "test-asp", 0, 0,
					   IPPROTO_TCP, OSMO_SS7_ASP_PROT_M3UA);
	if (!asp) {
		printf("FAIL: osmo_ss7_asp_find_or_create2\n");
		return 1;
	}
	printf("ok: osmo_ss7_asp_find_or_create2\n");

	if (osmo_ss7_asp_get_proto(asp) != OSMO_SS7_ASP_PROT_M3UA) {
		printf("FAIL: osmo_ss7_asp_get_proto\n");
		return 1;
	}
	if (osmo_ss7_asp_get_trans_proto(asp) != IPPROTO_TCP) {
		printf("FAIL: osmo_ss7_asp_get_trans_proto\n");
		return 1;
	}
	printf("ok: asp proto/trans_proto getters\n");

	as = osmo_ss7_as_find_or_create(inst, "test-as", OSMO_SS7_ASP_PROT_M3UA);
	if (!as) {
		printf("FAIL: osmo_ss7_as_find_or_create\n");
		return 1;
	}
	printf("ok: osmo_ss7_as_find_or_create\n");

	rc = osmo_ss7_as_add_asp(as, "test-asp");
	if (rc != 0) {
		printf("FAIL: osmo_ss7_as_add_asp rc=%d\n", rc);
		return 1;
	}
	printf("ok: osmo_ss7_as_add_asp\n");

	osmo_ss7_as_del_asp(as, "test-asp");
	osmo_ss7_as_destroy(as);
	osmo_ss7_asp_destroy(asp);
	osmo_ss7_instance_destroy(inst);
	printf("libosmo-sccp consumer test: PASS\n");
	return 0;
}
