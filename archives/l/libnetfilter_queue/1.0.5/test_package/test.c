/* libnetfilter_queue 1.0.5 consumer smoke test (Conan L1).
 *
 * Exercises real libnetfilter_queue APIs entirely in userspace (no kernel
 * NFQUEUE and no CAP_NET_ADMIN needed):
 *   - nfq_nlmsg_put(): build NFQNL_MSG_VERDICT / NFQNL_MSG_PACKET netlink
 *     message headers bound to a queue number
 *   - nfq_nlmsg_verdict_put() / nfq_nlmsg_verdict_put_mark(): append
 *     verdict attributes to the message
 * This links the static libnetfilter_queue together with its libmnl and
 * libnfnetlink dependencies end to end.
 */
/* OHOS: the sysroot ships a bionic-style uapi <linux/socket.h> whose
 * unconditional struct sockaddr_storage collides with musl
 * <sys/socket.h> (pulled in by libnfnetlink.h / libmnl.h / linux/netlink.h)
 * in BOTH include orders. Pre-define the uapi include guard so the sysroot
 * header contributes nothing and supply the typedef the netlink headers
 * need (same consumer-side variant as the libnfnetlink / libmnl ports).
 */
#ifndef __kernel_sa_family_t
typedef unsigned short __kernel_sa_family_t;
#endif
#ifndef _K_SS_MAXSIZE
#define _K_SS_MAXSIZE 128
#endif
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif

#include <stdio.h>
#include <string.h>
#include <arpa/inet.h> /* htons */

#include <linux/netfilter.h> /* NF_ACCEPT */

#include <libnetfilter_queue/libnetfilter_queue.h>

int main(void)
{
	char buf[8192] __attribute__((aligned(8)));
	struct nlmsghdr *nlh;
	struct nfgenmsg *nfmsg;
	unsigned int verdict_len, packet_len;

	memset(buf, 0, sizeof(buf));

	/* 1. Build a verdict message bound to queue 1.
	 * nfq_nlmsg_put() composes nlmsg_type as (NFNL_SUBSYS_QUEUE << 8) | type. */
	nlh = nfq_nlmsg_put(buf, NFQNL_MSG_VERDICT, 1);
	if (nlh == NULL ||
	    nlh->nlmsg_type != ((NFNL_SUBSYS_QUEUE << 8) | NFQNL_MSG_VERDICT)) {
		fprintf(stderr, "FAIL: nfq_nlmsg_put (verdict)\n");
		return 1;
	}
	nfmsg = (struct nfgenmsg *)NLMSG_DATA(nlh);
	if (ntohs(nfmsg->res_id) != 1u) {
		fprintf(stderr, "FAIL: queue number not encoded (res_id=%u)\n",
			ntohs(nfmsg->res_id));
		return 1;
	}

	/* 2. Append an ACCEPT verdict for packet id 42, then a mark. */
	nfq_nlmsg_verdict_put(nlh, 42, NF_ACCEPT);
	verdict_len = nlh->nlmsg_len;
	if (verdict_len <= NLMSG_HDRLEN + sizeof(struct nfgenmsg)) {
		fprintf(stderr, "FAIL: verdict attribute not appended\n");
		return 1;
	}
	nfq_nlmsg_verdict_put_mark(nlh, 0x12345678u);
	if (nlh->nlmsg_len <
	    verdict_len + NFA_LENGTH(sizeof(uint32_t))) {
		fprintf(stderr, "FAIL: mark attribute not appended\n");
		return 1;
	}

	/* 3. Build a packet message header for the same queue. */
	nlh = nfq_nlmsg_put(buf, NFQNL_MSG_PACKET, 2);
	if (nlh == NULL ||
	    nlh->nlmsg_type != ((NFNL_SUBSYS_QUEUE << 8) | NFQNL_MSG_PACKET)) {
		fprintf(stderr, "FAIL: nfq_nlmsg_put (packet)\n");
		return 1;
	}
	packet_len = nlh->nlmsg_len;

	printf("libnetfilter_queue 1.0.5 smoke test OK "
	       "(verdict msg %u bytes incl. verdict+mark attrs, "
	       "packet msg %u bytes)\n", verdict_len, packet_len);
	return 0;
}
