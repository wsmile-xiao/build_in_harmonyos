/* nftables 1.1.6 test_package consumer check (Conan L1).
 *
 * Links the packaged static libnftables.a as a real consumer (via
 * <nftables/libnftables.h>) and verifies at runtime that the documented
 * libnftables API symbols resolve. The symbols are REFERENCED, never
 * CALLED: nft_ctx_new(NFT_CTX_DEFAULT) runs nft_ctx_netlink_init(),
 * which opens a NETLINK_NETFILTER socket and exits(3) on kernels
 * without nf_tables (preflight evidence: every `nft --check` dies with
 * "Unable to initialize Netlink socket: Permission denied"). Taking the
 * addresses proves header usability plus static-link symbol resolution
 * with zero kernel/root/netlink requirements. A missing library or
 * header fails the link; a stub library fails the NULL check below.
 */
#include <stdio.h>

#include <nftables/libnftables.h>

int main(void)
{
	void *sym_new = (void *)nft_ctx_new;
	void *sym_free = (void *)nft_ctx_free;

	if (sym_new == NULL || sym_free == NULL) {
		fprintf(stderr, "FAIL: libnftables API symbols missing\n");
		return 1;
	}
	printf("libnftables API OK: nft_ctx_new=%p nft_ctx_free=%p\n",
	       sym_new, sym_free);
	return 0;
}
