/* nftables 1.1.6 test_package native smoke: libnftnl userspace alloc/free.
 *
 * Exercises the real packaged static libnftnl.a (official netfilter code,
 * vendored 1.3.1, shipped in-package as lib/libnftnl.a for the static link
 * order libnftables -> libnftnl) WITHOUT touching kernel/root/netlink:
 * nftnl_*_alloc/free are pure userspace (malloc/free + attribute init),
 * no socket, no NETLINK_NETFILTER, no nf_tables needed.
 *
 * Symbol declarations use void* (version-proof across libnftnl releases:
 * free() const-qualification varies; the ABI is a single pointer either
 * way, and linking is by symbol name). No libnftnl headers are included so
 * this file never breaks on header layout differences; header presence is
 * verified separately by test_nft_native_smoke.py via file reads.
 *
 * A stub/empty libnftnl.a fails the link (undefined symbols); a broken
 * allocator returning NULL fails the NULL checks below. Exit 0 only when
 * all 4 object kinds allocate, report non-NULL, and free cleanly.
 */
#include <stdio.h>

extern void *nftnl_table_alloc(void);
extern void nftnl_table_free(void *);
extern void *nftnl_chain_alloc(void);
extern void nftnl_chain_free(void *);
extern void *nftnl_rule_alloc(void);
extern void nftnl_rule_free(void *);
extern void *nftnl_set_alloc(void);
extern void nftnl_set_free(void *);

int main(void)
{
	void *t = nftnl_table_alloc();
	void *c = nftnl_chain_alloc();
	void *r = nftnl_rule_alloc();
	void *s = nftnl_set_alloc();

	if (t == (void *)0) {
		fprintf(stderr, "FAIL: nftnl_table_alloc returned NULL\n");
		return 1;
	}
	if (c == (void *)0) {
		fprintf(stderr, "FAIL: nftnl_chain_alloc returned NULL\n");
		nftnl_table_free(t);
		return 1;
	}
	if (r == (void *)0) {
		fprintf(stderr, "FAIL: nftnl_rule_alloc returned NULL\n");
		nftnl_table_free(t);
		nftnl_chain_free(c);
		return 1;
	}
	if (s == (void *)0) {
		fprintf(stderr, "FAIL: nftnl_set_alloc returned NULL\n");
		nftnl_table_free(t);
		nftnl_chain_free(c);
		nftnl_rule_free(r);
		return 1;
	}
	printf("libnftnl alloc OK: table=%p chain=%p rule=%p set=%p\n", t, c, r, s);
	nftnl_table_free(t);
	nftnl_chain_free(c);
	nftnl_rule_free(r);
	nftnl_set_free(s);
	printf("libnftnl free OK (no crash, no netlink, no root)\n");
	return 0;
}
